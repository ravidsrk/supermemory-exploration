"""Live throttled bulk ingestion, signed resume, processing queue, and reconciliation."""

from datetime import datetime, timezone
import json
import secrets
from typing import Any, Dict

from supermemory_lab.bulk_ingestion_controller import (
    AdaptiveBulkIngestionController,
    IngestionRecord,
)
from supermemory_lab.config import load_config
from supermemory_lab.http import ApiError
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


class OneThrottleMemory:
    """Injects one explicit 429, then delegates every operation to hosted Supermemory."""

    def __init__(self, memory: Any) -> None:
        self._memory = memory
        self.inject_throttle = True
        self.batch_sizes = []

    def add_documents_batch(self, documents, **kwargs):
        self.batch_sizes.append(len(documents))
        if self.inject_throttle:
            self.inject_throttle = False
            raise ApiError(
                "POST", "/v3/documents/batch", 429, "injected rate limit", "2"
            )
        return self._memory.add_documents_batch(documents, **kwargs)

    def list_documents(self, **kwargs):
        return self._memory.list_documents(**kwargs)

    def get_processing_documents(self, **kwargs):
        return self._memory.get_processing_documents(**kwargs)


def main() -> None:
    identity = _identity()
    suffix = identity[-6:].upper()
    run_id = f"bulk-{suffix.lower()}"
    workspace = f"lab:adaptive-bulk:{identity}"
    other_workspace = f"lab:adaptive-bulk:other:{identity}"
    first_marker = f"BULK_CANARY_{suffix}_01"
    last_marker = f"BULK_CANARY_{suffix}_24"
    other_marker = f"OTHER_BULK_TENANT_{suffix}"
    clients = build_live_clients(load_config())
    memory = OneThrottleMemory(clients.memory)
    signing_key = secrets.token_bytes(32)
    sleeps = []
    checkpoints = []
    trace = RunTrace(
        f"adaptive-bulk-{identity}",
        experiment="adaptive-resumable-bulk-ingestion-controller",
    )
    cleanup: Dict[str, Any] = {}
    evaluation: Dict[str, Any] = {}
    try:
        clients.memory.create_memories(
            other_workspace,
            [
                {
                    "content": f"Private other-tenant marker {other_marker}.",
                    "metadata": {"kind": "tenant-control"},
                }
            ],
        )
        records = []
        for index in range(1, 25):
            marker = f"BULK_CANARY_{suffix}_{index:02d}"
            records.append(
                IngestionRecord(
                    f"bulk-source-{suffix.lower()}-{index:02d}",
                    (
                        f"Synthetic bulk operations record {index}. Marker {marker}. "
                        f"The verified queue partition for item {index} is "
                        f"partition-{index % 4}; this is test data only."
                    ),
                    {"kind": "bulk-canary", "sequence": index, "synthetic": True},
                )
            )
        first = AdaptiveBulkIngestionController(
            memory,
            container_tag=workspace,
            run_id=run_id,
            signing_key=signing_key,
            initial_batch_size=8,
            maximum_batch_size=8,
            sleep=sleeps.append,
            checkpoint_sink=checkpoints.append,
        )
        manifest = first.build_manifest(records)
        paused = trace.capture(
            "inject_429_then_pause_after_two_accepted_batches",
            "policy+supermemory",
            lambda: first.submit(manifest, max_accepted_batches=2),
            summarize=lambda value: {
                "manifestValid": first.verify_manifest(manifest),
                "checkpointValid": first.verify_checkpoint(manifest, value),
                "accepted": len(value.accepted_custom_ids),
                "complete": value.complete,
                "throttles": value.throttle_events,
                "requestAttempts": value.request_attempts,
                "retryDelays": sleeps,
                "batchSizes": list(memory.batch_sizes),
            },
        )
        fresh = AdaptiveBulkIngestionController(
            memory,
            container_tag=workspace,
            run_id=run_id,
            signing_key=signing_key,
            initial_batch_size=8,
            maximum_batch_size=8,
            sleep=sleeps.append,
            checkpoint_sink=checkpoints.append,
        )
        completed = trace.capture(
            "fresh_process_resumes_only_pending_stable_ids",
            "policy+supermemory",
            lambda: fresh.submit(manifest, checkpoint=paused),
            summarize=lambda value: {
                "checkpointValid": fresh.verify_checkpoint(manifest, value),
                "accepted": len(value.accepted_custom_ids),
                "uniqueResponseIds": len(set(value.document_ids)),
                "complete": value.complete,
                "batchSizes": list(memory.batch_sizes),
            },
        )
        immediate = trace.capture(
            "observe_acceptance_separately_from_processing",
            "supermemory",
            lambda: fresh.reconcile(manifest),
            summarize=lambda value: {
                "acceptedCheckpointComplete": completed.complete,
                "inventoryExact": value.exact_inventory,
                "done": value.done_count,
                "processing": value.processing_count,
                "semanticallyReady": value.semantically_ready,
            },
        )
        ready = trace.capture(
            "wait_for_exact_inventory_and_processing_queue_exit",
            "supermemory",
            lambda: fresh.wait_until_ready(
                manifest, timeout_seconds=240, poll_seconds=4
            ),
            summarize=lambda value: {
                "expected": value.expected_count,
                "imported": value.imported_count,
                "done": value.done_count,
                "processing": value.processing_count,
                "failed": value.failed_count,
                "exactInventory": value.exact_inventory,
                "semanticallyReady": value.semantically_ready,
            },
        )
        first_search = clients.memory.search_documents(
            first_marker,
            container_tags=[workspace],
            limit=5,
            chunk_threshold=0.0,
            document_threshold=0.0,
            rerank=True,
            only_matching_chunks=True,
        )
        last_search = clients.memory.search_documents(
            last_marker,
            container_tags=[workspace],
            limit=5,
            chunk_threshold=0.0,
            document_threshold=0.0,
            rerank=True,
            only_matching_chunks=True,
        )
        combined_search = json.dumps(
            {"first": first_search, "last": last_search}, default=str
        )
        evaluation = {
            "manifestValid": first.verify_manifest(manifest),
            "throttleObserved": paused.throttle_events == 1,
            "retryAfterHonored": sleeps == [2.0],
            "batchReducedAfter429": memory.batch_sizes[:2] == [8, 4],
            "pauseCheckpointValid": first.verify_checkpoint(manifest, paused),
            "pauseWasIncomplete": not paused.complete,
            "resumeCheckpointValid": fresh.verify_checkpoint(manifest, completed),
            "resumeAcceptedAll": (
                completed.complete
                and len(completed.accepted_custom_ids) == len(records)
                and len(set(completed.document_ids)) == len(records)
            ),
            "checkpointPersistedAfterEachBatch": len(checkpoints) == 5,
            "acceptedVsReadyMeasured": isinstance(immediate.semantically_ready, bool),
            "inventoryExact": ready.exact_inventory,
            "allDocumentsDone": ready.done_count == len(records),
            "processingQueueEmpty": ready.processing_count == 0,
            "semanticReadinessExplicit": ready.semantically_ready,
            "edgeMarkersSearchable": (
                first_marker in combined_search and last_marker in combined_search
            ),
            "otherTenantAbsent": other_marker not in combined_search,
            "externalActionAuthorized": False,
        }
        evaluation["passed"] = all(
            value is True
            for key, value in evaluation.items()
            if key not in {"externalActionAuthorized", "passed"}
        ) and evaluation["externalActionAuthorized"] is False
        trace.metric("evaluation", evaluation)
    finally:
        for name, container in (("bulk", workspace), ("other", other_workspace)):
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
