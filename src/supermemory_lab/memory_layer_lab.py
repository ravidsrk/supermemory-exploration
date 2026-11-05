"""Nov 2026 "Memory Layer for Agents" live feature suite against Supermemory API v5.

Each exercise covers one documented capability and records a shape-only result: status
codes, counts, timings, field presence, and synthetic-canary matches. It never records
user content, keys, or full responses. Everything lives in two synthetic namespaces,
``lab:mla:<run>`` and ``lab:mla:<run>:dst``, which are deleted at the end.

If the preflight read returns 401/403, every exercise is reported as ``blocked`` with the
reason, and the suite performs no writes.

Deliberately NOT exercised (side effects outside the sandbox): ``POST /feedback`` (pages
Supermemory staff), scoped-key minting/revocation, ``PATCH /organization`` (org-wide),
connector creation (OAuth/third-party), and inferred-memory review *decisions*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Dict, List, Optional

from .http import ApiError
from .v5 import SupermemoryV5, all_of, eq, is_terminal, result_text

JsonObject = Dict[str, Any]


@dataclass
class Exercise:
    key: str
    feature: str
    docs: str
    status: str = "pending"  # pass | fail | blocked | skipped
    http_status: Optional[int] = None
    detail: JsonObject = field(default_factory=dict)
    seconds: float = 0.0

    def as_dict(self) -> JsonObject:
        return {
            "exercise": self.key,
            "feature": self.feature,
            "docs": self.docs,
            "status": self.status,
            "httpStatus": self.http_status,
            "seconds": round(self.seconds, 2),
            "detail": self.detail,
        }


D = "https://supermemory.ai/docs/"

PLAN = [
    ("preflight", "Auth + namespace list (read-only)", D + "authentication"),
    ("add_instant", "Add text, dreaming=instant, auto-create namespace", D + "ingestion/add-memories"),
    ("add_dynamic", "Add text, dreaming=dynamic; time to status/dreamingStatus", D + "concepts/how-it-works"),
    ("add_superrag", "taskType=superrag (chunks only, no memories)", D + "concepts/super-rag"),
    ("add_url", "Ingest a URL as content", D + "concepts/content-types"),
    ("batch_add", "Batch add with metadata and ids", D + "ingestion/batch-ingest-historical-data"),
    ("upload_file", "Multipart file upload (Markdown)", D + "v5/api-reference/ingest/upload-file"),
    ("search_default", "Search with no options = hybrid / 0.3", D + "recall/search"),
    ("search_modes", "memories vs chunks vs hybrid result kinds", D + "recall/search"),
    ("search_threshold", "Threshold sweep 0.3 / 0.6 / 0.8", D + "recall/search"),
    ("search_filter", "Typed metadata filter (and/eq)", D + "concepts/filtering"),
    ("search_include", "include.related / include.documents", D + "concepts/graph-memory"),
    ("profile", "Profile static/dynamic/buckets", D + "recall/user-profiles"),
    ("buckets", "Namespace bucket set/get/delete", D + "user-profiles/buckets"),
    ("append_same_id", "Re-add same id appends/diffs", D + "ingestion/add-memories"),
    ("patch_replace", "PATCH replaces content; latest fact wins", D + "ingestion/document-operations"),
    ("metadata_only_patch", "Metadata-only PATCH (no reindex)", D + "ingestion/document-operations"),
    ("list_cursor", "Unified list + cursor pagination + include.content", D + "ingestion/document-operations"),
    ("get_document", "Get document include=chunks,memories", D + "v5/api-reference/content-management/get-document"),
    ("get_memory", "Get memory include=related", D + "v5/api-reference/content-management/get-memory"),
    ("memory_counts", "Count memories per document", D + "v5/api-reference/content-management/list-resources"),
    ("forget_ids", "Forget memories by id (soft)", D + "recall/memory-operations"),
    ("forget_semantic", "Semantic forget dry run → exact ids", D + "recall/memory-operations"),
    ("inferred_queue", "Inferred-memory review queue (read only)", D + "recall/memory-review"),
    ("namespace_settings", "Namespace get + supportingContext", D + "concepts/container-tags"),
    ("namespace_move", "DELETE ?moveTo= (queued move)", D + "concepts/container-tags"),
    ("organization", "GET /organization (read only)", D + "v5/api-reference/organization/get-organization-settings"),
    ("connectors_list", "List connectors (read only)", D + "connectors/overview"),
    ("cleanup", "Delete documents + namespaces, verify absent", D + "overview/security"),
]


class MemoryLayerLab:
    def __init__(
        self,
        client: SupermemoryV5,
        *,
        run_id: str,
        canary: str,
        poll_timeout: float = 120.0,
        poll_interval: float = 3.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.c = client
        self.ns = f"lab:mla:{run_id}"
        self.dst = f"lab:mla:{run_id}:dst"
        self.tmp = f"lab:mla:{run_id}:tmp"
        self.canary = canary
        self.poll_timeout = poll_timeout
        self.poll_interval = poll_interval
        self.sleep = sleep
        self.clock = clock
        self.exercises: Dict[str, Exercise] = {
            key: Exercise(key, feature, docs) for key, feature, docs in PLAN
        }
        self.state: JsonObject = {"docs": set(), "memoryIds": []}

    # ---------------------------------------------------------------- helpers
    def _run(self, key: str, fn: Callable[[], JsonObject]) -> None:
        ex = self.exercises[key]
        start = self.clock()
        try:
            detail = fn() or {}
            ex.status = detail.pop("_status", "pass")
            ex.detail = detail
        except ApiError as error:
            ex.status = "fail"
            ex.http_status = error.status
            ex.detail = {"error": error.detail[:200], "path": error.path}
        except Exception as error:  # record and continue; cleanup must still run
            ex.status = "fail"
            ex.detail = {"error": f"{type(error).__name__}: {str(error)[:200]}"}
        ex.seconds = self.clock() - start

    def _wait(self, doc_id: str, *, need_memories: bool) -> JsonObject:
        start = self.clock()
        last: JsonObject = {}
        while self.clock() - start < self.poll_timeout:
            last = self.c.get_document(self.ns, doc_id)
            if is_terminal(last, need_memories=need_memories):
                break
            self.sleep(self.poll_interval)
        system = last.get("system") or {}
        return {
            "status": system.get("status"),
            "dreamingStatus": system.get("dreamingStatus"),
            "waitSeconds": round(self.clock() - start, 2),
        }

    def _hit(self, response: JsonObject, needle: str) -> bool:
        return any(needle in result_text(item) for item in response.get("results") or [])

    @staticmethod
    def _kinds(response: JsonObject) -> JsonObject:
        kinds = {"memory": 0, "chunk": 0}
        for item in response.get("results") or []:
            if item.get("memory"):
                kinds["memory"] += 1
            elif item.get("chunk"):
                kinds["chunk"] += 1
        return kinds

    def _add(self, doc_id: str, content: str, **kwargs: Any) -> JsonObject:
        response = self.c.add(self.ns, content, id=doc_id, **kwargs)
        self.state["docs"].add(doc_id)
        return response

    # ---------------------------------------------------------------- exercises
    def preflight(self) -> JsonObject:
        response = self.c.list_namespaces(limit=1)
        return {"namespacesField": "namespaces" in response, "paginationField": "pagination" in response}

    def add_instant(self) -> JsonObject:
        doc = f"{self.canary}-pref"
        added = self._add(
            doc,
            f"Profile note {self.canary}: Riya prefers concise answers, works in IST, "
            f"and is the tech lead for project Halcyon.",
            dreaming="instant",
            metadata={"kind": "preference", "team": "eng"},
        )
        waited = self._wait(doc, need_memories=True)
        found = self.c.search(self.ns, "what timezone does Riya work in?", search_mode="memories")
        return {
            "responseHasId": bool(added.get("id")),
            "echoedCustomId": added.get("id") == doc,
            **waited,
            "memoryRecallAfterInstant": len(found.get("results") or []),
        }

    def add_dynamic(self) -> JsonObject:
        doc = f"{self.canary}-dyn"
        self._add(
            doc,
            f"Session {self.canary}: Riya said the Halcyon launch moved to March and "
            f"she now prefers async standups.",
            dreaming="dynamic",
            metadata={"kind": "conversation", "team": "eng"},
        )
        return self._wait(doc, need_memories=True)

    def add_superrag(self) -> JsonObject:
        doc = f"{self.canary}-rag"
        self._add(
            doc,
            f"Refund policy {self.canary}: refunds are issued within 14 days of purchase "
            f"for annual plans only.",
            task_type="superrag",
            metadata={"kind": "policy"},
        )
        waited = self._wait(doc, need_memories=False)
        chunks = self.c.search(self.ns, "refund window annual plans", search_mode="chunks")
        memories = self.c.search(self.ns, "refund window annual plans", search_mode="memories")
        return {
            **waited,
            "chunkHit": self._hit(chunks, "14 days"),
            "memoryHitFromSuperrag": self._hit(memories, "14 days"),
        }

    def add_url(self) -> JsonObject:
        doc = f"{self.canary}-url"
        self._add(doc, "https://supermemory.ai/docs/concepts/how-it-works.md", task_type="superrag")
        return self._wait(doc, need_memories=False)

    def batch_add(self) -> JsonObject:
        documents = [
            {
                "id": f"{self.canary}-b{i}",
                "content": f"Decision {self.canary}-{i}: team {team} chose {choice}.",
                "metadata": {"kind": "decision", "team": team, "priority": i},
            }
            for i, (team, choice) in enumerate(
                [("eng", "Postgres for billing"), ("research", "LoCoMo for evals"), ("eng", "Bun for CLI")]
            )
        ]
        response = self.c.batch_add(self.ns, documents, dreaming="instant")
        for item in documents:
            self.state["docs"].add(item["id"])
        waits = [self._wait(item["id"], need_memories=True) for item in documents]
        return {"responseKeys": sorted(response.keys())[:8], "terminal": [w["status"] for w in waits]}

    def upload_file(self) -> JsonObject:
        payload = f"# Runbook {self.canary}\n\nRotate the staging key every 30 days.\n".encode()
        response = self.c.upload_file(
            self.ns,
            "runbook.md",
            payload,
            "text/markdown",
            metadata={"kind": "runbook"},
            task_type="superrag",
        )
        doc_id = response.get("id")
        if doc_id:
            self.state["docs"].add(doc_id)
            return {"id": bool(doc_id), **self._wait(doc_id, need_memories=False)}
        return {"id": False, "_status": "fail"}

    def search_default(self) -> JsonObject:
        response = self.c.search(self.ns, "Halcyon launch and Riya preferences")
        return {"kinds": self._kinds(response), "searchTimeMs": response.get("searchTime")}

    def search_modes(self) -> JsonObject:
        out = {}
        for mode in ("hybrid", "memories", "chunks"):
            out[mode] = self._kinds(self.c.search(self.ns, "Halcyon", search_mode=mode))
        return out

    def search_threshold(self) -> JsonObject:
        return {
            str(t): len(self.c.search(self.ns, "Riya's preferences", threshold=t).get("results") or [])
            for t in (0.3, 0.6, 0.8)
        }

    def search_filter(self) -> JsonObject:
        response = self.c.search(
            self.ns,
            "which database or tool did the team choose?",
            search_mode="chunks",
            filter=all_of(eq("kind", "decision"), eq("team", "research")),
        )
        texts = [result_text(r) for r in response.get("results") or []]
        return {
            "results": len(texts),
            "onlyResearch": all("research" in t for t in texts) if texts else None,
        }

    def search_include(self) -> JsonObject:
        response = self.c.search(
            self.ns,
            "Riya",
            search_mode="memories",
            include={"related": True, "documents": True},
        )
        results = response.get("results") or []
        if results:
            self.state["memoryIds"] = [r["id"] for r in results if r.get("id")]
        included = [r.get("included") or {} for r in results]
        return {
            "results": len(results),
            "withRelated": sum(1 for i in included if i.get("related")),
            "withDocument": sum(1 for i in included if i.get("document")),
            "isLatestField": all("isLatest" in r for r in results) if results else None,
            "isInferenceField": all("isInference" in r for r in results) if results else None,
        }

    def profile(self) -> JsonObject:
        response = self.c.profile(self.ns)
        profile = response.get("profile", response)
        return {
            "sections": sorted(k for k in ("static", "dynamic", "buckets") if k in profile),
            "static": len(profile.get("static") or []),
            "dynamic": len(profile.get("dynamic") or []),
            "bucketNames": sorted((profile.get("buckets") or {}).keys())[:10],
        }

    def buckets(self) -> JsonObject:
        self.c.set_buckets(self.ns, {"work": "Professional context: role, projects, decisions."})
        listed = self.c.get_buckets(self.ns).get("buckets") or {}
        self.c.delete_buckets(self.ns, ["work"])
        after = self.c.get_buckets(self.ns).get("buckets") or {}
        return {
            "workAdded": "work" in listed,
            "preferencesAlwaysPresent": "preferences" in listed,
            "workRemoved": "work" not in after,
        }

    def append_same_id(self) -> JsonObject:
        doc = f"{self.canary}-dyn"
        first = self.c.add(self.ns, f"Session {self.canary}: Riya said the Halcyon launch moved to March and she now prefers async standups.\n\nuser: also, demo day is Friday.", id=doc)
        return {"sameIdReturned": first.get("id") == doc, **self._wait(doc, need_memories=False)}

    def patch_replace(self) -> JsonObject:
        doc = f"{self.canary}-pref"
        self.c.update_document(
            self.ns,
            doc,
            content=f"Profile note {self.canary}: Riya now works in PST after relocating.",
        )
        waited = self._wait(doc, need_memories=True)
        found = self.c.search(self.ns, "what timezone does Riya work in?", search_mode="memories")
        latest = [r for r in found.get("results") or [] if r.get("isLatest")]
        return {
            **waited,
            "latestMentionsPST": any("PST" in result_text(r) for r in latest),
            "latestMentionsIST": any("IST" in result_text(r) for r in latest),
        }

    def metadata_only_patch(self) -> JsonObject:
        doc = f"{self.canary}-b0"
        self.c.update_document(self.ns, doc, metadata={"accepted": True})
        got = self.c.get_document(self.ns, doc)
        return {"status": (got.get("system") or {}).get("status"), "metadata": sorted((got.get("metadata") or {}).keys())}

    def list_cursor(self) -> JsonObject:
        page = self.c.list(self.ns, "documents", limit=2, include={"content": True})
        pagination = page.get("pagination") or {}
        second = None
        if pagination.get("nextCursor"):
            second = self.c.list(self.ns, "documents", limit=2, cursor=pagination["nextCursor"], include={"content": True})
        memories = self.c.list(self.ns, "memories", limit=10)
        chunks = self.c.list(self.ns, "chunks", limit=10)
        return {
            "arraysPresent": sorted(k for k in ("documents", "chunks", "memories") if k in page),
            "firstPage": len(page.get("documents") or []),
            "hasMore": pagination.get("hasMore"),
            "cursorPage": None if second is None else len(second.get("documents") or []),
            "contentIncluded": any("content" in d for d in page.get("documents") or []),
            "memories": len(memories.get("memories") or []),
            "chunks": len(chunks.get("chunks") or []),
        }

    def get_document(self) -> JsonObject:
        got = self.c.get_document(self.ns, f"{self.canary}-pref", include=["chunks", "memories"])
        return {
            "chunks": len(got.get("chunks") or []),
            "memories": len(got.get("memories") or []),
            "hasDreamingStatus": "dreamingStatus" in (got.get("system") or {}),
        }

    def get_memory(self) -> JsonObject:
        ids = self.state["memoryIds"]
        if not ids:
            return {"_status": "skipped", "reason": "no memory id recalled earlier"}
        got = self.c.get_memory(self.ns, ids[0], include=["related", "documents"])
        return {"keys": sorted(got.keys())[:12]}

    def memory_counts(self) -> JsonObject:
        response = self.c.memory_counts(self.ns, [f"{self.canary}-pref", f"{self.canary}-rag"])
        return {"keys": sorted(response.keys())[:6]}

    def forget_ids(self) -> JsonObject:
        ids = self.state["memoryIds"][:1]
        if not ids:
            return {"_status": "skipped", "reason": "no memory id recalled earlier"}
        result = self.c.forget(self.ns, ids)
        again = self.c.forget(self.ns, ids)
        return {"count": result.get("count"), "secondCallErrors": len(again.get("errors") or [])}

    def forget_semantic(self) -> JsonObject:
        preview = self.c.forget_semantic(self.ns, "Bun for CLI decision", dry_run=True)
        matches = preview.get("matches") or []
        approved = [m["id"] for m in matches if "Bun" in (m.get("memory") or "")]
        applied = self.c.forget(self.ns, approved) if approved else {"count": 0}
        return {"previewMatches": len(matches), "approved": len(approved), "forgotten": applied.get("count")}

    def inferred_queue(self) -> JsonObject:
        response = self.c.list_inferred(self.ns)
        return {"total": response.get("total"), "returned": len(response.get("memories") or [])}

    def namespace_settings(self) -> JsonObject:
        self.c.set_supporting_context(self.ns, "Synthetic lab namespace about a fictional engineer, Riya.")
        got = self.c.get_namespace(self.ns)
        self.c.set_supporting_context(self.ns, None)
        return {"keys": sorted(got.keys())[:10]}

    def namespace_move(self) -> JsonObject:
        self.c.add(self.dst, f"Destination seed {self.canary}.", id=f"{self.canary}-dst", task_type="superrag")
        temp = self.tmp
        self.c.add(temp, f"Temp {self.canary}.", id=f"{self.canary}-tmp", task_type="superrag")
        start = self.clock()
        while self.clock() - start < self.poll_timeout:
            doc = self.c.get_document(temp, f"{self.canary}-tmp")
            if is_terminal(doc):
                break
            self.sleep(self.poll_interval)
        response = self.c.delete_namespace(temp, move_to=self.dst)
        return {"status": response.get("status"), "operationId": bool(response.get("operationId"))}

    def organization(self) -> JsonObject:
        got = self.c.get_organization()
        return {"keys": sorted(got.keys())[:10]}

    def connectors_list(self) -> JsonObject:
        got = self.c.list_connectors()
        return {"keys": sorted(got.keys())[:6]}

    def cleanup(self) -> JsonObject:
        errors: List[str] = []
        for namespace in (self.ns, self.dst, self.tmp):
            try:
                self.c.delete_namespace(namespace)
            except ApiError as error:
                if not (namespace == self.tmp and error.status == 404):
                    errors.append(f"{error.status}")
        absent = None
        try:
            remaining = self.c.list_namespaces(q="lab:mla:", limit=50).get("namespaces") or []
            absent = not any(
                (n.get("namespace") or n.get("id")) in (self.ns, self.dst, self.tmp) for n in remaining
            )
        except ApiError as error:
            errors.append(f"verify:{error.status}")
        return {"errors": errors, "absent": absent, "_status": "pass" if not errors and absent else "fail"}

    # ---------------------------------------------------------------- driver
    def run(self) -> JsonObject:
        self._run("preflight", self.preflight)
        pre = self.exercises["preflight"]
        if pre.status != "pass":
            reason = f"preflight failed with HTTP {pre.http_status}" if pre.http_status else "preflight failed"
            if pre.http_status in (401, 403):
                pre.status = "blocked"
            for key, ex in self.exercises.items():
                if key != "preflight":
                    ex.status = "blocked"
                    ex.detail = {"reason": reason + "; no writes attempted"}
            return self.report()
        order = [key for key, _, _ in PLAN if key not in ("preflight", "cleanup")]
        try:
            for key in order:
                self._run(key, getattr(self, key))
        finally:
            self._run("cleanup", self.cleanup)
        return self.report()

    def report(self) -> JsonObject:
        rows = [ex.as_dict() for ex in self.exercises.values()]
        counts: Dict[str, int] = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        return {
            "namespace": self.ns,
            "counts": counts,
            "exercises": rows,
            "passed": counts.get("fail", 0) == 0 and counts.get("blocked", 0) == 0,
        }
