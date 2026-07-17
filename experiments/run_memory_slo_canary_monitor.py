"""Live four-surface memory SLO canaries plus an injected isolation alert."""

from datetime import datetime, timezone
import json
import secrets
import time
from typing import Any, Dict

from supermemory_lab.config import load_config
from supermemory_lab.live import build_live_clients
from supermemory_lab.memory_slo_monitor import (
    CanarySpec,
    MemorySLOCanaryMonitor,
    SLOPolicy,
)
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def _wait_for_profile_marker(memory: Any, container: str, marker: str) -> Dict[str, Any]:
    deadline = time.monotonic() + 90
    attempts = 0
    last: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        attempts += 1
        last = memory.profile(
            container,
            query=marker,
            threshold=0.0,
            include=["static", "dynamic", "buckets"],
        )
        if marker in json.dumps(last, ensure_ascii=False, default=str):
            last["_pollAttempts"] = attempts
            return last
        time.sleep(2)
    raise TimeoutError(f"profile canary did not become visible after {attempts} attempts")


class CountingLLM:
    def __init__(self, llm: Any) -> None:
        self._llm = llm
        self.calls = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return self._llm.complete(system_prompt, user_prompt)


class InjectedLeakMemory:
    """Adds a synthetic forbidden result to one probe without reading another tenant."""

    def __init__(self, memory: Any, forbidden_marker: str) -> None:
        self._memory = memory
        self._forbidden = forbidden_marker

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        response = dict(self._memory.search_memories(query, **kwargs))
        results = list(response.get("results") or [])
        results.append({"memory": f"Injected isolation violation {self._forbidden}"})
        response["results"] = results
        return response

    def search_documents(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return self._memory.search_documents(query, **kwargs)

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        return self._memory.profile(container_tag, **kwargs)


def main() -> None:
    identity = _identity()
    suffix = identity[-6:].upper()
    workspace = f"lab:memory-slo:{identity}"
    other_workspace = f"lab:memory-slo:other:{identity}"
    memory_marker = f"SLO_MEMORY_CANARY_{suffix}"
    document_marker = f"SLO_DOCUMENT_CANARY_{suffix}"
    other_marker = f"SLO_OTHER_TENANT_{suffix}"
    clients = build_live_clients(load_config())
    llm = CountingLLM(clients.llm)
    signing_key = secrets.token_bytes(32)
    trace = RunTrace(
        f"memory-slo-{identity}", experiment="four-surface-memory-slo-canary-monitor"
    )
    cleanup: Dict[str, Any] = {}
    evaluation: Dict[str, Any] = {}
    try:
        clients.memory.create_memories(
            workspace,
            [
                {
                    "content": (
                        f"Synthetic stable profile canary {memory_marker}. "
                        "The canary color is ultramarine."
                    ),
                    "isStatic": True,
                    "metadata": {"kind": "slo-canary"},
                }
            ],
        )
        document = clients.memory.add_document(
            (
                f"Synthetic document retrieval canary {document_marker}. "
                "The canary queue is north-seven."
            ),
            container_tag=workspace,
            custom_id=f"slo-document-{suffix.lower()}",
            metadata={"kind": "slo-document-canary", "synthetic": True},
            task_type="superrag",
            dreaming="instant",
        )
        document_id = str(document.get("id") or document.get("documentId") or "")
        if not document_id:
            raise RuntimeError("SLO canary document response omitted ID")
        clients.memory.create_memories(
            other_workspace,
            [
                {
                    "content": f"Private isolation control {other_marker}.",
                    "metadata": {"kind": "tenant-control"},
                }
            ],
        )
        clients.memory.wait_for_document(document_id, timeout_seconds=150, poll_seconds=3)
        clients.memory.wait_for_memory(
            memory_marker,
            container_tag=workspace,
            search_mode="memories",
            threshold=0.0,
            required_text=memory_marker,
            timeout_seconds=90,
            poll_seconds=2,
        )
        clients.memory.wait_for_memory(
            document_marker,
            container_tag=workspace,
            search_mode="hybrid",
            threshold=0.0,
            required_text=document_marker,
            timeout_seconds=90,
            poll_seconds=2,
        )
        _wait_for_profile_marker(clients.memory, workspace, memory_marker)

        specs = (
            CanarySpec(
                "v4-memories-canary",
                "memories",
                memory_marker,
                memory_marker,
                (other_marker,),
            ),
            CanarySpec(
                "v4-hybrid-canary",
                "hybrid",
                document_marker,
                document_marker,
                (other_marker,),
            ),
            CanarySpec(
                "v3-documents-canary",
                "documents",
                document_marker,
                document_marker,
                (other_marker,),
            ),
            CanarySpec(
                "v4-profile-canary",
                "profile",
                memory_marker,
                memory_marker,
                (other_marker,),
            ),
        )
        healthy_monitor = MemorySLOCanaryMonitor(
            clients.memory,
            llm,
            container_tag=workspace,
            signing_key=signing_key,
        )
        healthy = trace.capture(
            "probe_four_memory_surfaces_for_three_rounds",
            "supermemory",
            lambda: healthy_monitor.run(
                specs,
                rounds=3,
                policy=SLOPolicy(
                    minimum_success_rate=1.0,
                    maximum_p95_ms=10_000.0,
                    maximum_leaks=0,
                ),
            ),
            summarize=lambda value: {
                "reportValid": healthy_monitor.verify_report(value),
                "samples": len(value.samples),
                "successRate": value.success_rate,
                "p50Ms": value.p50_ms,
                "p95Ms": value.p95_ms,
                "leaks": value.leak_count,
                "violations": len(value.violations),
                "surfaceMetrics": [
                    {
                        "surface": item.surface,
                        "successes": item.successes,
                        "samples": item.samples,
                        "p95Ms": item.p95_ms,
                    }
                    for item in value.surface_metrics
                ],
            },
        )
        healthy_explanation = healthy_monitor.explain(healthy)
        healthy_llm_calls = llm.calls

        alert_monitor = MemorySLOCanaryMonitor(
            InjectedLeakMemory(clients.memory, other_marker),
            llm,
            container_tag=workspace,
            signing_key=signing_key,
        )
        alert = trace.capture(
            "inject_one_isolation_violation_and_sign_alert",
            "supermemory+policy",
            lambda: alert_monitor.run(
                specs[:1],
                rounds=1,
                policy=SLOPolicy(
                    minimum_success_rate=1.0,
                    maximum_p95_ms=10_000.0,
                    maximum_leaks=0,
                ),
            ),
            summarize=lambda value: {
                "reportValid": alert_monitor.verify_report(value),
                "successRate": value.success_rate,
                "leakCount": value.leak_count,
                "violations": list(value.violations),
                "rawMemoryStoredInSummary": False,
            },
        )
        alert_explanation = trace.capture(
            "explain_metrics_only_alert_without_action_authority",
            "openrouter",
            lambda: alert_monitor.explain(alert),
            summarize=lambda value: {
                "chars": len(value),
                "noActionEnvelope": value.startswith("NO_EXTERNAL_ACTION"),
                "otherTenantMarkerEmitted": other_marker in value,
            },
        )
        evaluation = {
            "healthyReportValid": healthy_monitor.verify_report(healthy),
            "fourSurfacesMeasured": len(healthy.surface_metrics) == 4,
            "twelveHealthySamples": len(healthy.samples) == 12,
            "healthySuccessRateOne": healthy.success_rate == 1.0,
            "healthyLeakCountZero": healthy.leak_count == 0,
            "healthyHasNoViolations": not healthy.violations,
            "healthySkippedLLM": (
                healthy_llm_calls == 0
                and healthy_explanation
                == "NO_EXTERNAL_ACTION\nMEMORY_SLO_HEALTHY"
            ),
            "alertReportValid": alert_monitor.verify_report(alert),
            "injectedLeakDetected": alert.leak_count == 1,
            "alertHasViolation": bool(alert.violations),
            "alertUsedLLMOnce": llm.calls == 1,
            "alertHidesRawForbiddenMarker": other_marker not in alert_explanation,
            "noActionEnvelope": alert_explanation.startswith("NO_EXTERNAL_ACTION"),
            "externalActionAuthorized": (
                healthy.external_action_authorized or alert.external_action_authorized
            ),
        }
        evaluation["passed"] = all(
            value is True
            for key, value in evaluation.items()
            if key not in {"externalActionAuthorized", "passed"}
        ) and evaluation["externalActionAuthorized"] is False
        trace.metric("evaluation", evaluation)
    finally:
        for name, container in (("slo", workspace), ("other", other_workspace)):
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
