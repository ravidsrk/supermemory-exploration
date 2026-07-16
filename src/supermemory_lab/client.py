"""Explicit wrapper over the hosted Supermemory v3/v4 endpoints under test."""

import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import quote

from .http import JsonObject, JsonTransport


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

    def update_memory(
        self,
        *,
        container_tag: str,
        new_content: str,
        memory_id: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> JsonObject:
        return self._transport.request(
            "PATCH",
            "/v4/memories",
            _without_none(
                {
                    "id": memory_id,
                    "content": content,
                    "containerTag": container_tag,
                    "newContent": new_content,
                    "metadata": dict(metadata) if metadata is not None else None,
                }
            ),
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
