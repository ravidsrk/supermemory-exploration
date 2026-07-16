import tempfile
import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.advanced_agents import (
    CompetitiveIntelligenceAgent,
    ReleaseMemoryAgent,
    SandboxedDebuggingAgent,
    ToolSelectionAgent,
)
from supermemory_lab.trace import RunTrace, redact


class FakeLLM:
    def __init__(self) -> None:
        self.calls: List[Any] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return "evidence-backed answer"


class FakeMemory:
    def __init__(self) -> None:
        self.calls: List[Any] = []
        self.search_response: Dict[str, Any] = {"results": []}
        self.profile_response: Dict[str, Any] = {
            "profile": {"static": [], "dynamic": [], "buckets": {}}
        }

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("search", query, kwargs))
        return self.search_response

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("profile", container_tag, kwargs))
        return self.profile_response

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("document", content, kwargs))
        return {"id": "doc_1"}

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.calls.append(("create", container_tag, memories))
        return {"memories": [{"id": "mem_1"}]}


class FakeContext:
    def brand(self, domain: str) -> Dict[str, Any]:
        return {"brand": {"title": "Acme", "domain": domain}}


class FakeExa:
    def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": [{"title": "Result", "url": "https://example.com"}]}


class FakeSocial:
    def twitter_tweets(self, handle: str, **kwargs: Any) -> Dict[str, Any]:
        return {"tweets": [{"text": f"post by {handle}"}]}

    def reddit_search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"posts": [{"title": query}]}


class FakeMonid:
    def discover(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": [{"provider": "one", "endpoint": "search"}]}

    def inspect(self, provider: str, endpoint: str) -> Dict[str, Any]:
        return {"provider": provider, "endpoint": endpoint, "inputSchema": {}}


class FakeComposio:
    def list_tools(self, **kwargs: Any) -> Dict[str, Any]:
        return {"items": [{"slug": "SEARCH"}]}


class FakeVercel:
    def list_projects(self, **kwargs: Any) -> Dict[str, Any]:
        return {"projects": [{"id": "p1", "name": "site"}]}

    def list_deployments(self, **kwargs: Any) -> Dict[str, Any]:
        return {"deployments": [{"name": "site", "state": "READY"}]}


class FakeSuperServe:
    def __init__(self) -> None:
        self.test_calls = 0
        self.deleted = False

    def create_sandbox(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        self.network = kwargs["network"]
        return {"id": "box_1", "access_token": "box_token", "status": "active"}

    def command_transport(self, sandbox_id: str, access_token: str) -> object:
        return object()

    def exec(self, transport: object, command: str, **kwargs: Any) -> Dict[str, Any]:
        if command.startswith("python3 -m unittest"):
            self.test_calls += 1
            return {"exit_code": 1 if self.test_calls == 1 else 0, "stderr": "test"}
        if command.startswith("python3 hidden_eval.py candidate_no_memory.py"):
            return {"exit_code": 1, "stderr": "hidden mismatch"}
        if command.startswith("python3 hidden_eval.py candidate_memory.py"):
            return {"exit_code": 0, "stdout": "hidden transfer test passed"}
        return {"exit_code": 0, "stdout": ""}

    def delete_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        self.deleted = True
        return {}


class AdvancedAgentTests(unittest.TestCase):
    def test_intelligence_agent_triangulates_and_keeps_sources_as_rag(self) -> None:
        memory = FakeMemory()
        agent = CompetitiveIntelligenceAgent(
            memory,
            FakeLLM(),
            FakeContext(),
            FakeExa(),
            FakeSocial(),
            workspace_id="intel:acme",
        )

        report = agent.research(
            domain="acme.test",
            question="What changed?",
            twitter_handle="acme",
            reddit_query="acme product",
        )

        documents = [call for call in memory.calls if call[0] == "document"]
        self.assertEqual(report.sources_written, 4)
        self.assertEqual(len(documents), 4)
        self.assertTrue(all(call[2]["task_type"] == "superrag" for call in documents))
        self.assertEqual(memory.calls[0][2]["search_mode"], "hybrid")

    def test_tool_selection_can_use_memory_only_without_catalog_calls(self) -> None:
        memory = FakeMemory()
        memory.profile_response = {
            "profile": {
                "static": [],
                "dynamic": ["Use SEARCH for this request"],
                "buckets": {},
            }
        }
        monid = FakeMonid()
        composio = FakeComposio()
        agent = ToolSelectionAgent(
            memory,
            FakeLLM(),
            monid,
            composio,
            workspace_id="tools:one",
        )

        report = agent.select("search the public web", refresh=False)

        self.assertEqual(report.providers_used, ["supermemory"])
        self.assertIn("Use SEARCH", report.recalled_context)
        self.assertEqual([call for call in memory.calls if call[0] == "create"], [])
        self.assertEqual(memory.calls[0][0], "profile")
        self.assertEqual(memory.calls[0][2]["include"], ["static", "dynamic", "buckets"])

    def test_release_agent_stores_bounded_rag_snapshot(self) -> None:
        memory = FakeMemory()
        agent = ReleaseMemoryAgent(
            memory,
            FakeLLM(),
            FakeVercel(),
            workspace_id="release:one",
        )

        report = agent.review("Is production healthy?")

        document = [call for call in memory.calls if call[0] == "document"][0]
        self.assertEqual(report.providers_used, ["supermemory", "vercel"])
        self.assertEqual(document[2]["task_type"], "superrag")
        self.assertIn('"state": "READY"', document[1])

    def test_trace_redacts_secrets_in_values_and_keys(self) -> None:
        secret = "ctxt_secret_123456789abcdef"
        cleaned = redact({"api_token": "anything", "text": f"leak {secret}"})
        self.assertEqual(cleaned["api_token"], "[REDACTED]")
        self.assertNotIn(secret, cleaned["text"])

        with tempfile.TemporaryDirectory() as directory:
            trace = RunTrace("test-run", experiment="unit")
            trace.capture("step", "fake", lambda: {"secret": secret})
            path = trace.write(directory)
            self.assertNotIn(secret, path.read_text(encoding="utf-8"))

    def test_debug_agent_blocks_egress_and_compares_transfer_candidates(self) -> None:
        memory = FakeMemory()
        memory.profile_response = {
            "profile": {
                "static": [],
                "dynamic": ["Apply Unicode NFKC and stable deduplication"],
                "buckets": {},
            }
        }
        sandbox = FakeSuperServe()
        agent = SandboxedDebuggingAgent(
            memory,
            FakeLLM(),
            sandbox,
            workspace_id="debug:one",
        )

        report = agent.run(sandbox_name="debug-one")

        self.assertTrue(report.first_fix_passed)
        self.assertFalse(report.no_memory_transfer_passed)
        self.assertTrue(report.memory_transfer_passed)
        self.assertEqual(sandbox.network["deny_out"], ["0.0.0.0/0"])
        self.assertTrue(sandbox.deleted)


if __name__ == "__main__":
    unittest.main()
