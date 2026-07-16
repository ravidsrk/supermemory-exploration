"""Explicit wrapper over the hosted Supermemory v3/v4 endpoints under test."""

import json
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import quote

from .http import JsonObject, JsonTransport


_UNSET = object()


def _without_none(values: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


class SupermemoryClient:
    def __init__(self, transport: JsonTransport) -> None:
        self._transport = transport

    def add_document(
        self,
        content: str,
        *,
        container_tag: Optional[str] = None,
        custom_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        entity_context: Optional[str] = None,
        dreaming: Optional[str] = None,
        filter_by_metadata: Optional[Mapping[str, Any]] = None,
        task_type: Optional[str] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v3/documents",
            _without_none(
                {
                    "content": content,
                    "containerTag": container_tag,
                    "customId": custom_id,
                    "metadata": dict(metadata) if metadata is not None else None,
                    "entityContext": entity_context,
                    "dreaming": dreaming,
                    "filterByMetadata": (
                        dict(filter_by_metadata)
                        if filter_by_metadata is not None
                        else None
                    ),
                    "taskType": task_type,
                }
            ),
        )

    def get_document(self, document_id: str) -> JsonObject:
        return self._transport.request(
            "GET", f"/v3/documents/{quote(document_id, safe='')}"
        )

    def wait_for_document(
        self,
        document_id: str,
        *,
        timeout_seconds: float = 120.0,
        poll_seconds: float = 2.0,
    ) -> JsonObject:
        deadline = time.monotonic() + timeout_seconds
        last: JsonObject = {}
        while time.monotonic() < deadline:
            last = self.get_document(document_id)
            status = last.get("status")
            if status == "done":
                return last
            if status == "failed":
                raise RuntimeError(f"document {document_id} processing failed")
            time.sleep(poll_seconds)
        raise TimeoutError(
            f"document {document_id} did not finish; last status={last.get('status')}"
        )

    def list_documents(
        self,
        *,
        container_tags: Optional[Sequence[str]] = None,
        limit: int = 50,
        page: int = 1,
        sort: str = "createdAt",
        order: str = "desc",
        filters: Optional[Mapping[str, Any]] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v3/documents/list",
            _without_none(
                {
                    "containerTags": list(container_tags)
                    if container_tags is not None
                    else None,
                    "limit": limit,
                    "page": page,
                    "sort": sort,
                    "order": order,
                    "filters": dict(filters) if filters is not None else None,
                }
            ),
        )

    def update_document(
        self,
        document_id: str,
        *,
        content: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> JsonObject:
        return self._transport.request(
            "PATCH",
            f"/v3/documents/{quote(document_id, safe='')}",
            _without_none(
                {
                    "content": content,
                    "metadata": dict(metadata) if metadata is not None else None,
                }
            ),
        )

    def delete_document(self, document_id: str) -> JsonObject:
        return self._transport.request(
            "DELETE", f"/v3/documents/{quote(document_id, safe='')}"
        )

    def search_documents(
        self,
        query: str,
        *,
        container_tags: Optional[Sequence[str]] = None,
        limit: int = 10,
        chunk_threshold: Optional[float] = None,
        document_threshold: Optional[float] = None,
        rerank: bool = False,
        rewrite_query: bool = False,
        include_full_docs: bool = False,
        include_summary: bool = False,
        only_matching_chunks: bool = False,
        filters: Optional[Mapping[str, Any]] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v3/search",
            _without_none(
                {
                    "q": query,
                    "containerTags": list(container_tags)
                    if container_tags is not None
                    else None,
                    "limit": limit,
                    "chunkThreshold": chunk_threshold,
                    "documentThreshold": document_threshold,
                    "rerank": rerank,
                    "rewriteQuery": rewrite_query,
                    "includeFullDocs": include_full_docs,
                    "includeSummary": include_summary,
                    "onlyMatchingChunks": only_matching_chunks,
                    "filters": dict(filters) if filters is not None else None,
                }
            ),
        )

    def search_memories(
        self,
        query: str,
        *,
        container_tag: str,
        search_mode: str = "memories",
        limit: int = 10,
        threshold: float = 0.5,
        rerank: bool = False,
        rewrite_query: bool = False,
        filters: Optional[Mapping[str, Any]] = None,
        include: Optional[Mapping[str, bool]] = None,
        aggregate: Optional[bool] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v4/search",
            _without_none(
                {
                    "q": query,
                    "containerTag": container_tag,
                    "searchMode": search_mode,
                    "limit": limit,
                    "threshold": threshold,
                    "rerank": rerank,
                    "rewriteQuery": rewrite_query,
                    "filters": dict(filters) if filters is not None else None,
                    "include": dict(include) if include is not None else None,
                    "aggregate": aggregate,
                }
            ),
        )

    def wait_for_memory(
        self,
        query: str,
        *,
        container_tag: str,
        search_mode: str = "hybrid",
        timeout_seconds: float = 60.0,
        poll_seconds: float = 2.0,
        limit: int = 10,
        threshold: float = 0.0,
        required_text: Optional[str] = None,
    ) -> JsonObject:
        """Poll until a newly written memory becomes searchable.

        Hosted writes can be accepted before their memory representation is visible to
        every search mode. Callers that need read-after-write semantics should use this
        explicit barrier instead of sleeping for an assumed indexing duration.
        """

        deadline = time.monotonic() + timeout_seconds
        attempts = 0
        last: JsonObject = {}
        while time.monotonic() < deadline:
            attempts += 1
            last = self.search_memories(
                query,
                container_tag=container_tag,
                search_mode=search_mode,
                limit=limit,
                threshold=threshold,
            )
            results = last.get("results")
            text_visible = required_text is None or required_text.casefold() in json.dumps(
                results, ensure_ascii=False, default=str
            ).casefold()
            if isinstance(results, list) and results and text_visible:
                last["_pollAttempts"] = attempts
                return last
            time.sleep(poll_seconds)
        raise TimeoutError(
            f"memory did not become searchable in {container_tag}; attempts={attempts}; "
            f"required_text={bool(required_text)}"
        )

    def profile(
        self,
        container_tag: str,
        *,
        query: Optional[str] = None,
        threshold: Optional[float] = None,
        filters: Optional[Mapping[str, Any]] = None,
        include: Optional[Sequence[str]] = None,
        buckets: Optional[Sequence[str]] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v4/profile",
            _without_none(
                {
                    "containerTag": container_tag,
                    "q": query,
                    "threshold": threshold,
                    "filters": dict(filters) if filters is not None else None,
                    "include": list(include) if include is not None else None,
                    "buckets": list(buckets) if buckets is not None else None,
                }
            ),
        )

    def list_profile_buckets(self, container_tag: str) -> JsonObject:
        return self._transport.request(
            "POST", "/v4/profile/buckets", {"containerTag": container_tag}
        )

    def suggest_profile_buckets(self) -> JsonObject:
        """Ask Supermemory to propose org-level profile bucket definitions."""

        return self._transport.request("POST", "/v3/settings/suggest-buckets", {})

    def get_container_settings(self, container_tag: str) -> JsonObject:
        return self._transport.request(
            "GET", f"/v3/container-tags/{quote(container_tag, safe='')}"
        )

    def update_container_settings(
        self,
        container_tag: str,
        *,
        name: Any = _UNSET,
        entity_context: Any = _UNSET,
        memory_filesystem_paths: Any = _UNSET,
        profile_buckets: Any = _UNSET,
    ) -> JsonObject:
        """Update per-container extraction settings.

        ``None`` is meaningful for nullable fields, so a private sentinel distinguishes
        an omitted setting from an explicit request to clear it.
        """

        payload: Dict[str, Any] = {}
        if name is not _UNSET:
            payload["name"] = name
        if entity_context is not _UNSET:
            payload["entityContext"] = entity_context
        if memory_filesystem_paths is not _UNSET:
            payload["memoryFilesystemPaths"] = (
                list(memory_filesystem_paths)
                if memory_filesystem_paths is not None
                else None
            )
        if profile_buckets is not _UNSET:
            payload["profileBuckets"] = (
                [dict(bucket) for bucket in profile_buckets]
                if profile_buckets is not None
                else None
            )
        return self._transport.request(
            "PATCH", f"/v3/container-tags/{quote(container_tag, safe='')}", payload
        )

    def delete_container(self, container_tag: str) -> JsonObject:
        return self._transport.request(
            "DELETE", f"/v3/container-tags/{quote(container_tag, safe='')}"
        )

    def merge_containers(
        self, container_tags: Sequence[str], *, target_container_tag: str
    ) -> JsonObject:
        if len(container_tags) != 2:
            raise ValueError("container merge requires exactly two source tags")
        return self._transport.request(
            "POST",
            "/v3/container-tags/merge",
            {
                "containerTags": list(container_tags),
                "targetContainerTag": target_container_tag,
            },
        )

    def get_container_merge_status(self, merge_id: str) -> JsonObject:
        return self._transport.request(
            "GET", f"/v3/container-tags/merge/{quote(merge_id, safe='')}"
        )

    def wait_for_container_merge(
        self,
        merge_id: str,
        *,
        timeout_seconds: float = 120.0,
        poll_seconds: float = 2.0,
    ) -> JsonObject:
        deadline = time.monotonic() + timeout_seconds
        last: JsonObject = {}
        while time.monotonic() < deadline:
            last = self.get_container_merge_status(merge_id)
            status = str(last.get("status", "")).lower()
            if status in {"completed", "complete", "done", "succeeded", "success"}:
                return last
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(
                    f"container merge {merge_id} failed with status={status}"
                )
            time.sleep(poll_seconds)
        raise TimeoutError(
            f"container merge {merge_id} did not finish; status={last.get('status')}"
        )

    def list_inferred_memories(self, container_tag: str) -> JsonObject:
        return self._transport.request(
            "GET",
            f"/v3/container-tags/{quote(container_tag, safe='')}/inferred",
        )

    def review_inferred_memory(
        self, container_tag: str, memory_id: str, *, action: str
    ) -> JsonObject:
        if action not in {"approve", "decline", "undo"}:
            raise ValueError("review action must be approve, decline, or undo")
        return self._transport.request(
            "POST",
            (
                f"/v3/container-tags/{quote(container_tag, safe='')}/inferred/"
                f"{quote(memory_id, safe='')}/review"
            ),
            {"action": action},
        )

    def wait_for_profile(
        self,
        container_tag: str,
        *,
        query: Optional[str] = None,
        timeout_seconds: float = 30.0,
        poll_seconds: float = 2.0,
    ) -> JsonObject:
        """Poll until a profile exposes at least one static, dynamic, or bucket item."""

        deadline = time.monotonic() + timeout_seconds
        attempts = 0
        while time.monotonic() < deadline:
            attempts += 1
            response = self.profile(
                container_tag,
                query=query,
                threshold=0.0,
                include=["static", "dynamic", "buckets"],
            )
            profile = response.get("profile")
            profile = profile if isinstance(profile, Mapping) else {}
            has_values = any(
                isinstance(profile.get(name), list) and bool(profile.get(name))
                for name in ("static", "dynamic")
            )
            buckets = profile.get("buckets")
            if isinstance(buckets, Mapping):
                has_values = has_values or any(
                    isinstance(value, list) and bool(value)
                    for value in buckets.values()
                )
            if has_values:
                response["_pollAttempts"] = attempts
                return response
            time.sleep(poll_seconds)
        raise TimeoutError(
            f"profile did not become visible in {container_tag}; attempts={attempts}"
        )

    def create_scoped_key(
        self,
        container_tag: Optional[str] = None,
        *,
        container_tags: Optional[Sequence[str]] = None,
        name: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit_max: Optional[int] = None,
        rate_limit_time_window: Optional[int] = None,
    ) -> JsonObject:
        if container_tag is not None and container_tags is not None:
            raise ValueError("provide container_tag or container_tags, not both")
        if container_tag is None and not container_tags:
            raise ValueError("at least one scoped container tag is required")
        return self._transport.request(
            "POST",
            "/v3/auth/scoped-key",
            _without_none(
                {
                    "containerTag": container_tag,
                    "containerTags": list(container_tags)
                    if container_tags is not None
                    else None,
                    "name": name,
                    "expiresInDays": expires_in_days,
                    "rateLimitMax": rate_limit_max,
                    "rateLimitTimeWindow": rate_limit_time_window,
                }
            ),
        )

    def revoke_scoped_key(self, key_id: str) -> JsonObject:
        return self._transport.request(
            "DELETE", f"/v3/auth/scoped-key/{quote(key_id, safe='')}"
        )

    def create_connection(
        self,
        provider: str,
        *,
        container_tags: Optional[Sequence[str]] = None,
        redirect_url: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        document_limit: Optional[int] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            f"/v3/connections/{quote(provider, safe='')}",
            _without_none(
                {
                    "containerTags": list(container_tags)
                    if container_tags is not None
                    else None,
                    "redirectUrl": redirect_url,
                    "metadata": dict(metadata) if metadata is not None else None,
                    "documentLimit": document_limit,
                }
            ),
        )

    def list_connections(
        self, *, container_tags: Optional[Sequence[str]] = None
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v3/connections/list",
            _without_none(
                {
                    "containerTags": list(container_tags)
                    if container_tags is not None
                    else None
                }
            ),
        )

    def list_connection_documents(
        self, provider: str, *, container_tags: Sequence[str]
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            f"/v3/connections/{quote(provider, safe='')}/documents",
            {"containerTags": list(container_tags)},
        )

    def delete_connection(self, connection_id: str) -> JsonObject:
        return self._transport.request(
            "DELETE", f"/v3/connections/{quote(connection_id, safe='')}"
        )

    def create_memories(
        self,
        container_tag: str,
        memories: Iterable[Mapping[str, Any]],
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v4/memories",
            {"containerTag": container_tag, "memories": [dict(m) for m in memories]},
        )

    def list_memory_entries(
        self,
        container_tags: Sequence[str],
        *,
        filters: Optional[Mapping[str, Any]] = None,
        limit: int = 50,
        page: int = 1,
        sort: str = "createdAt",
        order: str = "desc",
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v4/memories/list",
            _without_none(
                {
                    "containerTags": list(container_tags),
                    "filters": dict(filters) if filters is not None else None,
                    "limit": limit,
                    "page": page,
                    "sort": sort,
                    "order": order,
                }
            ),
        )

    def update_memory(
        self,
        *,
        container_tag: str,
        new_content: str,
        memory_id: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        forget_after: Any = _UNSET,
        forget_reason: Any = _UNSET,
        temporal_context: Any = _UNSET,
    ) -> JsonObject:
        payload: Dict[str, Any] = _without_none(
            {
                "id": memory_id,
                "content": content,
                "containerTag": container_tag,
                "newContent": new_content,
                "metadata": dict(metadata) if metadata is not None else None,
            }
        )
        if forget_after is not _UNSET:
            payload["forgetAfter"] = forget_after
        if forget_reason is not _UNSET:
            payload["forgetReason"] = forget_reason
        if temporal_context is not _UNSET:
            payload["temporalContext"] = (
                dict(temporal_context) if temporal_context is not None else None
            )
        return self._transport.request(
            "PATCH",
            "/v4/memories",
            payload,
        )

    def forget_memory(
        self,
        *,
        container_tag: str,
        memory_id: Optional[str] = None,
        content: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> JsonObject:
        return self._transport.request(
            "DELETE",
            "/v4/memories",
            _without_none(
                {
                    "id": memory_id,
                    "content": content,
                    "containerTag": container_tag,
                    "reason": reason,
                }
            ),
        )

    def forget_matching(
        self,
        query: str,
        *,
        container_tag: str,
        dry_run: bool = True,
        threshold: float = 0.5,
        max_forget: int = 100,
        reason: Optional[str] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v4/memories/forget-matching",
            _without_none(
                {
                    "query": query,
                    "containerTag": container_tag,
                    "dryRun": dry_run,
                    "threshold": threshold,
                    "maxForget": max_forget,
                    "reason": reason,
                }
            ),
        )

    def add_conversation(
        self,
        conversation_id: str,
        messages: Sequence[Mapping[str, Any]],
        *,
        container_tags: Optional[Sequence[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        entity_context: Optional[str] = None,
    ) -> JsonObject:
        return self._transport.request(
            "POST",
            "/v4/conversations",
            _without_none(
                {
                    "conversationId": conversation_id,
                    "messages": [dict(message) for message in messages],
                    "containerTags": list(container_tags)
                    if container_tags is not None
                    else None,
                    "metadata": dict(metadata) if metadata is not None else None,
                    "entityContext": entity_context,
                }
            ),
        )
