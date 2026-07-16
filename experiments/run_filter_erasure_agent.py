"""Live metadata-filter matrix plus preview-gated semantic erasure."""

from datetime import datetime, timezone
import json
import secrets
from typing import Any, Dict, List, Mapping, Sequence

from supermemory_lab.client import SupermemoryClient
from supermemory_lab.config import load_config
from supermemory_lab.erasure_agent import GovernedErasureAgent
from supermemory_lab.evaluation import contains_text
from supermemory_lab.http import UrlLibTransport
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def _result_text(response: Mapping[str, Any]) -> str:
    return json.dumps(response.get("results", []), ensure_ascii=False, default=str)


def _expect_markers(
    response: Mapping[str, Any], *, present: Sequence[str], absent: Sequence[str]
) -> Dict[str, Any]:
    text = _result_text(response)
    return {
        "present": {marker: marker in text for marker in present},
        "absent": {marker: marker not in text for marker in absent},
        "passed": all(marker in text for marker in present)
        and all(marker not in text for marker in absent),
    }


def _memory_id(response: Mapping[str, Any], index: int) -> str:
    memories = response.get("memories")
    if not isinstance(memories, list) or index >= len(memories):
        raise RuntimeError("direct memory response omitted an expected memory")
    memory_id = memories[index].get("id")
    if not isinstance(memory_id, str):
        raise RuntimeError("direct memory response omitted an expected memory id")
    return memory_id


def main() -> None:
    identity = _identity()
    suffix = identity[-6:]
    container = f"lab:erasure:{identity}"
    security = f"ERASE_SECURITY_{suffix}"
    privacy = f"REVIEW_PRIVACY_{suffix}"
    keep = f"RETAIN_DEPLOYMENT_{suffix}"
    config = load_config()
    if not config.supermemory_api_key:
        raise RuntimeError("SUPERMEMORY_API_KEY is required")
    memory = SupermemoryClient(
        UrlLibTransport(
            config.supermemory_base_url,
            config.supermemory_api_key,
            timeout_seconds=180,
        )
    )
    agent = GovernedErasureAgent(memory, container_tag=container)
    trace = RunTrace(f"erasure-{identity}", experiment="filter-erasure-agent")
    evaluation: Dict[str, Any] = {}
    cleanup: Dict[str, Any] = {}

    try:
        created = trace.capture(
            "seed_governed_records",
            "supermemory",
            lambda: memory.create_memories(
                container,
                [
                    {
                        "content": (
                            f"Governed erasure record {security}: synthetic security alert "
                            "for tenant Acme; deletion is approved only after preview."
                        ),
                        "isStatic": False,
                        "metadata": {
                            "tenant": "acme",
                            "category": "security-alert",
                            "priority": 9,
                            "labels": ["urgent", "customer-facing"],
                            "owner": "Mira Patel",
                            "owner.name": "Mira Patel",
                            "retention": "temporary",
                        },
                    },
                    {
                        "content": (
                            f"Governed erasure record {privacy}: synthetic privacy request "
                            "for tenant Acme; requires manual review."
                        ),
                        "isStatic": False,
                        "metadata": {
                            "tenant": "acme",
                            "category": "privacy-request",
                            "priority": 8,
                            "labels": ["customer-facing", "manual-review"],
                            "owner": "Mina Shah",
                            "owner.name": "Mina Shah",
                            "retention": "temporary",
                        },
                    },
                    {
                        "content": (
                            f"Governed erasure record {keep}: verified deployment note for "
                            "tenant Acme; this control must remain."
                        ),
                        "isStatic": False,
                        "metadata": {
                            "tenant": "acme",
                            "category": "deployment-note",
                            "priority": 4,
                            "labels": ["internal", "keep"],
                            "owner": "Raj Kumar",
                            "owner.name": "Raj Kumar",
                            "retention": "permanent",
                        },
                    },
                ],
            ),
            summarize=lambda value: {
                "created": len(value.get("memories", []))
                if isinstance(value.get("memories"), list)
                else 0
            },
        )
        memory.wait_for_memory(
            f"governed erasure record {security}",
            container_tag=container,
            search_mode="memories",
            threshold=0.0,
            required_text=security,
            timeout_seconds=60,
            poll_seconds=2,
        )

        cases = {
            "equality": (
                {"AND": [{"key": "category", "value": "security-alert"}]},
                [security],
                [privacy, keep],
            ),
            "numeric": (
                {
                    "AND": [
                        {
                            "filterType": "numeric",
                            "key": "priority",
                            "value": "8",
                            "numericOperator": ">=",
                        }
                    ]
                },
                [security, privacy],
                [keep],
            ),
            "array_contains": (
                {
                    "AND": [
                        {
                            "filterType": "array_contains",
                            "key": "labels",
                            "value": "urgent",
                        }
                    ]
                },
                [security],
                [privacy, keep],
            ),
            "string_contains": (
                {
                    "AND": [
                        {
                            "filterType": "string_contains",
                            "key": "owner",
                            "value": "mira",
                            "ignoreCase": True,
                        }
                    ]
                },
                [security],
                [privacy, keep],
            ),
            "negate": (
                {
                    "AND": [
                        {
                            "key": "category",
                            "value": "deployment-note",
                            "negate": True,
                        }
                    ]
                },
                [security, privacy],
                [keep],
            ),
            "nested": (
                {
                    "AND": [
                        {"key": "tenant", "value": "acme"},
                        {
                            "OR": [
                                {
                                    "filterType": "array_contains",
                                    "key": "labels",
                                    "value": "urgent",
                                },
                                {"key": "category", "value": "privacy-request"},
                            ]
                        },
                    ]
                },
                [security, privacy],
                [keep],
            ),
            "dot_key": (
                {
                    "AND": [
                        {
                            "filterType": "string_contains",
                            "key": "owner.name",
                            "value": "Mira",
                        }
                    ]
                },
                [security],
                [privacy, keep],
            ),
        }
        filter_results: Dict[str, Any] = {}
        for name, (filters, present, absent) in cases.items():
            try:
                response = trace.capture(
                    f"filter_{name}",
                    "supermemory",
                    lambda filters=filters: agent.filtered_search(
                        "governed erasure record for tenant Acme", filters
                    ),
                    summarize=lambda value, present=present, absent=absent: _expect_markers(
                        value, present=present, absent=absent
                    ),
                )
                filter_results[name] = _expect_markers(
                    response, present=present, absent=absent
                )
            except Exception as error:
                filter_results[name] = {
                    "passed": False,
                    "error": type(error).__name__,
                    "detail": str(error)[:300],
                }

        listed = memory.list_memory_entries(
            [container],
            filters={"AND": [{"key": "category", "value": "security-alert"}]},
            limit=20,
        )
        listed_entries = listed.get("memoryEntries")
        list_filter_exact = (
            isinstance(listed_entries, list)
            and len(listed_entries) == 1
            and contains_text(listed_entries[0], security)
        )

        query = (
            f"Forget only the synthetic security alert carrying exact token {security}. "
            f"Never forget {privacy} or {keep}."
        )
        preview = trace.capture(
            "preview_semantic_erasure",
            "supermemory",
            lambda: agent.preview(
                query,
                required_tokens=[security],
                protected_tokens=[privacy, keep],
                threshold=0.5,
                max_candidates=1,
            ),
            summarize=lambda value: {
                "authorized": value.authorized,
                "reason": value.reason,
                "candidateCount": len(value.candidates),
                "candidateIdsPresent": all(bool(row.get("id")) for row in value.candidates),
            },
        )
        before_apply = memory.search_memories(
            security,
            container_tag=container,
            search_mode="memories",
            threshold=0.0,
            limit=20,
        )
        applied = trace.capture(
            "apply_approved_erasure",
            "supermemory",
            lambda: agent.apply(preview, reason="approved synthetic governance rehearsal"),
            summarize=lambda value: {
                "dryRun": value.get("dryRun"),
                "count": value.get("count"),
                "batchIdPresent": bool(value.get("forgetBatchId")),
                "forgottenCount": len(value.get("forgotten", []))
                if isinstance(value.get("forgotten"), list)
                else 0,
            },
        )
        after_default = memory.search_memories(
            security,
            container_tag=container,
            search_mode="memories",
            threshold=0.0,
            limit=20,
        )
        after_with_forgotten = memory.search_memories(
            security,
            container_tag=container,
            search_mode="memories",
            threshold=0.0,
            limit=20,
            include={"forgottenMemories": True},
        )
        control_after = memory.search_memories(
            keep,
            container_tag=container,
            search_mode="memories",
            threshold=0.0,
            limit=20,
        )
        history = memory.list_memory_entries([container], limit=20)
        history_entries = history.get("memoryEntries")
        target_id = _memory_id(created, 0)
        target_history = [
            entry
            for entry in history_entries or []
            if isinstance(entry, Mapping)
            and (entry.get("id") == target_id or entry.get("rootMemoryId") == target_id)
        ]

        evaluation = {
            "filters": filter_results,
            "filterCasesPassed": sum(
                int(bool(result.get("passed"))) for result in filter_results.values()
            ),
            "filterCasesTotal": len(filter_results),
            "listFilterExact": list_filter_exact,
            "previewAuthorized": preview.authorized,
            "previewCandidateCount": len(preview.candidates),
            "targetVisibleBefore": contains_text(before_apply, security),
            "applyCount": applied.get("count"),
            "batchIdPresent": bool(applied.get("forgetBatchId")),
            "targetHiddenByDefault": not contains_text(after_default, security),
            "targetRecoverableWhenIncluded": contains_text(
                after_with_forgotten, security
            ),
            "controlRetained": contains_text(control_after, keep),
            "historyMarksForgotten": any(
                bool(entry.get("isForgotten")) for entry in target_history
            ),
            "forgetReasonPersisted": any(
                entry.get("forgetReason") == "approved synthetic governance rehearsal"
                for entry in target_history
            ),
        }
        evaluation["safeErasurePassed"] = all(
            [
                evaluation["filterCasesPassed"] == evaluation["filterCasesTotal"],
                evaluation["previewAuthorized"],
                evaluation["targetVisibleBefore"],
                evaluation["applyCount"] == 1,
                evaluation["batchIdPresent"],
                evaluation["targetHiddenByDefault"],
                evaluation["controlRetained"],
            ]
        )
        evaluation["documentedAuditRecoveryObserved"] = all(
            [
                evaluation["listFilterExact"],
                evaluation["targetRecoverableWhenIncluded"],
                evaluation["historyMarksForgotten"],
                evaluation["forgetReasonPersisted"],
            ]
        )
        evaluation["passed"] = evaluation["safeErasurePassed"]
        trace.metric("evaluation", evaluation)
    finally:
        try:
            cleanup = memory.delete_container(container)
        except Exception as error:
            cleanup = {
                "error": type(error).__name__,
                "detail": str(error)[:300],
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
