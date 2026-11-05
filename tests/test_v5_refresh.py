import unittest
from typing import Any, Dict, List, Mapping, Optional, Tuple

from supermemory_lab.http import ApiError
from supermemory_lab.v5_refresh import V5RefreshProbe


class FakeV5Transport:
    """In-memory stand-in for the hosted v5 + legacy v4 surface."""

    def __init__(self, *, unauthorized: bool = False) -> None:
        self.unauthorized = unauthorized
        self.calls: List[Tuple[str, str, Optional[Mapping[str, Any]]]] = []
        self.docs: Dict[str, str] = {}
        self.memories: List[str] = []
        self.namespace_deleted = False

    def request(self, method: str, path: str, body: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        self.calls.append((method, path, body))
        if self.unauthorized:
            raise ApiError(method, path, 401, "Unauthorized")
        if method == "POST" and path.endswith("/document"):
            self.docs[body["id"]] = body["content"]
            self.memories.append(body["content"])
            return {"id": body["id"], "status": "queued"}
        if method == "GET" and "/document/" in path:
            doc_id = path.rsplit("/", 1)[-1]
            if self.namespace_deleted or doc_id not in self.docs:
                raise ApiError(method, path, 404, "Not found")
            return {"id": doc_id, "system": {"status": "done", "dreamingStatus": "done"}}
        if method == "POST" and path.endswith("/search"):
            mode = (body or {}).get("searchMode", "hybrid")
            results: List[Dict[str, Any]] = [{"memory": text} for text in self.memories]
            if mode == "hybrid":
                results += [{"chunk": text} for text in self.docs.values()]
            return {"results": results, "total": len(results)}
        if method == "POST" and path.endswith("/profile"):
            return {"profile": {"static": [], "dynamic": []}}
        if method == "POST" and "/list/documents" in path:
            return {"documents": [{"id": k} for k in self.docs], "pagination": {"nextCursor": None, "hasMore": False}}
        if path == "/v4/search":
            return {"results": [{"memory": text} for text in self.memories]}
        if path == "/v4/memories":
            self.memories.extend(m["content"] for m in body["memories"])
            return {"documentId": "d1", "memories": []}
        if method == "DELETE" and path.endswith("/memories/semantic"):
            assert body["dryRun"] is True
            return {"matches": [{"id": "m1"}], "errors": []}
        if method == "DELETE" and path.endswith("/document"):
            for doc_id in body["ids"]:
                self.docs.pop(doc_id, None)
            return {"matches": body["ids"], "errors": []}
        if method == "DELETE":
            self.namespace_deleted = True
            return {"status": "deleted", "namespace": "x", "deletedDocumentsCount": 0, "deletedMemoriesCount": 0}
        raise AssertionError(f"unexpected call {method} {path}")


class V5RefreshProbeTest(unittest.TestCase):
    def make(self, transport: FakeV5Transport) -> V5RefreshProbe:
        return V5RefreshProbe(
            transport,
            namespace="lab:v5refresh:test",
            canary="V5REFRESH_TEST",
            sleep=lambda _: None,
            timeout_seconds=5,
        )

    def test_happy_path_passes_and_cleans_up(self) -> None:
        transport = FakeV5Transport()
        report = self.make(transport).run()
        self.assertTrue(report["passed"], report)
        names = [step["name"] for step in report["steps"]]
        self.assertEqual(names[-1], "cleanup.verify_document_absent")
        default = next(s for s in report["steps"] if s["name"] == "v5.search_default")
        self.assertGreater(default["resultKinds"]["chunk"], 0)
        listing = next(s for s in report["steps"] if s["name"] == "v5.list_documents")
        self.assertTrue(listing["hasCursorFields"])

    def test_never_calls_feedback_or_key_minting(self) -> None:
        transport = FakeV5Transport()
        self.make(transport).run()
        paths = [path for _, path, _ in transport.calls]
        self.assertFalse(any("feedback" in p or "scoped-key" in p or "/organization" in p for p in paths))

    def test_unauthorized_key_reports_failure_and_still_attempts_cleanup(self) -> None:
        transport = FakeV5Transport(unauthorized=True)
        report = self.make(transport).run()
        self.assertFalse(report["passed"])
        self.assertTrue(all(step["status"] == 401 for step in report["steps"]))
        self.assertIn("cleanup.delete_namespace", [s["name"] for s in report["steps"]])

    def test_rejects_non_synthetic_namespace(self) -> None:
        with self.assertRaises(ValueError):
            V5RefreshProbe(FakeV5Transport(), namespace="prod_user_1", canary="X")


if __name__ == "__main__":
    unittest.main()
