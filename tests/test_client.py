import unittest

from supermemory_lab.client import SupermemoryClient

from .fakes import RecordingTransport


class SupermemoryClientTests(unittest.TestCase):
    def test_add_document_uses_singular_container_and_omits_none(self) -> None:
        transport = RecordingTransport()
        client = SupermemoryClient(transport)

        client.add_document(
            "Alex prefers concise answers",
            container_tag="user_alex",
            custom_id="conversation_1",
            metadata={"kind": "conversation"},
        )

        self.assertEqual(transport.calls[0][0:2], ("POST", "/v3/documents"))
        self.assertEqual(
            transport.calls[0][2],
            {
                "content": "Alex prefers concise answers",
                "containerTag": "user_alex",
                "customId": "conversation_1",
                "metadata": {"kind": "conversation"},
            },
        )

    def test_memory_search_always_sets_mode_and_tuning(self) -> None:
        transport = RecordingTransport()
        client = SupermemoryClient(transport)

        client.search_memories(
            "deployment preferences",
            container_tag="user_alex",
            search_mode="hybrid",
            threshold=0.63,
            rerank=True,
            include={"documents": True, "relatedMemories": True},
        )

        body = transport.calls[0][2]
        self.assertEqual(transport.calls[0][1], "/v4/search")
        self.assertEqual(body["searchMode"], "hybrid")
        self.assertEqual(body["containerTag"], "user_alex")
        self.assertEqual(body["threshold"], 0.63)
        self.assertTrue(body["rerank"])

    def test_wait_for_memory_polls_until_result_is_searchable(self) -> None:
        transport = RecordingTransport(
            responses=[{"results": []}, {"results": [{"id": "mem_1"}]}]
        )
        client = SupermemoryClient(transport)

        response = client.wait_for_memory(
            "GitHub tool",
            container_tag="tools:one",
            poll_seconds=0.001,
            timeout_seconds=1,
        )

        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(response["_pollAttempts"], 2)
        self.assertEqual(transport.calls[0][2]["searchMode"], "hybrid")

    def test_wait_for_profile_polls_until_dynamic_memory_is_visible(self) -> None:
        transport = RecordingTransport(
            responses=[
                {"profile": {"static": [], "dynamic": []}},
                {"profile": {"static": [], "dynamic": ["Use GitHub search"]}},
            ]
        )
        client = SupermemoryClient(transport)

        response = client.wait_for_profile(
            "tools:one", poll_seconds=0.001, timeout_seconds=1
        )

        self.assertEqual(response["_pollAttempts"], 2)
        self.assertEqual(len(transport.calls), 2)

    def test_profile_can_request_only_selected_buckets(self) -> None:
        transport = RecordingTransport()
        client = SupermemoryClient(transport)

        client.profile(
            "user_alex",
            include=["buckets"],
            buckets=["preferences", "goals"],
        )

        self.assertEqual(
            transport.calls[0][2],
            {
                "containerTag": "user_alex",
                "include": ["buckets"],
                "buckets": ["preferences", "goals"],
            },
        )

    def test_forget_matching_defaults_to_preview(self) -> None:
        transport = RecordingTransport()
        client = SupermemoryClient(transport)

        client.forget_matching("Project Titan", container_tag="user_alex")

        body = transport.calls[0][2]
        self.assertEqual(transport.calls[0][1], "/v4/memories/forget-matching")
        self.assertTrue(body["dryRun"])
        self.assertEqual(body["maxForget"], 100)

    def test_versioned_update_includes_observed_required_container(self) -> None:
        transport = RecordingTransport()
        client = SupermemoryClient(transport)

        client.update_memory(
            memory_id="mem_1",
            container_tag="project_alpha",
            new_content="Use PostgreSQL 18",
        )

        self.assertEqual(
            transport.calls[0][2],
            {
                "id": "mem_1",
                "containerTag": "project_alpha",
                "newContent": "Use PostgreSQL 18",
            },
        )

    def test_web_crawler_connection_uses_bounded_scope(self) -> None:
        transport = RecordingTransport()
        client = SupermemoryClient(transport)

        client.create_connection(
            "web-crawler",
            container_tags=["lab:crawler:1"],
            metadata={"startUrl": "https://example.com"},
            document_limit=1,
        )

        self.assertEqual(transport.calls[0][1], "/v3/connections/web-crawler")
        self.assertEqual(
            transport.calls[0][2],
            {
                "containerTags": ["lab:crawler:1"],
                "metadata": {"startUrl": "https://example.com"},
                "documentLimit": 1,
            },
        )

    def test_scoped_key_lifecycle_uses_container_and_key_id(self) -> None:
        transport = RecordingTransport()
        client = SupermemoryClient(transport)

        client.create_scoped_key(
            "tenant_1",
            name="sandbox",
            expires_in_days=7,
            rate_limit_max=50,
        )
        client.revoke_scoped_key("key/id")

        create = transport.calls[0]
        self.assertEqual(create[0:2], ("POST", "/v3/auth/scoped-key"))
        self.assertEqual(create[2]["containerTag"], "tenant_1")
        self.assertEqual(create[2]["expiresInDays"], 7)
        self.assertNotIn("rateLimitTimeWindow", create[2])
        self.assertEqual(
            transport.calls[1][0:2],
            ("DELETE", "/v3/auth/scoped-key/key%2Fid"),
        )

    def test_structured_conversation_preserves_roles(self) -> None:
        transport = RecordingTransport()
        client = SupermemoryClient(transport)
        messages = [
            {"role": "user", "content": "Remember that I use Python."},
            {"role": "assistant", "content": "Noted."},
        ]

        client.add_conversation(
            "conv_1", messages, container_tags=["user_alex"]
        )

        self.assertEqual(transport.calls[0][1], "/v4/conversations")
        self.assertEqual(transport.calls[0][2]["messages"], messages)


if __name__ == "__main__":
    unittest.main()
