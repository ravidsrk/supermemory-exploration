"""November 2026 contract-refresh probe for the namespace-scoped v5 API.

The probe answers a narrow set of questions raised by the October 2026 v5 launch:

* Does the v5 write → poll → search/profile/list loop work in one synthetic namespace?
* Does omitting ``searchMode`` behave as the documented ``hybrid`` default?
* Does v5 list expose the documented cursor pagination fields?
* Do legacy v4 search and direct v4 memory writes still interoperate with v5 data?
* Does semantic forget support a side-effect-free dry run?
* Does exact document delete plus permanent namespace delete leave nothing behind?

It never calls ``/feedback`` (that would page the vendor), never mints or revokes keys,
never touches organization settings, and only records shapes, statuses, and synthetic
canary matches. Every created resource lives in one ``lab:v5refresh:*`` namespace that
is deleted at the end.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Dict, List, Mapping, Optional
from urllib.parse import quote

from .http import ApiError, JsonTransport


def _ns_path(namespace: str, suffix: str = "") -> str:
    return f"/ns/{quote(namespace, safe='')}{suffix}"


def _result_kinds(results: List[Mapping[str, Any]]) -> Dict[str, int]:
    kinds = {"memory": 0, "chunk": 0, "other": 0}
    for item in results:
        if isinstance(item.get("memory"), str) and item.get("memory"):
            kinds["memory"] += 1
        elif isinstance(item.get("chunk"), str) and item.get("chunk"):
            kinds["chunk"] += 1
        else:
            kinds["other"] += 1
    return kinds


def _contains(results: List[Mapping[str, Any]], canary: str) -> bool:
    for item in results:
        for key in ("memory", "chunk", "content"):
            value = item.get(key)
            if isinstance(value, str) and canary in value:
                return True
    return False


@dataclass
class StepResult:
    name: str
    ok: bool
    status: Optional[int] = None
    detail: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "status": self.status, **self.detail}


class V5RefreshProbe:
    def __init__(
        self,
        transport: JsonTransport,
        *,
        namespace: str,
        canary: str,
        sleep: Callable[[float], None] = time.sleep,
        poll_seconds: float = 3.0,
        timeout_seconds: float = 120.0,
    ) -> None:
        if not namespace.startswith("lab:v5refresh:"):
            raise ValueError("refresh probe namespace must be a synthetic lab:v5refresh: tag")
        self._t = transport
        self._ns = namespace
        self._canary = canary
        self._sleep = sleep
        self._poll = poll_seconds
        self._timeout = timeout_seconds
        self.steps: List[StepResult] = []

    # -- helpers -----------------------------------------------------------------
    def _call(self, name: str, method: str, path: str, body: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            response = self._t.request(method, path, body)
        except ApiError as error:
            self.steps.append(StepResult(name, False, error.status, {"error": error.detail[:200]}))
            return None
        return response

    def _record(self, name: str, ok: bool, **detail: Any) -> None:
        self.steps.append(StepResult(name, ok, 200 if ok else None, detail))

    # -- probe -------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        doc_id = f"refresh-{self._canary.lower()}"
        legacy_memory_canary = f"{self._canary}_LEGACY"
        try:
            self._v5_write_and_poll(doc_id)
            self._v5_search()
            self._v5_profile()
            self._v5_list()
            self._legacy_interop(legacy_memory_canary)
            self._semantic_forget_dry_run()
        finally:
            self._cleanup(doc_id)
        return {
            "namespace": self._ns,
            "steps": [step.as_dict() for step in self.steps],
            "passed": all(step.ok for step in self.steps),
        }

    def _v5_write_and_poll(self, doc_id: str) -> None:
        body = {
            "id": doc_id,
            "content": (
                f"Field-lab refresh canary {self._canary}. The synthetic release train "
                "codename is Heliotrope and its owner prefers written status updates."
            ),
            "metadata": {"source": "field-lab-refresh"},
            "dreaming": "instant",
        }
        response = self._call("v5.add_document", "POST", _ns_path(self._ns, "/document"), body)
        if response is None:
            return
        self._record(
            "v5.add_document",
            response.get("id") == doc_id and response.get("status") in {
                "unknown", "queued", "extracting", "chunking", "embedding", "indexing", "done"
            },
            responseKeys=sorted(response),
            initialStatus=response.get("status"),
        )
        started = time.monotonic()
        last: Optional[Dict[str, Any]] = None
        polls = 0
        while time.monotonic() - started < self._timeout:
            polls += 1
            last = self._call(
                "v5.poll_document", "GET", _ns_path(self._ns, f"/document/{quote(doc_id, safe='')}")
            )
            if last is None:
                return
            status = (last.get("system") or {}).get("status")
            if status in {"done", "failed"}:
                break
            self._sleep(self._poll)
        system = (last or {}).get("system") or {}
        self._record(
            "v5.poll_document",
            system.get("status") == "done",
            finalStatus=system.get("status"),
            dreamingStatus=system.get("dreamingStatus"),
            polls=polls,
            elapsedSeconds=round(time.monotonic() - started, 1),
            systemKeys=sorted(system),
        )

    def _v5_search(self) -> None:
        path = _ns_path(self._ns, "/search")
        default = self._call("v5.search_default", "POST", path, {"query": f"{self._canary} release codename"})
        if default is not None:
            results = default.get("results") or []
            self._record(
                "v5.search_default",
                _contains(results, self._canary) or _contains(results, "Heliotrope"),
                resultKinds=_result_kinds(results),
                topLevelKeys=sorted(default),
            )
        memories = self._call(
            "v5.search_memories",
            "POST",
            path,
            {"query": "What is the release train codename?", "searchMode": "memories", "threshold": 0.3},
        )
        if memories is not None:
            results = memories.get("results") or []
            self._record(
                "v5.search_memories",
                bool(results),
                resultKinds=_result_kinds(results),
                mentionsCodename=_contains(results, "Heliotrope"),
            )

    def _v5_profile(self) -> None:
        response = self._call("v5.profile", "POST", _ns_path(self._ns, "/profile"), {})
        if response is not None:
            self._record("v5.profile", True, topLevelKeys=sorted(response))

    def _v5_list(self) -> None:
        response = self._call(
            "v5.list_documents", "POST", _ns_path(self._ns, "/list/documents?limit=1"), {}
        )
        if response is not None:
            pagination = response.get("pagination") or {}
            self._record(
                "v5.list_documents",
                isinstance(response.get("documents"), list),
                documentCount=len(response.get("documents") or []),
                paginationKeys=sorted(pagination),
                hasCursorFields="nextCursor" in pagination and "hasMore" in pagination,
            )

    def _legacy_interop(self, legacy_canary: str) -> None:
        legacy = self._call(
            "legacy.v4_search",
            "POST",
            "/v4/search",
            {"q": f"{self._canary} release codename", "containerTag": self._ns, "searchMode": "hybrid"},
        )
        if legacy is not None:
            results = legacy.get("results") or []
            self._record(
                "legacy.v4_search_sees_v5_write",
                _contains(results, self._canary) or _contains(results, "Heliotrope"),
                resultCount=len(results),
            )
        created = self._call(
            "legacy.v4_direct_memory",
            "POST",
            "/v4/memories",
            {
                "containerTag": self._ns,
                "memories": [{"content": f"Legacy direct canary {legacy_canary} is teal.", "isStatic": False}],
            },
        )
        if created is None:
            return
        self._record("legacy.v4_direct_memory", True, responseKeys=sorted(created))
        started = time.monotonic()
        seen = False
        while time.monotonic() - started < 45:
            found = self._call(
                "v5.search_sees_legacy_memory",
                "POST",
                _ns_path(self._ns, "/search"),
                {"query": f"{legacy_canary} colour", "searchMode": "memories", "threshold": 0.3},
            )
            if found is None:
                return
            if _contains(found.get("results") or [], legacy_canary):
                seen = True
                break
            self._sleep(self._poll)
        self._record(
            "v5.search_sees_legacy_memory",
            seen,
            elapsedSeconds=round(time.monotonic() - started, 1),
        )

    def _semantic_forget_dry_run(self) -> None:
        response = self._call(
            "v5.semantic_forget_dry_run",
            "DELETE",
            _ns_path(self._ns, "/memories/semantic"),
            {"query": "the release train codename", "dryRun": True},
        )
        if response is not None:
            self._record(
                "v5.semantic_forget_dry_run",
                True,
                topLevelKeys=sorted(response),
                matchCount=len(response.get("matches") or []),
            )

    def _cleanup(self, doc_id: str) -> None:
        self._call("cleanup.delete_document", "DELETE", _ns_path(self._ns, "/document"), {"ids": [doc_id]})
        deleted = self._call("cleanup.delete_namespace", "DELETE", _ns_path(self._ns))
        if deleted is not None:
            self._record(
                "cleanup.delete_namespace",
                deleted.get("status") in {"deleted", "queued"},
                deleteStatus=deleted.get("status"),
            )
        try:
            self._t.request("GET", _ns_path(self._ns, f"/document/{quote(doc_id, safe='')}"))
            self._record("cleanup.verify_document_absent", False, note="document still readable")
        except ApiError as error:
            self.steps.append(
                StepResult("cleanup.verify_document_absent", error.status == 404, error.status)
            )
