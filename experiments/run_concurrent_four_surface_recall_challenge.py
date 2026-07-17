"""Live sequential baseline and bounded concurrent four-surface recall challenge."""

from datetime import datetime, timezone
import json
import secrets
import time
from typing import Any, Dict

from supermemory_lab.concurrent_recall_challenger import (
    ConcurrentRecallChallenger,
    RecallProbe,
)
from supermemory_lab.config import load_config
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def _wait_for_profile(memory: Any, container: str, marker: str) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        response = memory.profile(
            container,
            query=marker,
            threshold=0.0,
            include=["static", "dynamic", "buckets"],
        )
        if marker in json.dumps(response, ensure_ascii=False, default=str):
            return
        time.sleep(2)
    raise TimeoutError("profile challenge marker did not become visible")


def _summary(challenger: ConcurrentRecallChallenger, challenge: Any, value: Any) -> Dict[str, Any]:
    return {
        "challengeValid": challenger.verify_challenge(challenge),
        "reportValid": challenger.verify_report(challenge, value),
        "samples": len(value.samples),
        "peakInFlight": value.peak_in_flight,
        "wallTimeMs": value.wall_time_ms,
        "requestsPerSecond": value.requests_per_second,
        "successRate": value.success_rate,
        "leaks": value.leak_count,
        "errors": value.error_count,
        "surfaceMetrics": [
            {
                "surface": item.surface,
                "samples": item.samples,
                "successes": item.successes,
                "p50Ms": item.p50_ms,
                "p95Ms": item.p95_ms,
                "maximumMs": item.maximum_ms,
            }
            for item in value.surface_metrics
        ],
    }


def main() -> None:
    identity = _identity()
    suffix = identity[-6:].upper()
    workspace = f"lab:concurrent-recall:{identity}"
    other_workspace = f"lab:concurrent-recall:other:{identity}"
    memory_marker = f"CONCURRENT_MEMORY_{suffix}"
    document_marker = f"CONCURRENT_DOCUMENT_{suffix}"
    forbidden_marker = f"CONCURRENT_OTHER_{suffix}"
    clients = build_live_clients(load_config())
    signing_key = secrets.token_bytes(32)
    trace = RunTrace(
        f"concurrent-recall-{identity}",
        experiment="bounded-concurrent-four-surface-recall-challenge",
    )
    cleanup: Dict[str, Any] = {}
    evaluation: Dict[str, Any] = {}
    try:
        clients.memory.create_memories(
            workspace,
            [{
                "content": f"Synthetic concurrent profile canary {memory_marker}.",
                "isStatic": True,
                "metadata": {"synthetic": True, "kind": "concurrent-canary"},
            }],
        )
        document = clients.memory.add_document(
            f"Synthetic concurrent document canary {document_marker}.",
            container_tag=workspace,
            custom_id=f"concurrent-document-{suffix.lower()}",
            metadata={"synthetic": True, "kind": "concurrent-document"},
            task_type="superrag",
            dreaming="instant",
        )
        document_id = str(document.get("id") or document.get("documentId") or "")
        if not document_id:
            raise RuntimeError("concurrent canary response omitted document ID")
        clients.memory.create_memories(
            other_workspace,
            [{
                "content": f"Private concurrent isolation control {forbidden_marker}.",
                "metadata": {"synthetic": True, "kind": "tenant-control"},
            }],
        )
        clients.memory.wait_for_document(
            document_id, timeout_seconds=180, poll_seconds=3
        )
        clients.memory.wait_for_memory(
            memory_marker,
            container_tag=workspace,
            search_mode="memories",
            threshold=0.0,
            required_text=memory_marker,
            timeout_seconds=120,
            poll_seconds=2,
        )
        clients.memory.wait_for_memory(
            document_marker,
            container_tag=workspace,
            search_mode="hybrid",
            threshold=0.0,
            required_text=document_marker,
            timeout_seconds=120,
            poll_seconds=2,
        )
        _wait_for_profile(clients.memory, workspace, memory_marker)

        probes = (
            RecallProbe("memories", "memories", memory_marker, memory_marker, (forbidden_marker,)),
            RecallProbe("hybrid", "hybrid", document_marker, document_marker, (forbidden_marker,)),
            RecallProbe("documents", "documents", document_marker, document_marker, (forbidden_marker,)),
            RecallProbe("profile", "profile", memory_marker, memory_marker, (forbidden_marker,)),
        )
        challenger = ConcurrentRecallChallenger(
            clients.memory,
            container_tag=workspace,
            signing_key=signing_key,
        )
        sequential_challenge = challenger.build_challenge(
            probes, rounds=5, max_workers=1
        )
        sequential = trace.capture(
            "five_round_sequential_four_surface_baseline",
            "supermemory",
            lambda: challenger.run(sequential_challenge),
            summarize=lambda value: _summary(
                challenger, sequential_challenge, value
            ),
        )
        concurrent_challenge = challenger.build_challenge(
            probes, rounds=5, max_workers=8
        )
        concurrent = trace.capture(
            "five_round_eight_worker_four_surface_challenge",
            "supermemory",
            lambda: challenger.run(concurrent_challenge),
            summarize=lambda value: _summary(
                challenger, concurrent_challenge, value
            ),
        )
        evaluation = {
            "sequentialChallengeValid": challenger.verify_challenge(sequential_challenge),
            "sequentialReportValid": challenger.verify_report(sequential_challenge, sequential),
            "concurrentChallengeValid": challenger.verify_challenge(concurrent_challenge),
            "concurrentReportValid": challenger.verify_report(concurrent_challenge, concurrent),
            "twentySequentialSamples": len(sequential.samples) == 20,
            "twentyConcurrentSamples": len(concurrent.samples) == 20,
            "fourConcurrentSurfaces": len(concurrent.surface_metrics) == 4,
            "concurrencyActuallyObserved": concurrent.peak_in_flight > 1,
            "concurrencyBoundRespected": concurrent.peak_in_flight <= 8,
            "allConcurrentReadsCorrect": concurrent.success_rate == 1.0,
            "noConcurrentTenantLeaks": concurrent.leak_count == 0,
            "noConcurrentErrors": concurrent.error_count == 0,
            "noExternalActionAuthority": not concurrent.external_action_authorized,
            "sequentialWallTimeMs": sequential.wall_time_ms,
            "concurrentWallTimeMs": concurrent.wall_time_ms,
            "sequentialRequestsPerSecond": sequential.requests_per_second,
            "concurrentRequestsPerSecond": concurrent.requests_per_second,
        }
        evaluation["passed"] = all(
            value is True
            for key, value in evaluation.items()
            if key
            not in {
                "sequentialWallTimeMs",
                "concurrentWallTimeMs",
                "sequentialRequestsPerSecond",
                "concurrentRequestsPerSecond",
                "passed",
            }
        )
        trace.metric("evaluation", evaluation)
    finally:
        for name, container in (("challenge", workspace), ("other", other_workspace)):
            try:
                cleanup[name] = clients.memory.delete_container(container)
            except Exception as error:
                cleanup[name] = {
                    "error": type(error).__name__,
                    "detail": str(error)[:180],
                }
        trace.metric("cleanup", cleanup)
        path = trace.write()
        print(json.dumps({"trace": str(path), "evaluation": evaluation, "cleanup": cleanup}, indent=2))


if __name__ == "__main__":
    main()
