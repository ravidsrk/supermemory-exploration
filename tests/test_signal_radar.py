import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.signal_radar import DeveloperSignalRadarAgent


class FakeMemory:
    def __init__(self) -> None:
        self.calls: List[Any] = []
        self.search_response: Dict[str, Any] = {"results": []}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("search", query, kwargs))
        return self.search_response

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("document", content, kwargs))
        return {"id": "doc"}

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.calls.append(("memory", container_tag, memories))
        return {"memories": [{"id": "memory"}]}


class FakeLLM:
    def __init__(self) -> None:
        self.prompts: List[Any] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.prompts.append((system_prompt, user_prompt))
        return "Observed signal with evidence gaps."


class FakeComposio:
    def __init__(self) -> None:
        self.executions = 0

    def get_tool(self, slug: str) -> Dict[str, Any]:
        return {"slug": slug, "no_auth": True, "version": "latest"}

    def execute_tool(self, slug: str, **kwargs: Any) -> Dict[str, Any]:
        self.executions += 1
        return {"successful": True, "data": {"hits": [{"title": "HN"}]}}


class FakeExa:
    def __init__(self) -> None:
        self.calls = 0

    def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls += 1
        return {"results": [{"title": "Web"}], "costDollars": 0.001}


class FakeSocial:
    def __init__(self) -> None:
        self.reddit_calls = 0
        self.twitter_calls = 0

    def reddit_search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.reddit_calls += 1
        return {"posts": [{"title": "Reddit"}]}

    def twitter_tweets(self, handle: str, **kwargs: Any) -> Dict[str, Any]:
        self.twitter_calls += 1
        return {"tweets": [{"text": "Tweet"}]}


class SignalRadarTests(unittest.TestCase):
    def test_fresh_scan_triangulates_and_persists_each_source_as_rag(self) -> None:
        memory = FakeMemory()
        composio = FakeComposio()
        exa = FakeExa()
        social = FakeSocial()
        report = DeveloperSignalRadarAgent(
            memory,
            FakeLLM(),
            composio,
            exa,
            social,
            workspace_id="radar:agents",
        ).scan(
            "agent memory",
            refresh=True,
            twitter_handle="supermemory",
            reddit_query="agent memory",
        )

        documents = [call for call in memory.calls if call[0] == "document"]
        self.assertEqual(composio.executions, 1)
        self.assertEqual(exa.calls, 1)
        self.assertEqual(social.reddit_calls, 1)
        self.assertEqual(social.twitter_calls, 1)
        self.assertEqual(len(documents), 4)
        self.assertTrue(all(call[2]["task_type"] == "superrag" for call in documents))
        self.assertEqual(report.sources_written, 5)

    def test_memory_only_fallback_skips_external_providers_and_writes(self) -> None:
        memory = FakeMemory()
        memory.search_response = {"results": [{"memory": "Prior observed signal"}]}
        composio = FakeComposio()
        exa = FakeExa()
        social = FakeSocial()
        llm = FakeLLM()
        report = DeveloperSignalRadarAgent(
            memory,
            llm,
            composio,
            exa,
            social,
            workspace_id="radar:agents",
        ).scan("agent memory", refresh=False)

        self.assertEqual(composio.executions, 0)
        self.assertEqual(exa.calls, 0)
        self.assertEqual(report.providers_used, ["supermemory", "openrouter"])
        self.assertEqual(report.sources_written, 0)
        self.assertTrue(report.briefing.startswith("MEMORY-ONLY FALLBACK"))
        self.assertIn("Prior observed signal", report.prior_context)
        self.assertIn("no fresh evidence", llm.prompts[0][0].casefold())

    def test_fails_closed_when_composio_tool_requires_auth(self) -> None:
        class AuthComposio(FakeComposio):
            def get_tool(self, slug: str) -> Dict[str, Any]:
                return {"slug": slug, "no_auth": False}

        with self.assertRaises(PermissionError):
            DeveloperSignalRadarAgent(
                FakeMemory(),
                FakeLLM(),
                AuthComposio(),
                FakeExa(),
                FakeSocial(),
                workspace_id="radar:agents",
            ).scan("agent memory", refresh=True)


if __name__ == "__main__":
    unittest.main()
