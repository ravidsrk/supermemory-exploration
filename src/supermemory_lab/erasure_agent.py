"""Metadata-filtered retrieval and preview-gated memory erasure."""

from dataclasses import dataclass
from typing import Any, List, Mapping, Sequence

from .client import SupermemoryClient


def _candidate_rows(response: Mapping[str, Any], key: str) -> List[Mapping[str, Any]]:
    values = response.get(key)
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, Mapping)]


@dataclass(frozen=True)
class ErasurePreview:
    query: str
    candidates: List[Mapping[str, Any]]
    authorized: bool
    reason: str
    threshold: float


class GovernedErasureAgent:
    """Separates semantic discovery, deterministic approval, and mutation."""

    def __init__(self, memory: SupermemoryClient, *, container_tag: str) -> None:
        self._memory = memory
        self._container_tag = container_tag

    def filtered_search(
        self, query: str, filters: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        return self._memory.search_memories(
            query,
            container_tag=self._container_tag,
            search_mode="memories",
            threshold=0.0,
            limit=50,
            filters=filters,
        )

    def preview(
        self,
        query: str,
        *,
        required_tokens: Sequence[str],
        protected_tokens: Sequence[str],
        threshold: float = 0.5,
        max_candidates: int = 10,
    ) -> ErasurePreview:
        response = self._memory.forget_matching(
            query,
            container_tag=self._container_tag,
            dry_run=True,
            threshold=threshold,
            max_forget=max_candidates,
        )
        candidates = _candidate_rows(response, "candidates")
        texts = [str(candidate.get("memory", "")) for candidate in candidates]
        combined = "\n".join(texts).casefold()
        protected_hit = any(token.casefold() in combined for token in protected_tokens)
        required_present = all(
            token.casefold() in combined for token in required_tokens
        )
        count_matches = response.get("count") == len(candidates)
        within_cap = 0 < len(candidates) <= max_candidates
        authorized = (
            bool(response.get("dryRun"))
            and required_present
            and not protected_hit
            and count_matches
            and within_cap
        )
        if not candidates:
            reason = "preview returned no candidates"
        elif protected_hit:
            reason = "preview included a protected token"
        elif not required_present:
            reason = "preview omitted a required token"
        elif not count_matches:
            reason = "preview count did not match candidate rows"
        elif not within_cap:
            reason = "preview exceeded the application cap"
        elif not response.get("dryRun"):
            reason = "provider response was not a dry run"
        else:
            reason = "candidate set satisfies deterministic policy"
        return ErasurePreview(query, candidates, authorized, reason, threshold)

    def apply(self, preview: ErasurePreview, *, reason: str) -> Mapping[str, Any]:
        if not preview.authorized:
            raise PermissionError(f"erasure preview is not authorized: {preview.reason}")
        response = self._memory.forget_matching(
            preview.query,
            container_tag=self._container_tag,
            dry_run=False,
            threshold=preview.threshold,
            max_forget=len(preview.candidates),
            reason=reason,
        )
        preview_ids = {
            str(candidate.get("id"))
            for candidate in preview.candidates
            if candidate.get("id") is not None
        }
        forgotten = _candidate_rows(response, "forgotten")
        forgotten_ids = {
            str(candidate.get("id"))
            for candidate in forgotten
            if candidate.get("id") is not None
        }
        if forgotten_ids and not forgotten_ids.issubset(preview_ids):
            raise RuntimeError("apply mutated a memory outside the approved preview set")
        return response
