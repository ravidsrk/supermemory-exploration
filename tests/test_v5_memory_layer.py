import unittest

from supermemory_lab.http import ApiError
from supermemory_lab.memory_layer import MemoryLayer, SharedMemoryRouter
from supermemory_lab.memory_layer_lab import PLAN, MemoryLayerLab
from supermemory_lab.v5 import SupermemoryV5, all_of, any_of, eq, is_terminal, result_text

from tests.fakes import RecordingMultipartTransport, RecordingTransport


class V5ClientPathTests(unittest.TestCase):
    def setUp(self):
        self.t = RecordingMultipartTransport()
        self.c = SupermemoryV5(self.t)

    def test_add_uses_namespace_path_without_v5_prefix(self):
        self.c.add("org:acme:user:1", "hello", id="s1", dreaming="instant", task_type="superrag")
        method, path, body = self.t.calls[-1]
        self.assertEqual((method, path), ("POST", "/ns/org%3Aacme%3Auser%3A1/document"))
        self.assertEqual(body, {"content": "hello", "id": "s1", "dreaming": "instant", "taskType": "superrag"})
        self.assertNotIn("/v5", path)

    def test_namespace_and_metadata_validation(self):
        for bad in ("user 1", "a/b", "x" * 101, ""):
            with self.assertRaises(ValueError):
                self.c.add(bad, "x")
        with self.assertRaises(ValueError):
            self.c.add("u", "x", metadata={"nested": {"a": 1}})
        with self.assertRaises(ValueError):
            self.c.add("u", "x", metadata={"bad key": 1})
        with self.assertRaises(ValueError):
            self.c.add("u", "x", dreaming="later")
        self.assertEqual(self.t.calls, [])

    def test_search_sends_only_explicit_options(self):
        self.c.search("u", "q")
        self.assertEqual(self.t.calls[-1][2], {"query": "q"})
        self.c.search(
            "u",
            "q",
            search_mode="memories",
            threshold=0.6,
            rerank="order",
            include={"related": True},
            filter=all_of(eq("team", "eng"), any_of(eq("p", 1), eq("p", 2))),
        )
        body = self.t.calls[-1][2]
        self.assertEqual(body["searchMode"], "memories")
        self.assertEqual(body["include"], {"related": True})
        with self.assertRaises(ValueError):
            self.c.search("u", "q", search_mode="documents")  # v4 name, renamed to chunks

    def test_filter_depth_limit(self):
        node = eq("a", 1)
        for _ in range(6):
            node = all_of(node)
        with self.assertRaises(ValueError):
            self.c.search("u", "q", filter=node)

    def test_list_puts_pagination_in_query_and_filter_in_body(self):
        self.c.list("u", "documents", limit=2, cursor="abc", filter=eq("k", "v"), include={"content": True})
        method, path, body = self.t.calls[-1]
        self.assertEqual(method, "POST")
        self.assertTrue(path.startswith("/ns/u/list/documents?"))
        self.assertIn("cursor=abc", path)
        self.assertEqual(body, {"filter": eq("k", "v"), "include": {"content": True}})

    def test_iterate_follows_cursor(self):
        t = RecordingTransport(
            [
                {"documents": [{"id": 1}], "pagination": {"hasMore": True, "nextCursor": "c2"}},
                {"documents": [{"id": 2}], "pagination": {"hasMore": False}},
            ]
        )
        items = list(SupermemoryV5(t).iterate("u", "documents", limit=1))
        self.assertEqual([i["id"] for i in items], [1, 2])
        self.assertIn("cursor=c2", t.calls[1][1])

    def test_move_to_is_query_parameter_never_body(self):
        self.c.delete_namespace("old", move_to="new")
        method, path, body = self.t.calls[-1]
        self.assertEqual((method, path, body), ("DELETE", "/ns/old?moveTo=new", None))

    def test_forget_limits_and_semantic_dry_run_flag(self):
        with self.assertRaises(ValueError):
            self.c.forget("u", [])
        with self.assertRaises(ValueError):
            self.c.forget("u", [str(i) for i in range(501)])
        self.c.forget_semantic("u", "Project Titan", dry_run=True)
        self.assertEqual(self.t.calls[-1], ("DELETE", "/ns/u/memories/semantic", {"query": "Project Titan", "dryRun": True}))

    def test_batch_and_delete_limits(self):
        with self.assertRaises(ValueError):
            self.c.batch_add("u", [{"content": "x"}] * 601)
        with self.assertRaises(ValueError):
            self.c.delete_documents("u", ["x"] * 101)

    def test_upload_sends_metadata_as_json_string(self):
        self.c.upload_file("u", "a.md", b"# hi", "text/markdown", metadata={"kind": "runbook"})
        method, path, fields, files = self.t.multipart_calls[-1]
        self.assertEqual(path, "/ns/u/document/file")
        self.assertEqual(fields["metadata"], '{"kind": "runbook"}')
        self.assertEqual(files["file"][0], "a.md")

    def test_bucket_validation(self):
        with self.assertRaises(ValueError):
            self.c.set_buckets("u", {"static": "reserved"})
        with self.assertRaises(ValueError):
            self.c.set_buckets("u", {"Work": "uppercase"})
        self.c.set_buckets("u", {"work": "role and projects"})
        self.assertEqual(self.t.calls[-1][:2], ("PUT", "/ns/u/profile/buckets"))

    def test_inferred_review_uses_legacy_container_tag_path(self):
        self.c.review_inferred("user_1", "mem_1", "decline")
        self.assertEqual(self.t.calls[-1], ("POST", "/v3/container-tags/user_1/inferred/mem_1/review", {"action": "decline"}))
        with self.assertRaises(ValueError):
            self.c.review_inferred("user_1", "mem_1", "reject")

    def test_helpers(self):
        self.assertEqual(result_text({"chunk": "c"}), "c")
        self.assertEqual(result_text({"memory": "m", "chunk": "c"}), "m")
        self.assertFalse(is_terminal({"system": {"status": "embedding"}}))
        self.assertTrue(is_terminal({"system": {"status": "done", "dreamingStatus": "dreaming"}}))
        self.assertFalse(is_terminal({"system": {"status": "done", "dreamingStatus": "dreaming"}}, need_memories=True))
        self.assertTrue(is_terminal({"system": {"status": "failed"}}, need_memories=True))


class FailingTransport:
    def __init__(self, status):
        self.status = status
        self.calls = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        raise ApiError(method, path, self.status, "Unauthorized")


class MemoryLayerTests(unittest.TestCase):
    def test_hooks_profile_search_and_stable_session_append(self):
        t = RecordingTransport(
            [
                {"profile": {"static": [{"id": "m1", "memory": "Prefers concise answers"}], "dynamic": ["Shipping v2"], "buckets": {}}},
                {"results": [{"memory": "Prefers concise answers"}, {"chunk": "Refunds take 14 days"}]},
                {"id": "sess-1"},
                {"id": "sess-1"},
            ]
        )
        layer = MemoryLayer(SupermemoryV5(t), "user_1", session_id="sess-1")
        layer.session_start()
        context = layer.before_turn("refund?")
        self.assertEqual(context.recalled, ["Refunds take 14 days"])  # profile duplicate dropped
        self.assertIn("untrusted evidence", context.render())
        layer.after_turn("hi", "hello")
        layer.after_turn("refund?", "14 days")
        first, second = t.calls[2][2], t.calls[3][2]
        self.assertEqual(first["id"], second["id"])
        self.assertTrue(second["content"].startswith(first["content"]))  # same prefix → diff billing

    def test_fail_open_when_memory_unavailable(self):
        errors = []
        layer = MemoryLayer(SupermemoryV5(FailingTransport(503)), "user_1", session_id="s", on_error=lambda s, e: errors.append(s))
        self.assertTrue(layer.session_start().degraded)
        self.assertTrue(layer.before_turn("x").degraded)
        self.assertIsNone(layer.after_turn("a", "b"))
        self.assertEqual(errors, ["session_start", "before_turn", "after_turn"])

    def test_forget_reviewed_applies_only_approved_ids(self):
        t = RecordingTransport(
            [
                {"count": 2, "matches": [{"id": "a", "memory": "Titan budget"}, {"id": "b", "memory": "Titan is a moon"}], "errors": []},
                {"count": 1, "matches": [{"id": "a"}], "errors": []},
            ]
        )
        layer = MemoryLayer(SupermemoryV5(t), "u", session_id="s")
        result = layer.forget_reviewed("Project Titan", lambda matches: [m["id"] for m in matches if "budget" in m["memory"]])
        self.assertEqual(t.calls[1], ("DELETE", "/ns/u/memories", {"ids": ["a"]}))
        self.assertEqual(result["count"], 1)

    def test_remember_now_and_correct(self):
        t = RecordingTransport()
        layer = MemoryLayer(SupermemoryV5(t), "u", session_id="s")
        layer.remember_now("fact-tz", "User works in IST")
        layer.correct("fact-tz", "User works in PST")
        self.assertEqual(t.calls[0][2]["dreaming"], "instant")
        self.assertEqual(t.calls[1][:2], ("PATCH", "/ns/u/document/fact-tz"))

    def test_shared_router_merges_two_namespaces(self):
        t = RecordingTransport(
            [
                {"results": [{"memory": "private note", "similarity": 0.5}]},
                {"results": [{"chunk": "team decision", "similarity": 0.9}]},
            ]
        )
        router = SharedMemoryRouter(SupermemoryV5(t), private_namespace="agent_a", shared_namespace="team_x", agent_name="a")
        merged = router.recall("decision")
        self.assertEqual([m["scope"] for m in merged], ["shared", "private"])
        self.assertEqual([c[1] for c in t.calls], ["/ns/agent_a/search", "/ns/team_x/search"])


class LabSuiteTests(unittest.TestCase):
    def test_rejected_key_blocks_everything_without_writes(self):
        t = FailingTransport(401)
        report = MemoryLayerLab(SupermemoryV5(t), run_id="r", canary="C", sleep=lambda s: None).run()
        self.assertEqual(len(t.calls), 1)
        self.assertEqual(t.calls[0][0], "GET")
        self.assertEqual(report["counts"], {"blocked": len(PLAN)})
        self.assertFalse(report["passed"])

    def test_plan_covers_unique_keys_with_docs(self):
        keys = [k for k, _, _ in PLAN]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(d.startswith("https://supermemory.ai/docs/") for _, _, d in PLAN))
        self.assertEqual(keys[0], "preflight")
        self.assertEqual(keys[-1], "cleanup")


if __name__ == "__main__":
    unittest.main()


class HappyFake:
    """Route-aware fake so every lab exercise runs end to end offline."""

    def __init__(self):
        self.calls = []

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        route = path.split("?")[0]
        if route == "/namespaces":
            return {"namespaces": [], "pagination": {}}
        if route.endswith("/search"):
            return {"results": [{"id": "mem_1", "memory": "Riya works in PST, research chose LoCoMo", "isLatest": True, "isInference": False, "included": {"related": {"parents": []}}}], "searchTime": 5}
        if route.endswith("/profile"):
            return {"profile": {"static": [], "dynamic": [], "buckets": {"preferences": []}}}
        if route.endswith("/profile/buckets"):
            return {"buckets": {"preferences": "x", **({"work": "y"} if method == "GET" and not any(c[0] == "DELETE" and c[1] == route for c in self.calls) else {})}}
        if "/list/" in route:
            return {"documents": [{"id": "d", "content": "x"}], "chunks": [], "memories": [], "pagination": {"hasMore": False}}
        if "/memories/semantic" in route:
            return {"count": 1, "matches": [{"id": "mem_2", "memory": "Bun for CLI"}], "errors": []}
        if route.endswith("/memories"):
            return {"count": len(body["ids"]), "matches": [], "errors": []}
        if "/document/" in route and method == "GET":
            return {"id": route.rsplit("/", 1)[-1], "system": {"status": "done", "dreamingStatus": "done"}, "metadata": {}}
        if method == "DELETE" and "moveTo=" in path:
            return {"status": "queued", "operationId": "op"}
        if route.endswith("/document") and method == "POST":
            return {"id": body.get("id", "gen")}
        return {"ok": True}

    def request_multipart(self, method, path, *, fields, files):
        self.calls.append((method, path, fields))
        return {"id": "file_doc"}


class LabHappyPathTests(unittest.TestCase):
    def test_every_exercise_runs_and_cleanup_hits_all_namespaces(self):
        fake = HappyFake()
        report = MemoryLayerLab(SupermemoryV5(fake), run_id="r", canary="C", sleep=lambda s: None).run()
        failed = [e for e in report["exercises"] if e["status"] == "fail"]
        self.assertEqual(failed, [])
        deletes = [c[1] for c in fake.calls if c[0] == "DELETE" and c[1].startswith("/ns/lab") and "/" not in c[1][4:].split("?")[0]]
        self.assertIn("/ns/lab%3Amla%3Ar", deletes)
        self.assertIn("/ns/lab%3Amla%3Ar%3Adst", deletes)
        self.assertFalse(any(c[1] == "/feedback" for c in fake.calls))
        self.assertFalse(any(c[0] == "PATCH" and c[1] == "/organization" for c in fake.calls))
