"""Live automatic-expiry, expiry-cancellation, and container-merge rehearsal."""

from datetime import datetime, timedelta, timezone
import json
import secrets
import time
from typing import Any, Dict, Mapping

from supermemory_lab.config import load_config
from supermemory_lab.evaluation import contains_text
from supermemory_lab.lifecycle_agents import (
    EphemeralIncidentAgent,
    WorkspaceConsolidationAgent,
)
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


from supermemory_lab.integrity import new_run_identity


_identity = new_run_identity


def _memory_id(response: Mapping[str, Any]) -> str:
    memories = response.get("memories")
    if not isinstance(memories, list) or not memories:
        raise RuntimeError("lease response omitted memory")
    memory_id = memories[0].get("id")
    if not isinstance(memory_id, str):
        raise RuntimeError("lease response omitted memory id")
    return memory_id


def _poll_expiry(
    agent: EphemeralIncidentAgent,
    *,
    expiring: str,
    retained: str,
    timeout_seconds: float = 45,
) -> Dict[str, Any]:
    started = time.monotonic()
    attempts = 0
    expiring_response: Mapping[str, Any] = {}
    retained_response: Mapping[str, Any] = {}
    while time.monotonic() - started < timeout_seconds:
        attempts += 1
        expiring_response = agent.search(expiring)
        retained_response = agent.search(retained)
        if not contains_text(expiring_response, expiring) and contains_text(
            retained_response, retained
        ):
            break
        time.sleep(2)
    return {
        "attempts": attempts,
        "elapsedMs": round((time.monotonic() - started) * 1000, 1),
        "expiredHidden": not contains_text(expiring_response, expiring),
        "cancelledExpiryRetained": contains_text(retained_response, retained),
    }


def _merge_status_name(response: Mapping[str, Any]) -> str:
    for key in ("status", "state"):
        value = response.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            nested = value.get("status") or value.get("state")
            if isinstance(nested, str):
                return nested
    return ""


def main() -> None:
    identity = _identity()
    suffix = identity[-6:]
    expiry_container = f"lab:lifecycle:{identity}:expiry"
    source_container = f"lab:lifecycle:{identity}:source"
    target_container = f"lab:lifecycle:{identity}:target"
    expiring = f"EXPIRING_INCIDENT_{suffix}"
    retained = f"RETAINED_POSTMORTEM_{suffix}"
    source_marker = f"MERGED_SOURCE_{suffix}"
    target_marker = f"MERGED_TARGET_{suffix}"
    clients = build_live_clients(load_config())
    incident = EphemeralIncidentAgent(
        clients.memory, container_tag=expiry_container
    )
    consolidation = WorkspaceConsolidationAgent(clients.memory)
    trace = RunTrace(f"lifecycle-{identity}", experiment="lifecycle-agents")
    evaluation: Dict[str, Any] = {}
    cleanup: Dict[str, Any] = {}

    try:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=16)
        expires_iso = expires_at.isoformat().replace("+00:00", "Z")
        expiring_created = trace.capture(
            "create_expiring_incident_lease",
            "supermemory",
            lambda: incident.create_lease(
                f"Temporary responder assignment {expiring} is active during this incident.",
                forget_after=expires_iso,
                reason="synthetic incident window ended",
                event_dates=[datetime.now(timezone.utc).isoformat()],
            ),
            summarize=lambda value: {
                "idPresent": bool(_memory_id(value)),
                "forgetAfter": value.get("memories", [{}])[0].get("forgetAfter"),
            },
        )
        retained_created = trace.capture(
            "create_cancelable_incident_lease",
            "supermemory",
            lambda: incident.create_lease(
                f"Temporary incident record {retained} will be promoted to a postmortem.",
                forget_after=expires_iso,
                reason="temporary until promoted",
            ),
            summarize=lambda value: {"idPresent": bool(_memory_id(value))},
        )
        clients.memory.wait_for_memory(
            expiring,
            container_tag=expiry_container,
            search_mode="memories",
            threshold=0.0,
            required_text=expiring,
            timeout_seconds=30,
            poll_seconds=1,
        )
        retained_update = trace.capture(
            "cancel_postmortem_expiry",
            "supermemory",
            lambda: incident.cancel_expiry(
                _memory_id(retained_created),
                content=(
                    f"Retained incident postmortem {retained} has no automatic expiry."
                ),
            ),
            summarize=lambda value: {
                "version": value.get("version"),
                "forgetAfter": value.get("forgetAfter"),
                "forgetReason": value.get("forgetReason"),
            },
        )
        expiry_result = trace.capture(
            "wait_for_server_expiry",
            "supermemory",
            lambda: _poll_expiry(
                incident, expiring=expiring, retained=retained
            ),
            summarize=lambda value: value,
        )
        expired_with_include = incident.search(
            expiring, include_forgotten=True
        )

        clients.memory.create_memories(
            source_container,
            [
                {
                    "content": f"Legacy workspace fact {source_marker} from source.",
                    "metadata": {"kind": "merge-source"},
                }
            ],
        )
        clients.memory.create_memories(
            target_container,
            [
                {
                    "content": f"Canonical workspace fact {target_marker} from target.",
                    "metadata": {"kind": "merge-target"},
                }
            ],
        )
        clients.memory.update_container_settings(
            source_container, name="Legacy synthetic workspace"
        )
        clients.memory.update_container_settings(
            target_container, name="Canonical synthetic workspace"
        )
        request = trace.capture(
            "queue_workspace_merge",
            "supermemory",
            lambda: consolidation.request_merge(
                source_container, target_container
            ),
            summarize=lambda value: {
                "mergeIdPresent": bool(value.merge_id),
                "target": value.target_tag,
            },
        )
        merge_started = time.monotonic()
        merge_attempts = 0
        last_status: Mapping[str, Any] = {}
        merged_search: Mapping[str, Any] = {}
        while time.monotonic() - merge_started < 90:
            merge_attempts += 1
            last_status = consolidation.status(request)
            merged_search = clients.memory.search_memories(
                f"workspace facts {source_marker} {target_marker}",
                container_tag=target_container,
                search_mode="memories",
                threshold=0.0,
                limit=20,
            )
            if contains_text(merged_search, source_marker) and contains_text(
                merged_search, target_marker
            ):
                break
            time.sleep(2)
        data_plane_status = _merge_status_name(last_status)
        status_wait_error = None
        try:
            final_status = trace.capture(
                "wait_for_merge_status_finalization",
                "supermemory",
                lambda: clients.memory.wait_for_container_merge(
                    request.merge_id, timeout_seconds=20, poll_seconds=1
                ),
                summarize=lambda value: {
                    "status": _merge_status_name(value),
                    "progress": value.get("progress"),
                },
            )
        except Exception as error:
            final_status = last_status
            status_wait_error = {
                "type": type(error).__name__,
                "detail": str(error)[:220],
            }
        try:
            clients.memory.get_container_settings(source_container)
            source_deleted = False
        except Exception:
            source_deleted = True
        target_settings = clients.memory.get_container_settings(target_container)

        evaluation = {
            "expiryAccepted": bool(
                expiring_created.get("memories", [{}])[0].get("forgetAfter")
            ),
            "expiry": expiry_result,
            "expiryCancellationVersion": retained_update.get("version"),
            "expiryCancellationCleared": retained_update.get("forgetAfter") is None,
            "expiredRecoverableWhenIncluded": contains_text(
                expired_with_include, expiring
            ),
            "mergeAttempts": merge_attempts,
            "mergeElapsedMs": round((time.monotonic() - merge_started) * 1000, 1),
            "mergeDataPlaneStatus": data_plane_status,
            "mergeFinalStatus": _merge_status_name(final_status),
            "mergeStatusWaitError": status_wait_error,
            "mergeStatusKeys": sorted(final_status.keys()),
            "sourceMemoryMoved": contains_text(merged_search, source_marker),
            "targetMemoryRetained": contains_text(merged_search, target_marker),
            "sourceContainerDeleted": source_deleted,
            "targetSettingsRetained": target_settings.get("name")
            == "Canonical synthetic workspace",
        }
        evaluation["expiryLifecyclePassed"] = all(
            [
                evaluation["expiryAccepted"],
                expiry_result["expiredHidden"],
                expiry_result["cancelledExpiryRetained"],
                evaluation["expiryCancellationVersion"] == 2,
                evaluation["expiryCancellationCleared"],
            ]
        )
        evaluation["mergeLifecyclePassed"] = all(
            [
                evaluation["sourceMemoryMoved"],
                evaluation["targetMemoryRetained"],
                evaluation["sourceContainerDeleted"],
                evaluation["targetSettingsRetained"],
            ]
        )
        evaluation["passed"] = (
            evaluation["expiryLifecyclePassed"]
            and evaluation["mergeLifecyclePassed"]
        )
        trace.metric("evaluation", evaluation)
    finally:
        for tag in (expiry_container, source_container, target_container):
            try:
                cleanup[tag] = clients.memory.delete_container(tag)
            except Exception as error:
                if tag == source_container and "(404)" in str(error):
                    cleanup[tag] = {"alreadyDeletedByMerge": True}
                else:
                    cleanup[tag] = {
                        "notDeleted": True,
                        "error": type(error).__name__,
                        "detail": str(error)[:220],
                    }
        trace.metric("cleanup", cleanup)

    path = trace.write()
    print(
        json.dumps(
            {"trace": str(path), "evaluation": evaluation, "cleanup": cleanup},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
