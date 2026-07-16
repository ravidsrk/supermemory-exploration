"""Evaluation utilities for memory visibility and deterministic answer scoring."""

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .client import SupermemoryClient


def contains_text(value: Any, needle: str) -> bool:
    """Return true when a nested JSON-like value contains the exact text fragment."""

    if isinstance(value, str):
        return needle in value
    if isinstance(value, Mapping):
        return any(contains_text(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(contains_text(item, needle) for item in value)
    return False


def required_term_score(answer: str, required_terms: Sequence[str]) -> bool:
    normalized = answer.casefold()
    return all(term.casefold() in normalized for term in required_terms)


@dataclass(frozen=True)
class VisibilityCase:
    name: str
    content: str
    is_static: bool


@dataclass(frozen=True)
class RetrievalQuery:
    name: str
    query: str
    should_match: bool


class ConsistencyMatrix:
    """Measure when one direct write becomes visible through each supported read path."""

    def __init__(
        self,
        memory: SupermemoryClient,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._memory = memory
        self._clock = clock
        self._sleeper = sleeper

    def run_case(
        self,
        case: VisibilityCase,
        *,
        container_tag: str,
        canary: str,
        timeout_seconds: float = 60,
        poll_seconds: float = 2,
    ) -> Dict[str, Any]:
        created = self._memory.create_memories(
            container_tag,
            [
                {
                    "content": case.content,
                    "isStatic": case.is_static,
                    "metadata": {"kind": "consistency-matrix", "case": case.name},
                }
            ],
        )
        memory_ids = [
            item.get("id")
            for item in created.get("memories", [])
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        ]
        started = self._clock()
        first_seen_ms: Dict[str, Optional[float]] = {
            "profile": None,
            "memories": None,
            "hybrid": None,
        }
        attempts: Dict[str, int] = {name: 0 for name in first_seen_ms}
        errors: List[Dict[str, str]] = []
        query = f"Which stored fact contains the identifier {canary}?"

        while self._clock() - started < timeout_seconds:
            requests = {
                "profile": lambda: self._memory.profile(
                    container_tag,
                    query=query,
                    threshold=0.0,
                    include=["static", "dynamic", "buckets"],
                ),
                "memories": lambda: self._memory.search_memories(
                    query,
                    container_tag=container_tag,
                    search_mode="memories",
                    threshold=0.0,
                    limit=10,
                ),
                "hybrid": lambda: self._memory.search_memories(
                    query,
                    container_tag=container_tag,
                    search_mode="hybrid",
                    threshold=0.0,
                    limit=10,
                ),
            }
            for path, action in requests.items():
                if first_seen_ms[path] is not None:
                    continue
                attempts[path] += 1
                try:
                    response = action()
                    if contains_text(response, canary):
                        first_seen_ms[path] = round(
                            (self._clock() - started) * 1000, 1
                        )
                except Exception as error:
                    errors.append(
                        {"path": path, "type": type(error).__name__, "detail": str(error)[:300]}
                    )
            if all(value is not None for value in first_seen_ms.values()):
                break
            self._sleeper(poll_seconds)

        cleanup_errors: List[str] = []
        for memory_id in memory_ids:
            try:
                self._memory.forget_memory(
                    container_tag=container_tag,
                    memory_id=memory_id,
                    reason="consistency matrix cleanup",
                )
            except Exception as error:
                cleanup_errors.append(f"{type(error).__name__}: {str(error)[:200]}")

        return {
            "case": case.name,
            "contentChars": len(case.content),
            "isStatic": case.is_static,
            "firstSeenMs": first_seen_ms,
            "attempts": attempts,
            "errors": errors,
            "createdMemoryCount": len(memory_ids),
            "cleanupErrors": cleanup_errors,
        }

    def run_query_sensitivity(
        self,
        *,
        content: str,
        container_tag: str,
        canary: str,
        queries: Sequence[RetrievalQuery],
        threshold: float = 0.5,
    ) -> Dict[str, Any]:
        created = self._memory.create_memories(
            container_tag,
            [
                {
                    "content": content,
                    "isStatic": False,
                    "metadata": {"kind": "query-sensitivity"},
                }
            ],
        )
        memory_ids = [
            item.get("id")
            for item in created.get("memories", [])
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        ]
        observations: List[Dict[str, Any]] = []
        for query_case in queries:
            profile = self._memory.profile(
                container_tag,
                query=query_case.query,
                threshold=threshold,
                include=["static", "dynamic", "buckets"],
            )
            memories = self._memory.search_memories(
                query_case.query,
                container_tag=container_tag,
                search_mode="memories",
                threshold=threshold,
                limit=10,
            )
            hybrid = self._memory.search_memories(
                query_case.query,
                container_tag=container_tag,
                search_mode="hybrid",
                threshold=threshold,
                limit=10,
            )
            observations.append(
                {
                    "name": query_case.name,
                    "shouldMatch": query_case.should_match,
                    "profileContains": contains_text(profile, canary),
                    "memoriesContains": contains_text(memories, canary),
                    "hybridContains": contains_text(hybrid, canary),
                    "profileSearchCount": len(
                        ((profile.get("searchResults") or {}).get("results") or [])
                    ),
                    "memoriesCount": len(memories.get("results") or []),
                    "hybridCount": len(hybrid.get("results") or []),
                }
            )

        cleanup_errors: List[str] = []
        for memory_id in memory_ids:
            try:
                self._memory.forget_memory(
                    container_tag=container_tag,
                    memory_id=memory_id,
                    reason="query sensitivity cleanup",
                )
            except Exception as error:
                cleanup_errors.append(f"{type(error).__name__}: {str(error)[:200]}")
        return {
            "contentChars": len(content),
            "threshold": threshold,
            "queries": observations,
            "cleanupErrors": cleanup_errors,
        }
