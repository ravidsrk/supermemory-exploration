"""Live 600-document ingest and checkpointed six-by-100 exact deletion boundary audit."""

from datetime import datetime, timezone
import json
import secrets
import time
from typing import Any, Dict, List, Mapping

from supermemory_lab.bulk_ingestion_controller import (
    AdaptiveBulkIngestionController,
    IngestionRecord,
)
from supermemory_lab.config import load_config
from supermemory_lab.authorization import TestingAuthorizationLedger
from supermemory_lab.exact_deletion_controller import (
    DeletionAuthorization,
    ExactDeletionController,
)
from supermemory_lab.live import build_live_clients
from supermemory_lab.http import ApiError
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def _documents(value: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    raw = value.get("documents") or value.get("memories") or value.get("results") or []
    return [item for item in raw if isinstance(item, Mapping)]


def _inventory(memory: Any, workspace: str) -> List[Mapping[str, Any]]:
    documents: List[Mapping[str, Any]] = []
    seen = set()
    for page in range(1, 101):
        response = memory.list_documents(
            container_tags=[workspace], limit=100, page=page
        )
        current = _documents(response)
        for document in current:
            document_id = str(document.get("id") or document.get("documentId") or "")
            if document_id and document_id not in seen:
                seen.add(document_id)
                documents.append(document)
        if len(current) < 100:
            break
    return documents


def _exact_cleanup(memory: Any, workspace: str) -> Dict[str, Any]:
    """Enumerate exact IDs before deleting; repair the empty-container API edge."""

    before = _inventory(memory, workspace)
    ids = [
        str(item.get("id") or item.get("documentId"))
        for item in before
        if item.get("id") or item.get("documentId")
    ]
    batches = []
    for offset in range(0, len(ids), 100):
        response = memory.bulk_delete_documents(ids[offset : offset + 100])
        batches.append(
            {
                "requested": len(ids[offset : offset + 100]),
                "success": response.get("success"),
                "deletedCount": response.get("deletedCount"),
                "errors": len(response.get("errors") or []),
            }
        )
    remaining = _inventory(memory, workspace)
    result: Dict[str, Any] = {
        "inventoryBefore": len(before),
        "exactDeleteBatches": batches,
        "inventoryAfter": len(remaining),
    }
    if remaining:
        result["containerDeleteSkipped"] = "exact inventory cleanup incomplete"
        return result
    try:
        memory.delete_container(workspace)
        result["containerDeleted"] = True
        return result
    except ApiError as error:
        result["initialContainerDelete"] = {
            "status": error.status,
            "detail": error.detail[:120],
        }
        if error.status == 404:
            result["containerAlreadyAbsent"] = True
            return result
        if error.status != 500:
            return result

    # Hosted deletion can return 500 for a real but empty container. A single scoped
    # canary makes that control-plane record deletable; it is never used as evidence.
    cleanup_id = f"orphan-cleanup-{secrets.token_hex(8)}"
    added = memory.add_document(
        "Synthetic teardown canary for an empty capacity-audit container.",
        custom_id=cleanup_id,
        container_tag=workspace,
        metadata={"synthetic": True, "purpose": "orphan-container-teardown"},
    )
    document_id = str(added.get("id") or added.get("documentId") or "")
    result["orphanRepairCanaryCreated"] = bool(document_id)
    if document_id:
        for _ in range(10):
            try:
                state = memory.get_document(document_id)
                if str(state.get("status") or "").lower() in {"done", "failed"}:
                    break
            except ApiError:
                pass
            time.sleep(1)
    try:
        memory.delete_container(workspace)
        result["containerDeletedAfterOrphanRepair"] = True
    except ApiError as error:
        result["orphanRepairDelete"] = {
            "status": error.status,
            "detail": error.detail[:120],
        }
        if document_id:
            fallback = memory.bulk_delete_documents([document_id])
            result["orphanRepairExactFallback"] = {
                "success": fallback.get("success"),
                "deletedCount": fallback.get("deletedCount"),
            }
    return result


def main() -> None:
    identity = _identity()
    suffix = identity[-6:].upper()
    workspace = f"lab:max-cardinality:{identity}"
    run_id = f"max-cardinality-{suffix.lower()}"
    first_marker = f"MAX_BATCH_{suffix}_000"
    middle_marker = f"MAX_BATCH_{suffix}_299"
    last_marker = f"MAX_BATCH_{suffix}_599"
    clients = build_live_clients(load_config(), memory_timeout_seconds=240)
    signing_key = secrets.token_bytes(32)
    ingest_checkpoints = []
    deletion_checkpoints = []
    trace = RunTrace(
        f"max-cardinality-{identity}",
        experiment="maximum-cardinality-ingest-and-exact-delete-audit",
    )
    cleanup: Dict[str, Any] = {}
    evaluation: Dict[str, Any] = {}
    try:
        batch_601_denied = False
        try:
            clients.memory.add_documents_batch(
                [{"content": "local boundary control"}] * 601,
                container_tag=workspace,
            )
        except ValueError:
            batch_601_denied = True
        delete_101_denied = False
        try:
            clients.memory.bulk_delete_documents(
                [f"local-boundary-{index}" for index in range(101)]
            )
        except ValueError:
            delete_101_denied = True

        records = tuple(
            IngestionRecord(
                f"max-source-{suffix.lower()}-{index:03d}",
                (
                    f"Synthetic maximum batch record {index}. "
                    f"Marker MAX_BATCH_{suffix}_{index:03d}. "
                    f"Shard {index % 20}; verification group {index % 7}."
                ),
                {"kind": "capacity-canary", "sequence": index, "synthetic": True},
            )
            for index in range(600)
        )
        ingestion = AdaptiveBulkIngestionController(
            clients.memory,
            container_tag=workspace,
            run_id=run_id,
            signing_key=signing_key,
            initial_batch_size=600,
            maximum_batch_size=600,
            max_throttle_retries=0,
            checkpoint_sink=ingest_checkpoints.append,
        )
        manifest = ingestion.build_manifest(records)
        accepted = trace.capture(
            "submit_exact_document_batch_maximum_600",
            "supermemory",
            lambda: ingestion.submit(manifest),
            summarize=lambda value: {
                "manifestValid": ingestion.verify_manifest(manifest),
                "checkpointValid": ingestion.verify_checkpoint(manifest, value),
                "accepted": len(value.accepted_custom_ids),
                "uniqueDocumentIds": len(set(value.document_ids)),
                "requestAttempts": value.request_attempts,
                "complete": value.complete,
            },
        )
        immediate = trace.capture(
            "measure_maximum_batch_inventory_vs_processing",
            "supermemory",
            lambda: ingestion.reconcile(manifest),
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
        ready = trace.capture(
            "wait_for_all_600_documents_to_exit_processing",
            "supermemory",
            lambda: ingestion.wait_until_ready(
                manifest, timeout_seconds=900, poll_seconds=10
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
        searches = []
        for name, marker in (
            ("first", first_marker),
            ("middle", middle_marker),
            ("last", last_marker),
        ):
            response = clients.memory.search_documents(
                marker,
                container_tags=[workspace],
                limit=5,
                chunk_threshold=0.0,
                document_threshold=0.0,
                rerank=True,
                only_matching_chunks=True,
            )
            searches.append((name, marker in json.dumps(response, default=str)))

        deletion = ExactDeletionController(
            clients.memory,
            signing_key=signing_key,
            authorization_ledger=TestingAuthorizationLedger(trust_first_use=True),
            checkpoint_sink=deletion_checkpoints.append,
        )
        plan = deletion.build_plan(
            container_tag=workspace,
            source_manifest_hash=manifest.manifest_hash,
            document_ids=accepted.document_ids,
        )
        authorization = DeletionAuthorization(
            plan.plan_hash, plan.source_manifest_hash, "synthetic-capacity-owner"
        )
        wrong_authorization_denied = False
        try:
            deletion.apply(
                plan,
                DeletionAuthorization(
                    "wrong", plan.source_manifest_hash, "synthetic-capacity-owner"
                ),
            )
        except PermissionError:
            wrong_authorization_denied = True
        paused = trace.capture(
            "delete_first_200_by_two_exact_100_id_batches",
            "supermemory",
            lambda: deletion.apply(plan, authorization, max_batches=2),
            summarize=lambda value: {
                "checkpointValid": deletion.verify_checkpoint(plan, value),
                "deleted": len(value.deleted_document_ids),
                "completedBatches": value.completed_batches,
                "complete": value.complete,
            },
        )
        fresh_deletion = ExactDeletionController(
            clients.memory,
            signing_key=signing_key,
            authorization_ledger=TestingAuthorizationLedger(trust_first_use=True),
            checkpoint_sink=deletion_checkpoints.append,
        )
        completed = trace.capture(
            "fresh_process_deletes_remaining_400_by_exact_ids",
            "supermemory",
            lambda: fresh_deletion.apply(
                plan, authorization, checkpoint=paused
            ),
            summarize=lambda value: {
                "checkpointValid": fresh_deletion.verify_checkpoint(plan, value),
                "deleted": len(value.deleted_document_ids),
                "completedBatches": value.completed_batches,
                "complete": value.complete,
            },
        )
        replay_calls_before = len(deletion_checkpoints)
        replay_checkpoint = fresh_deletion.apply(
            plan, authorization, checkpoint=completed
        )
        remaining = _inventory(clients.memory, workspace)
        negative_search = clients.memory.search_documents(
            middle_marker,
            container_tags=[workspace],
            limit=5,
            chunk_threshold=0.0,
            document_threshold=0.0,
            rerank=False,
            only_matching_chunks=True,
        )
        evaluation = {
            "batch601DeniedLocally": batch_601_denied,
            "delete101DeniedLocally": delete_101_denied,
            "manifestValid": ingestion.verify_manifest(manifest),
            "maximum600AcceptedInOneRequest": (
                accepted.complete
                and accepted.request_attempts == 1
                and len(accepted.document_ids) == 600
            ),
            "immediateInventoryMeasured": immediate.imported_count == 600,
            "immediateProcessingCount": immediate.processing_count,
            "finalInventoryExact": ready.exact_inventory,
            "all600Done": ready.done_count == 600 and ready.failed_count == 0,
            "threeEdgeCanariesSearchable": all(passed for _, passed in searches),
            "wrongDeletionAuthorizationDenied": wrong_authorization_denied,
            "pausedDeletionCheckpointValid": deletion.verify_checkpoint(plan, paused),
            "pausedAfter200": len(paused.deleted_document_ids) == 200,
            "sixExactDeleteBatches": (
                completed.completed_batches == 6 and len(deletion_checkpoints) == 6
            ),
            "all600ExactIdsDeleted": (
                completed.complete and len(completed.deleted_document_ids) == 600
            ),
            "completedReplayIdempotent": (
                replay_checkpoint == completed
                and len(deletion_checkpoints) == replay_calls_before
            ),
            "inventoryEmptyAfterExactDelete": not remaining,
            "middleCanaryAbsentAfterDelete": middle_marker
            not in json.dumps(negative_search, default=str),
            "broadContainerDeleteUsedForPrimaryCleanup": False,
        }
        evaluation["passed"] = all(
            value is True
            for key, value in evaluation.items()
            if key not in {
                "immediateProcessingCount",
                "broadContainerDeleteUsedForPrimaryCleanup",
                "passed",
            }
        ) and evaluation["broadContainerDeleteUsedForPrimaryCleanup"] is False
        trace.metric("evaluation", evaluation)
    finally:
        try:
            cleanup["exactWorkspaceCleanup"] = _exact_cleanup(
                clients.memory, workspace
            )
        except Exception as error:
            cleanup["exactWorkspaceCleanup"] = {
                "error": type(error).__name__,
                "detail": str(error)[:180],
            }
        trace.metric("cleanup", cleanup)
        path = trace.write()
        print(json.dumps({"trace": str(path), "evaluation": evaluation, "cleanup": cleanup}, indent=2))


if __name__ == "__main__":
    main()
