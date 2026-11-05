"""Dependency-free client for the namespace-scoped Supermemory API v5 (Nov 2026).

Every method maps one-to-one onto an operation in the live v5 OpenAPI document
(https://api.supermemory.ai/openapi.json, ``info.version`` 5.0.0, fetched 2026-11-05).
The routes have **no** ``/v5`` prefix: scope lives in ``/ns/{namespace}/...``.

The client is intentionally thin. It validates the documented limits locally, so that a
bad call fails before any credits are spent, and it never renders credentials. Use it
from experiments, or as a readable reference for what the official SDKs send.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence
from urllib.parse import quote, urlencode

from .http import JsonTransport

JsonObject = Dict[str, Any]

NAMESPACE_PATTERN = re.compile(r"^[a-zA-Z0-9_:-]{1,100}$")
METADATA_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")
BUCKET_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

SEARCH_MODES = ("hybrid", "memories", "chunks")
RERANK_MODES = ("none", "order", "aggregate")
DREAMING_MODES = ("dynamic", "instant")
TASK_TYPES = ("memory", "superrag")
LIST_TYPES = ("documents", "chunks", "memories")
FEEDBACK_TYPES = ("bug", "feature_request", "docs", "other")
CONNECTOR_PROVIDERS = (
    "notion",
    "google-drive",
    "onedrive",
    "gmail",
    "github",
    "web-crawler",
    "s3",
    "granola",
)

# Documented defaults (v5). v4 used searchMode="memories" and threshold=0.6.
DEFAULT_SEARCH_MODE = "hybrid"
DEFAULT_THRESHOLD = 0.3


def validate_namespace(namespace: str) -> str:
    if not isinstance(namespace, str) or not NAMESPACE_PATTERN.match(namespace):
        raise ValueError(
            "namespace must match ^[a-zA-Z0-9_:-]+$ and be at most 100 characters"
        )
    return namespace


def _ns(namespace: str, suffix: str = "") -> str:
    return f"/ns/{quote(validate_namespace(namespace), safe='')}{suffix}"


def _seg(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("path identifiers must be non-empty strings")
    return quote(value, safe="")


def _query(params: Mapping[str, Any]) -> str:
    clean = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            value = ",".join(str(item) for item in value)
        elif isinstance(value, bool):
            value = "true" if value else "false"
        clean[key] = value
    return f"?{urlencode(clean)}" if clean else ""


def _check_metadata(metadata: Optional[Mapping[str, Any]]) -> None:
    if metadata is None:
        return
    for key, value in metadata.items():
        if not METADATA_KEY_PATTERN.match(key):
            raise ValueError(f"metadata key {key!r} has unsupported characters")
        if isinstance(value, Mapping):
            raise ValueError("metadata values cannot be nested objects")
        if isinstance(value, list) and not all(isinstance(item, str) for item in value):
            raise ValueError("metadata arrays must contain only strings")


def _check_choice(name: str, value: Optional[str], allowed: Sequence[str]) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f"{name} must be one of {', '.join(allowed)}")


def _filter_depth(node: Any, depth: int = 0) -> int:
    if not isinstance(node, Mapping):
        return depth
    operands = node.get("operands")
    if node.get("operator") in ("and", "or") and isinstance(operands, list):
        if len(operands) > 200:
            raise ValueError("a logical filter group accepts at most 200 operands")
        return max([_filter_depth(item, depth + 1) for item in operands] or [depth + 1])
    return depth


def check_filter(expression: Optional[Mapping[str, Any]]) -> None:
    """Validate the documented filter limits: 5 nested levels, 200 operands per group."""

    if expression is None:
        return
    if _filter_depth(expression) > 5:
        raise ValueError("filter expressions nest at most 5 and/or levels")


def eq(field: str, value: Any) -> JsonObject:
    return {"field": field, "operator": "eq", "value": value}


def all_of(*operands: Mapping[str, Any]) -> JsonObject:
    return {"operator": "and", "operands": list(operands)}


def any_of(*operands: Mapping[str, Any]) -> JsonObject:
    return {"operator": "or", "operands": list(operands)}


def result_text(result: Mapping[str, Any]) -> str:
    """Hybrid results carry either ``memory`` or ``chunk``. Branch on presence."""

    value = result.get("memory") or result.get("chunk") or ""
    return value if isinstance(value, str) else ""


def is_terminal(document: Mapping[str, Any], *, need_memories: bool = False) -> bool:
    """True when ``system.status`` is done/failed (and dreaming done, if requested)."""

    system = document.get("system") or {}
    status = system.get("status")
    if status == "failed":
        return True
    if status != "done":
        return False
    if need_memories:
        return system.get("dreamingStatus", "done") == "done"
    return True


class SupermemoryV5:
    """One method per v5 operation. ``transport`` must speak JSON over HTTPS."""

    def __init__(self, transport: JsonTransport) -> None:
        self._t = transport

    # ------------------------------------------------------------------ ingest
    def add(
        self,
        namespace: str,
        content: str,
        *,
        id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        group: Optional[Mapping[str, Any]] = None,
        supporting_context: Optional[str] = None,
        date: Optional[str] = None,
        dreaming: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> JsonObject:
        """``POST /ns/{ns}/document``. Same ``id`` again appends/diffs (diff-billed)."""

        if not content:
            raise ValueError("content is required")
        if id is not None and len(id) > 255:
            raise ValueError("id is at most 255 characters")
        if supporting_context is not None and len(supporting_context) > 1500:
            raise ValueError("supportingContext is at most 1500 characters")
        _check_metadata(metadata)
        _check_choice("dreaming", dreaming, DREAMING_MODES)
        _check_choice("taskType", task_type, TASK_TYPES)
        body: JsonObject = {"content": content}
        for key, value in (
            ("id", id),
            ("metadata", metadata),
            ("group", group),
            ("supportingContext", supporting_context),
            ("date", date),
            ("dreaming", dreaming),
            ("taskType", task_type),
        ):
            if value is not None:
                body[key] = value
        return self._t.request("POST", _ns(namespace, "/document"), body)

    def batch_add(
        self,
        namespace: str,
        documents: Sequence[Mapping[str, Any]],
        *,
        dreaming: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> JsonObject:
        """``POST /ns/{ns}/document/batch`` with 1–600 documents. Match outcomes by id."""

        if not 1 <= len(documents) <= 600:
            raise ValueError("batch accepts 1 to 600 documents")
        for document in documents:
            _check_metadata(document.get("metadata"))
        _check_choice("dreaming", dreaming, DREAMING_MODES)
        _check_choice("taskType", task_type, TASK_TYPES)
        body: JsonObject = {"documents": [dict(item) for item in documents]}
        if dreaming:
            body["dreaming"] = dreaming
        if task_type:
            body["taskType"] = task_type
        return self._t.request("POST", _ns(namespace, "/document/batch"), body)

    def upload_file(
        self,
        namespace: str,
        filename: str,
        content: bytes,
        content_type: str,
        *,
        id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        dreaming: Optional[str] = None,
        task_type: Optional[str] = None,
        replace: bool = False,
    ) -> JsonObject:
        """``POST /ns/{ns}/document/file`` (or ``/file/{id}`` to replace). 50 MB max.

        Multipart: ``metadata`` travels as a JSON *string*, not an object.
        """

        if len(content) > 50 * 1024 * 1024:
            raise ValueError("files are limited to 50 MB")
        _check_metadata(metadata)
        _check_choice("dreaming", dreaming, DREAMING_MODES)
        _check_choice("taskType", task_type, TASK_TYPES)
        fields: Dict[str, str] = {}
        if metadata is not None:
            fields["metadata"] = json.dumps(metadata)
        if dreaming:
            fields["dreaming"] = dreaming
        if task_type:
            fields["taskType"] = task_type
        if replace:
            if not id:
                raise ValueError("replace requires the document id")
            path = _ns(namespace, f"/document/file/{_seg(id)}")
        else:
            path = _ns(namespace, "/document/file")
        multipart = getattr(self._t, "request_multipart", None)
        if multipart is None:
            raise RuntimeError("transport does not support multipart uploads")
        return multipart(
            "POST", path, fields=fields, files={"file": (filename, content, content_type)}
        )

    def get_document(
        self, namespace: str, id: str, *, include: Sequence[str] = ()
    ) -> JsonObject:
        """``GET /ns/{ns}/document/{id}``; ``include`` ⊆ {chunks, memories}."""

        for item in include:
            _check_choice("include", item, ("chunks", "memories"))
        suffix = _query({"include": list(include) or None})
        return self._t.request("GET", _ns(namespace, f"/document/{_seg(id)}{suffix}"))

    def update_document(
        self,
        namespace: str,
        id: str,
        *,
        content: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        supporting_context: Optional[str] = None,
        date: Optional[str] = None,
    ) -> JsonObject:
        """``PATCH /ns/{ns}/document/{id}``: content replaces + reprocesses;
        metadata-only merges key by key without reindexing."""

        _check_metadata(metadata)
        body: JsonObject = {}
        for key, value in (
            ("content", content),
            ("metadata", metadata),
            ("supportingContext", supporting_context),
            ("date", date),
        ):
            if value is not None:
                body[key] = value
        if not body:
            raise ValueError("update needs at least one of content/metadata/supportingContext/date")
        return self._t.request("PATCH", _ns(namespace, f"/document/{_seg(id)}"), body)

    def delete_documents(self, namespace: str, ids: Sequence[str]) -> JsonObject:
        """``DELETE /ns/{ns}/document`` with 1–100 ids. Check ``errors`` for partial failure."""

        if not 1 <= len(ids) <= 100:
            raise ValueError("delete accepts 1 to 100 ids")
        return self._t.request("DELETE", _ns(namespace, "/document"), {"ids": list(ids)})

    # ------------------------------------------------------------------ recall
    def search(
        self,
        namespace: str,
        query: str,
        *,
        search_mode: Optional[str] = None,
        limit: Optional[int] = None,
        threshold: Optional[float] = None,
        rerank: Optional[str] = None,
        rewrite_query: Optional[bool] = None,
        filter: Optional[Mapping[str, Any]] = None,
        include: Optional[Mapping[str, bool]] = None,
    ) -> JsonObject:
        """``POST /ns/{ns}/search``. Omitted options take v5 defaults (hybrid, 0.3)."""

        if not query:
            raise ValueError("query is required")
        _check_choice("searchMode", search_mode, SEARCH_MODES)
        _check_choice("rerank", rerank, RERANK_MODES)
        if limit is not None and not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if threshold is not None and not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        check_filter(filter)
        body: JsonObject = {"query": query}
        for key, value in (
            ("searchMode", search_mode),
            ("limit", limit),
            ("threshold", threshold),
            ("rerank", rerank),
            ("rewriteQuery", rewrite_query),
            ("filter", filter),
            ("include", dict(include) if include else None),
        ):
            if value is not None:
                body[key] = value
        return self._t.request("POST", _ns(namespace, "/search"), body)

    def profile(
        self,
        namespace: str,
        *,
        filter: Optional[Mapping[str, Any]] = None,
        buckets: Optional[Sequence[str]] = None,
    ) -> JsonObject:
        """``POST /ns/{ns}/profile``. No query in v5; returns static/dynamic/buckets.

        The route can also return Markdown with ``Accept: text/markdown`` (not used here
        because this transport is JSON-only).
        """

        check_filter(filter)
        if buckets is not None and len(buckets) > 50:
            raise ValueError("at most 50 bucket names")
        body: JsonObject = {}
        if filter is not None:
            body["filter"] = filter
        if buckets is not None:
            body["buckets"] = list(buckets)
        return self._t.request("POST", _ns(namespace, "/profile"), body)

    def get_buckets(self, namespace: str) -> JsonObject:
        return self._t.request("GET", _ns(namespace, "/profile/buckets"))

    def set_buckets(self, namespace: str, buckets: Mapping[str, str]) -> JsonObject:
        """``PUT /ns/{ns}/profile/buckets``: add-only on top of org buckets."""

        if not 1 <= len(buckets) <= 50:
            raise ValueError("set 1 to 50 buckets per request")
        for name, description in buckets.items():
            if name in ("static", "dynamic") or not BUCKET_NAME_PATTERN.match(name):
                raise ValueError(f"invalid bucket name {name!r}")
            if len(description) > 2000:
                raise ValueError("bucket descriptions are at most 2000 characters")
        return self._t.request(
            "PUT", _ns(namespace, "/profile/buckets"), {"buckets": dict(buckets)}
        )

    def delete_buckets(self, namespace: str, names: Sequence[str]) -> JsonObject:
        if not 1 <= len(names) <= 50:
            raise ValueError("delete 1 to 50 buckets per request")
        return self._t.request(
            "DELETE", _ns(namespace, "/profile/buckets"), {"buckets": list(names)}
        )

    # ------------------------------------------------------------------ memories
    def get_memory(
        self,
        namespace: str,
        id: str,
        *,
        include: Sequence[str] = (),
        related_limit: Optional[int] = None,
    ) -> JsonObject:
        """``GET /ns/{ns}/memories/{id}``; ``include`` ⊆ {related, documents}."""

        for item in include:
            _check_choice("include", item, ("related", "documents"))
        suffix = _query({"include": list(include) or None, "relatedLimit": related_limit})
        return self._t.request("GET", _ns(namespace, f"/memories/{_seg(id)}{suffix}"))

    def forget(self, namespace: str, ids: Sequence[str]) -> JsonObject:
        """``DELETE /ns/{ns}/memories`` (1–500 ids). Soft delete; inspect ``errors``."""

        if not 1 <= len(ids) <= 500:
            raise ValueError("forget accepts 1 to 500 ids")
        return self._t.request("DELETE", _ns(namespace, "/memories"), {"ids": list(ids)})

    def forget_semantic(self, namespace: str, query: str, *, dry_run: bool) -> JsonObject:
        """``DELETE /ns/{ns}/memories/semantic``. ``dryRun`` is required by the API.

        Preferred flow: dry run → human/agent review → :meth:`forget` with the reviewed ids,
        because a second semantic run can drift from the preview.
        """

        if not 1 <= len(query) <= 2000:
            raise ValueError("query must be 1 to 2000 characters")
        return self._t.request(
            "DELETE",
            _ns(namespace, "/memories/semantic"),
            {"query": query, "dryRun": bool(dry_run)},
        )

    def list(
        self,
        namespace: str,
        type: str,
        *,
        limit: Optional[int] = None,
        page: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        filter: Optional[Mapping[str, Any]] = None,
        include: Optional[Mapping[str, bool]] = None,
    ) -> JsonObject:
        """``POST /ns/{ns}/list/{type}``: pagination in the query, filter/include in body."""

        _check_choice("type", type, LIST_TYPES)
        _check_choice("order", order, ("asc", "desc"))
        _check_choice("sort", sort, ("createdAt", "updatedAt", "position"))
        if limit is not None and not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        check_filter(filter)
        suffix = _query(
            {"limit": limit, "page": page, "cursor": cursor, "sort": sort, "order": order}
        )
        body: JsonObject = {}
        if filter is not None:
            body["filter"] = filter
        if include:
            body["include"] = dict(include)
        return self._t.request("POST", _ns(namespace, f"/list/{type}{suffix}"), body)

    def iterate(
        self, namespace: str, type: str, *, limit: int = 100, max_pages: int = 50, **kwargs: Any
    ) -> Iterator[JsonObject]:
        """Follow ``pagination.nextCursor`` (2026-11-02) until ``hasMore`` is false."""

        cursor: Optional[str] = None
        for _ in range(max_pages):
            page = self.list(namespace, type, limit=limit, cursor=cursor, **kwargs)
            for item in page.get(type) or []:
                yield item
            pagination = page.get("pagination") or {}
            cursor = pagination.get("nextCursor")
            if not pagination.get("hasMore") or not cursor:
                return

    def memory_counts(self, namespace: str, document_ids: Sequence[str]) -> JsonObject:
        if not 1 <= len(document_ids) <= 100:
            raise ValueError("memory-counts accepts 1 to 100 ids")
        return self._t.request(
            "POST",
            _ns(namespace, "/list/documents/memory-counts"),
            {"ids": list(document_ids)},
        )

    # ------------------------------------------------------------------ inferred review
    # Documented under the legacy path family; namespace is passed as containerTag.
    def list_inferred(self, namespace: str) -> JsonObject:
        return self._t.request(
            "GET", f"/v3/container-tags/{_seg(validate_namespace(namespace))}/inferred"
        )

    def review_inferred(self, namespace: str, memory_id: str, action: str) -> JsonObject:
        _check_choice("action", action, ("approve", "decline", "undo"))
        return self._t.request(
            "POST",
            f"/v3/container-tags/{_seg(validate_namespace(namespace))}/inferred/"
            f"{_seg(memory_id)}/review",
            {"action": action},
        )

    # ------------------------------------------------------------------ namespaces
    def list_namespaces(
        self, *, page: Optional[int] = None, limit: Optional[int] = None, q: Optional[str] = None
    ) -> JsonObject:
        return self._t.request("GET", f"/namespaces{_query({'page': page, 'limit': limit, 'q': q})}")

    def get_namespace(self, namespace: str) -> JsonObject:
        return self._t.request("GET", _ns(namespace))

    def set_supporting_context(self, namespace: str, text: Optional[str]) -> JsonObject:
        if text is not None and len(text) > 1500:
            raise ValueError("supportingContext is at most 1500 characters")
        return self._t.request("PATCH", _ns(namespace), {"supportingContext": text})

    def delete_namespace(self, namespace: str, *, move_to: Optional[str] = None) -> JsonObject:
        """``DELETE /ns/{ns}`` (permanent) or ``?moveTo=`` (queued move).

        Footgun guard: ``moveTo`` is a *query* parameter. Sent in a JSON body it is
        ignored and the namespace is permanently deleted, so this method never sends a body.
        """

        suffix = _query({"moveTo": validate_namespace(move_to) if move_to else None})
        return self._t.request("DELETE", _ns(namespace) + suffix)

    # ------------------------------------------------------------------ org / connectors
    def get_organization(self) -> JsonObject:
        return self._t.request("GET", "/organization")

    def list_connectors(self, namespace: Optional[str] = None) -> JsonObject:
        if namespace is None:
            return self._t.request("GET", "/connectors")
        return self._t.request("GET", _ns(namespace, "/connectors"))

    def create_connector(
        self,
        namespace: str,
        provider: str,
        *,
        redirect_url: Optional[str] = None,
        document_limit: Optional[int] = None,
        config: Optional[Mapping[str, Any]] = None,
    ) -> JsonObject:
        _check_choice("provider", provider, CONNECTOR_PROVIDERS)
        if document_limit is not None and not 1 <= document_limit <= 10000:
            raise ValueError("documentLimit must be between 1 and 10000")
        body: JsonObject = {"provider": provider}
        for key, value in (
            ("redirectUrl", redirect_url),
            ("documentLimit", document_limit),
            ("config", config),
        ):
            if value is not None:
                body[key] = value
        return self._t.request("POST", _ns(namespace, "/connectors"), body)

    def sync_connector(self, namespace: str, connector_id: str) -> JsonObject:
        return self._t.request("POST", _ns(namespace, f"/connectors/{_seg(connector_id)}/sync"))

    def delete_connector(
        self, namespace: str, connector_id: str, *, delete_documents: bool = True
    ) -> JsonObject:
        suffix = _query({"deleteDocuments": delete_documents})
        return self._t.request("DELETE", _ns(namespace, f"/connectors/{_seg(connector_id)}{suffix}"))


def memory_texts(results: Iterable[Mapping[str, Any]]) -> List[str]:
    return [text for text in (result_text(item) for item in results) if text]
