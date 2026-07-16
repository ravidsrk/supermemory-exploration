"""Lifecycle agents for expiring state and workspace consolidation."""

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from .client import SupermemoryClient


@dataclass(frozen=True)
class MergeRequest:
    merge_id: str
    source_tags: Sequence[str]
    target_tag: str


class EphemeralIncidentAgent:
    """Stores operational state with a server-enforced retention horizon."""

    def __init__(self, memory: SupermemoryClient, *, container_tag: str) -> None:
        self._memory = memory
        self._container_tag = container_tag

    def create_lease(
        self,
        content: str,
        *,
        forget_after: str,
        reason: str,
        event_dates: Optional[Sequence[str]] = None,
    ) -> Mapping[str, Any]:
        record = {
            "content": content,
            "isStatic": False,
            "metadata": {"kind": "ephemeral-incident-lease"},
            "forgetAfter": forget_after,
            "forgetReason": reason,
        }
        if event_dates is not None:
            record["temporalContext"] = {"eventDate": list(event_dates)}
        return self._memory.create_memories(self._container_tag, [record])

    def cancel_expiry(self, memory_id: str, *, content: str) -> Mapping[str, Any]:
        return self._memory.update_memory(
            memory_id=memory_id,
            container_tag=self._container_tag,
            new_content=content,
            forget_after=None,
            forget_reason=None,
            metadata={
                "kind": "retained-incident-postmortem",
                "expiryCancelled": True,
            },
        )

    def search(
        self, query: str, *, include_forgotten: bool = False
    ) -> Mapping[str, Any]:
        return self._memory.search_memories(
            query,
            container_tag=self._container_tag,
            search_mode="memories",
            threshold=0.0,
            limit=20,
            include={"forgottenMemories": True} if include_forgotten else None,
        )


class WorkspaceConsolidationAgent:
    """Queues an audited two-container merge into a chosen target workspace."""

    def __init__(self, memory: SupermemoryClient) -> None:
        self._memory = memory

    def request_merge(self, source_tag: str, target_tag: str) -> MergeRequest:
        response = self._memory.merge_containers(
            [source_tag, target_tag], target_container_tag=target_tag
        )
        merge_id = response.get("mergeId")
        if not isinstance(merge_id, str) or not merge_id:
            raise RuntimeError("merge request did not return mergeId")
        if response.get("status") != "queued":
            raise RuntimeError("merge request was not acknowledged as queued")
        return MergeRequest(merge_id, [source_tag, target_tag], target_tag)

    def status(self, request: MergeRequest) -> Mapping[str, Any]:
        return self._memory.get_container_merge_status(request.merge_id)
