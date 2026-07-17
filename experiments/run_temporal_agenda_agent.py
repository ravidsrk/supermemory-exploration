"""Measure exact and natural-language date recall for a practical agenda agent."""

from datetime import datetime, timezone
import json
import secrets
import statistics
from typing import Any, Dict, List

from supermemory_lab.config import load_config
from supermemory_lab.live import build_live_clients
from supermemory_lab.temporal_agenda import TemporalAgendaAgent
from supermemory_lab.trace import RunTrace


from supermemory_lab.integrity import new_run_identity


_identity = new_run_identity


def _percentile(values: List[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction + 0.999) - 1))
    return round(ordered[index], 1)


def main() -> None:
    identity = _identity()
    suffix = identity[-6:]
    workspace = f"lab:temporal-agenda:{identity}"
    past = f"PAST_EVENT_{suffix}"
    today = f"TODAY_EVENT_{suffix}"
    future = f"FUTURE_EVENT_{suffix}"
    clients = build_live_clients(load_config())
    trace = RunTrace(f"temporal-{identity}", experiment="temporal-agenda-agent")
    evaluation: Dict[str, Any] = {}
    cleanup: Dict[str, Any] = {}

    try:
        memories = [
            {
                "content": (
                    f"Database rehearsal {past} occurred on July 10, 2026 at 14:30 UTC and "
                    "completed successfully."
                ),
                "metadata": {"kind": "agenda-event", "eventDate": "2026-07-10"},
            },
            {
                "content": (
                    f"Customer interview {today} is scheduled for July 16, 2026 at 16:00 UTC."
                ),
                "metadata": {"kind": "agenda-event", "eventDate": "2026-07-16"},
            },
            {
                "content": (
                    f"Launch dry run {future} is scheduled for August 5, 2026 at 09:00 UTC."
                ),
                "metadata": {"kind": "agenda-event", "eventDate": "2026-08-05"},
            },
        ]
        trace.capture(
            "seed_dated_agenda",
            "supermemory",
            lambda: clients.memory.create_memories(workspace, memories),
            summarize=lambda value: {
                "accepted": len(value.get("memories", [])),
            },
        )
        for canary in (past, today, future):
            clients.memory.wait_for_memory(
                canary,
                container_tag=workspace,
                search_mode="memories",
                threshold=0.0,
                required_text=canary,
                timeout_seconds=30,
                poll_seconds=1,
            )

        cases = [
            ("exact-past", "between July 9 and July 11, 2026", "database rehearsal", past, 0.0),
            ("natural-past", "last week", "database rehearsal", past, 0.0),
            ("exact-today", "on July 16, 2026", "customer interview", today, 0.0),
            ("month-future", "in August 2026", "launch dry run", future, 0.0),
            ("unrelated", "in August 2026", "payroll approval", "", 0.7),
        ]
        rows: List[Dict[str, Any]] = []
        agent = TemporalAgendaAgent(clients.memory, clients.llm, container_tag=workspace)
        for rewrite in (False, True):
            for name, window, subject, expected, threshold in cases:
                recall = trace.capture(
                    f"recall_{name}_{'rewrite' if rewrite else 'literal'}",
                    "supermemory",
                    lambda window=window, subject=subject, rewrite=rewrite, threshold=threshold: agent.recall_window(
                        natural_window=window,
                        subject=subject,
                        rewrite_query=rewrite,
                        limit=1,
                        threshold=threshold,
                    ),
                    summarize=lambda value: {
                        "firstResult": value.first_result_text,
                        "latencyMs": value.latency_ms,
                    },
                )
                hit = (
                    expected.casefold() in recall.first_result_text.casefold()
                    if expected
                    else recall.first_result_text == ""
                )
                rows.append(
                    {
                        "name": name,
                        "window": window,
                        "rewriteQuery": rewrite,
                        "expected": expected or "no-result",
                        "threshold": threshold,
                        "firstResult": recall.first_result_text,
                        "hit": hit,
                        "latencyMs": recall.latency_ms,
                    }
                )

        answer = trace.capture(
            "answer_temporal_agenda",
            "supermemory+openrouter",
            lambda: agent.answer_window(
                natural_window="between July 9 and July 17, 2026",
                question=(
                    "Which database rehearsal completed and which customer interview is "
                    "scheduled in this window? Include evidence identifiers and exact times."
                ),
                current_time="2026-07-16T12:00:00Z",
                rewrite_query=True,
            ),
            summarize=lambda value: {
                "answer": value.answer,
                "contextChars": len(value.retrieved_context),
            },
        )
        exact_rows = [row for row in rows if row["name"].startswith("exact")]
        natural_rows = [row for row in rows if not row["name"].startswith("exact")]
        latencies = [row["latencyMs"] for row in rows]
        evaluation = {
            "cases": rows,
            "exactDateHits": sum(int(row["hit"]) for row in exact_rows),
            "exactDateTotal": len(exact_rows),
            "naturalPhraseHits": sum(int(row["hit"]) for row in natural_rows),
            "naturalPhraseTotal": len(natural_rows),
            "searchLatencyP50Ms": round(statistics.median(latencies), 1),
            "searchLatencyP95Ms": _percentile(latencies, 0.95),
            "answer": answer.answer,
            "answerHasPast": past.casefold() in answer.answer.casefold(),
            "answerHasToday": today.casefold() in answer.answer.casefold(),
            "answerExcludesFuture": future.casefold() not in answer.answer.casefold(),
        }
        evaluation["passed"] = all(
            [
                evaluation["exactDateHits"] == evaluation["exactDateTotal"],
                evaluation["naturalPhraseHits"] == evaluation["naturalPhraseTotal"],
                evaluation["answerHasPast"],
                evaluation["answerHasToday"],
                evaluation["answerExcludesFuture"],
            ]
        )
        trace.metric("evaluation", evaluation)
    finally:
        try:
            cleanup = clients.memory.delete_container(workspace)
        except Exception as error:
            cleanup = {"error": type(error).__name__, "detail": str(error)[:200]}
        trace.metric("cleanup", cleanup)

    path = trace.write()
    print(json.dumps({"trace": str(path), "evaluation": evaluation, "cleanup": cleanup}, indent=2))


if __name__ == "__main__":
    main()
