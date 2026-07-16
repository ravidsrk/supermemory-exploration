"""Live correction, custom-bucket, idempotence, and isolation rehearsal."""

from datetime import datetime, timezone
import json
import secrets
import time
from typing import Any, Dict, List, Mapping

from supermemory_lab.config import load_config
from supermemory_lab.evaluation import contains_text
from supermemory_lab.live import build_live_clients
from supermemory_lab.personalization_agent import EvolvingPreferenceAgent
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def _entries(response: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    values = response.get("memoryEntries")
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, Mapping)]


def _documents(response: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    for key in ("memories", "documents", "data"):
        values = response.get(key)
        if isinstance(values, list):
            return [value for value in values if isinstance(value, Mapping)]
    return []


def _observe_exact_conversation_memory(
    memory: Any,
    *,
    container_tag: str,
    query: str,
    canary: str,
    timeout_seconds: float = 30,
) -> Dict[str, Any]:
    """Observe automatic extraction without treating unrelated seed data as ready."""

    started = time.monotonic()
    attempts = 0
    latest: Mapping[str, Any] = {}
    while time.monotonic() - started < timeout_seconds:
        attempts += 1
        latest = memory.search_memories(
            query,
            container_tag=container_tag,
            search_mode="memories",
            threshold=0.0,
            limit=20,
        )
        if contains_text(latest, canary):
            break
        time.sleep(2)
    return {
        "attempts": attempts,
        "elapsedMs": round((time.monotonic() - started) * 1000, 1),
        "visible": contains_text(latest, canary),
    }


def _poll_correction(
    memory: Any,
    *,
    container_tag: str,
    query: str,
    old_canary: str,
    new_canary: str,
    timeout_seconds: float = 120,
) -> Dict[str, Any]:
    started = time.monotonic()
    attempts = 0
    latest: Dict[str, Any] = {}
    while time.monotonic() - started < timeout_seconds:
        attempts += 1
        profile = memory.profile(
            container_tag,
            query=query,
            threshold=0.0,
            include=["static", "dynamic", "buckets"],
        )
        search = memory.search_memories(
            query,
            container_tag=container_tag,
            search_mode="memories",
            threshold=0.0,
            limit=20,
        )
        latest = {"profile": profile, "search": search}
        if all(contains_text(value, new_canary) for value in latest.values()):
            break
        time.sleep(2)
    return {
        "attempts": attempts,
        "elapsedMs": round((time.monotonic() - started) * 1000, 1),
        "newVisible": {
            key: contains_text(value, new_canary) for key, value in latest.items()
        },
        "oldVisible": {
            key: contains_text(value, old_canary) for key, value in latest.items()
        },
    }


def main() -> None:
    identity = _identity()
    suffix = identity[-6:]
    primary = f"lab:preference:{identity}:primary"
    isolated = f"lab:preference:{identity}:isolated"
    conversation_id = f"preference-conversation-{identity}"
    old_canary = f"WEEKLY_PDF_{suffix}"
    new_canary = f"DAILY_MARKDOWN_{suffix}"
    other_canary = f"OTHER_TENANT_{suffix}"
    clients = build_live_clients(load_config())
    trace = RunTrace(
        f"preference-{identity}", experiment="evolving-preference-agent"
    )
    agent = EvolvingPreferenceAgent(
        clients.memory, clients.llm, container_tag=primary
    )
    cleanup: Dict[str, Any] = {}
    evaluation: Dict[str, Any] = {}

    try:
        for tag, marker in ((primary, "workspace-initialized"), (isolated, other_canary)):
            trace.capture(
                f"seed_{marker.lower()}",
                "supermemory",
                lambda tag=tag, marker=marker: clients.memory.create_memories(
                    tag,
                    [
                        {
                            "content": (
                                "Synthetic workspace initialized; this is not a user "
                                "preference."
                                if tag == primary
                                else f"Synthetic isolated marker {marker}."
                            ),
                            "isStatic": True,
                            "metadata": {"kind": "workspace-seed"},
                        }
                    ],
                ),
                summarize=lambda value: {
                    "created": len(value.get("memories", []))
                    if isinstance(value.get("memories"), list)
                    else 0
                },
            )

        settings = trace.capture(
            "configure_primary",
            "supermemory",
            lambda: agent.configure(name="Synthetic evolving preference"),
            summarize=lambda value: {
                "containerTag": value.get("containerTag"),
                "bucketCount": len(value.get("profileBuckets", []))
                if isinstance(value.get("profileBuckets"), list)
                else 0,
                "hasEntityContext": bool(value.get("entityContext")),
            },
        )
        buckets = trace.capture(
            "read_bucket_definitions",
            "supermemory",
            lambda: clients.memory.list_profile_buckets(primary),
            summarize=lambda value: {
                "keys": [
                    bucket.get("key")
                    for bucket in value.get("buckets", [])
                    if isinstance(bucket, Mapping)
                ]
            },
        )

        initial_history = [
            {
                "role": "user",
                "content": (
                    f"My explicit report preference is weekly PDF. Marker {old_canary}."
                ),
            },
            {"role": "assistant", "content": "I will remember that preference."},
        ]
        trace.capture(
            "ingest_initial_history",
            "supermemory",
            lambda: agent.record_history(
                conversation_id, initial_history, revision=1
            ),
            summarize=lambda value: {"accepted": bool(value)},
        )
        conversation_extraction = trace.capture(
            "observe_conversation_extraction",
            "supermemory",
            lambda: _observe_exact_conversation_memory(
                clients.memory,
                container_tag=primary,
                query=f"explicit weekly PDF report preference marker {old_canary}",
                canary=old_canary,
            ),
            summarize=lambda value: value,
        )
        conversation_documents = trace.capture(
            "inspect_conversation_document",
            "supermemory",
            lambda: clients.memory.list_documents(
                container_tags=[primary], limit=20
            ),
            summarize=lambda value: {
                "documents": [
                    {
                        "idPresent": bool(document.get("id")),
                        "customId": document.get("customId"),
                        "status": document.get("status"),
                    }
                    for document in _documents(value)
                ]
            },
        )

        normalized_initial = trace.capture(
            "store_normalized_initial_preference",
            "supermemory",
            lambda: agent.record_explicit_preference(
                f"Current explicit report preference {old_canary}: weekly PDF reports."
            ),
            summarize=lambda value: {
                "created": len(value.get("memories", []))
                if isinstance(value.get("memories"), list)
                else 0
            },
        )
        normalized_memories = normalized_initial.get("memories")
        if not isinstance(normalized_memories, list) or not normalized_memories:
            raise RuntimeError("normalized preference write did not return a memory id")
        normalized_memory_id = normalized_memories[0].get("id")
        if not isinstance(normalized_memory_id, str):
            raise RuntimeError("normalized preference response omitted memory id")
        initial_visibility = trace.capture(
            "wait_normalized_initial_preference",
            "supermemory",
            lambda: clients.memory.wait_for_memory(
                f"explicit weekly PDF report preference marker {old_canary}",
                container_tag=primary,
                search_mode="memories",
                timeout_seconds=60,
                poll_seconds=2,
                threshold=0.0,
                required_text=old_canary,
            ),
            summarize=lambda value: {
                "attempts": value.get("_pollAttempts"),
                "oldVisible": contains_text(value, old_canary),
            },
        )

        corrected_history = initial_history + [
            {
                "role": "user",
                "content": (
                    "Correction: replace my earlier preference. I now explicitly want daily "
                    f"Markdown reports and no PDF. Marker {new_canary}."
                ),
            },
            {"role": "assistant", "content": "I will use the corrected preference."},
        ]
        trace.capture(
            "ingest_corrected_full_history",
            "supermemory",
            lambda: agent.record_history(
                conversation_id, corrected_history, revision=2
            ),
            summarize=lambda value: {"accepted": bool(value)},
        )
        normalized_correction = trace.capture(
            "version_normalized_preference",
            "supermemory",
            lambda: agent.correct_explicit_preference(
                normalized_memory_id,
                content=(
                    f"Current explicit report preference {new_canary}: daily Markdown "
                    "reports and no PDF. This supersedes the earlier weekly PDF preference."
                ),
            ),
            summarize=lambda value: {
                "version": value.get("version"),
                "hasParent": bool(value.get("parentMemoryId")),
                "hasRoot": bool(value.get("rootMemoryId")),
            },
        )
        correction = trace.capture(
            "wait_for_corrected_memory",
            "supermemory",
            lambda: _poll_correction(
                clients.memory,
                container_tag=primary,
                query="current explicit report format and cadence preference",
                old_canary=old_canary,
                new_canary=new_canary,
            ),
            summarize=lambda value: value,
        )

        before_repeat = clients.memory.list_memory_entries([primary], limit=100)
        documents_before_repeat = clients.memory.list_documents(
            container_tags=[primary], limit=100
        )
        trace.capture(
            "repeat_identical_full_history",
            "supermemory",
            lambda: agent.record_history(
                conversation_id, corrected_history, revision=2
            ),
            summarize=lambda value: {"accepted": bool(value)},
        )
        time.sleep(8)
        after_repeat = clients.memory.list_memory_entries([primary], limit=100)
        documents_after_repeat = clients.memory.list_documents(
            container_tags=[primary], limit=100
        )

        personalized = trace.capture(
            "answer_from_corrected_preference",
            "supermemory+openrouter",
            lambda: agent.answer(
                "In one sentence, how should you deliver my reports now? Include the exact "
                "current evidence token beginning DAILY_MARKDOWN_ and do not repeat any "
                "superseded token."
            ),
            summarize=lambda value: {
                "answer": value.answer,
                "profileChars": len(value.profile_context),
                "searchChars": len(value.search_context),
            },
        )
        isolation_read = clients.memory.search_memories(
            f"report marker {new_canary}",
            container_tag=isolated,
            search_mode="memories",
            threshold=0.0,
            limit=20,
        )
        inferred_queue = clients.memory.list_inferred_memories(primary)
        bucket_profile = clients.memory.profile(
            primary,
            query="current report delivery preference",
            threshold=0.0,
            include=["buckets"],
            buckets=["communication-preferences"],
        )

        before_entries = _entries(before_repeat)
        after_entries = _entries(after_repeat)
        before_documents = _documents(documents_before_repeat)
        after_documents = _documents(documents_after_repeat)
        expected_buckets = {
            "communication-preferences",
            "privacy-constraints",
            "active-goals",
        }
        actual_buckets = {
            str(bucket.get("key"))
            for bucket in buckets.get("buckets", [])
            if isinstance(bucket, Mapping)
        }
        evaluation = {
            "settingsPersisted": bool(settings.get("entityContext")),
            "customBucketsPresent": expected_buckets.issubset(actual_buckets),
            "conversationAutomaticExtraction": conversation_extraction["visible"],
            "conversationDocumentCount": len(_documents(conversation_documents)),
            "initialOldVisible": contains_text(initial_visibility, old_canary),
            "correction": correction,
            "correctionVersion": normalized_correction.get("version"),
            "answerUsesNew": new_canary in personalized.answer,
            "answerOmitsOld": old_canary not in personalized.answer,
            "isolatedContainerOmitsPrimary": not contains_text(
                isolation_read, new_canary
            ),
            "idempotentEntryCount": len(after_entries) == len(before_entries),
            "idempotentDocumentCount": len(after_documents)
            == len(before_documents),
            "entriesBeforeRepeat": len(before_entries),
            "entriesAfterRepeat": len(after_entries),
            "documentsBeforeRepeat": len(before_documents),
            "documentsAfterRepeat": len(after_documents),
            "versionedEntries": sum(
                int(bool(entry.get("history"))) for entry in after_entries
            ),
            "customBucketClassified": contains_text(bucket_profile, new_canary),
            "inferredQueueCount": inferred_queue.get("total", 0),
        }
        evaluation["passed"] = all(
            [
                evaluation["settingsPersisted"],
                evaluation["customBucketsPresent"],
                evaluation["initialOldVisible"],
                all(correction.get("newVisible", {}).values()),
                evaluation["answerUsesNew"],
                evaluation["answerOmitsOld"],
                evaluation["isolatedContainerOmitsPrimary"],
                evaluation["idempotentEntryCount"],
                evaluation["idempotentDocumentCount"],
                evaluation["correctionVersion"] == 2,
                evaluation["versionedEntries"] >= 1,
            ]
        )
        trace.metric("evaluation", evaluation)
    finally:
        for tag in (primary, isolated):
            try:
                cleanup[tag] = clients.memory.delete_container(tag)
            except Exception as error:
                cleanup[tag] = {
                    "error": type(error).__name__,
                    "detail": str(error)[:300],
                }
        trace.metric("cleanup", cleanup)

    path = trace.write()
    print(
        json.dumps(
            {
                "trace": str(path),
                "evaluation": evaluation,
                "cleanup": cleanup,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
