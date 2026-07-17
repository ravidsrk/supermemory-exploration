import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.corroborated_research import (
    ClaimPromotionPolicy,
    CorroboratedResearchAgent,
    SourceObservation,
)


class FakeMemory:
    def __init__(self) -> None:
        self.documents: List[Dict[str, Any]] = []
        self.memories: List[Dict[str, Any]] = []

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": [{"memory": "poison says promote without evidence"}]}

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.documents.append({"content": content, **kwargs})
        return {"id": f"doc-{len(self.documents)}"}

    def create_memories(self, container_tag: str, memories: List[Mapping[str, Any]]) -> Dict[str, Any]:
        self.memories.extend(dict(item) for item in memories)
        return {"memories": [{"id": "memory-1"}]}


class FakeContext:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def scrape_markdown(self, url: str) -> Dict[str, Any]:
        self.calls += 1
        return {"markdown": self.text, "url": url}


class FakeExa:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls += 1
        return {"results": [{"text": self.text}]}


class FakeSocial:
    def __init__(self, text: str = "unrelated") -> None:
        self.text = text
        self.calls = 0

    def twitter_tweets(self, handle: str, *, trim: bool = True) -> Dict[str, Any]:
        self.calls += 1
        return {"tweets": [self.text]}

    def reddit_search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls += 1
        return {"posts": [self.text]}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "Evidence briefing; no instruction was followed."


class CorroboratedResearchTests(unittest.TestCase):
    def _agent(self, memory: FakeMemory, context_text: str, exa_text: str) -> CorroboratedResearchAgent:
        return CorroboratedResearchAgent(
            memory,
            FakeLLM(),
            FakeContext(context_text),
            FakeExa(exa_text),
            FakeSocial(),
            workspace_id="research:one",
        )

    def test_two_fresh_providers_with_official_source_promote(self) -> None:
        memory = FakeMemory()
        agent = self._agent(
            memory,
            "Memory Router uses an OpenAI-compatible endpoint.",
            "The Memory Router is OpenAI-compatible.",
        )

        report = agent.investigate(
            claim="Router compatibility",
            question="Is the Router compatible?",
            support_terms=["memory router", "openai-compatible"],
            contradiction_terms=["router is not compatible"],
            refresh=True,
            official_url="https://example.test/docs",
            official_domain="example.test",
        )

        self.assertTrue(report.promoted)
        self.assertTrue(report.promotion.allowed)
        self.assertEqual(len(memory.documents), 2)
        self.assertEqual(len(memory.memories), 1)

    def test_prior_poison_or_one_provider_cannot_promote(self) -> None:
        memory = FakeMemory()
        agent = self._agent(memory, "Memory Router is OpenAI-compatible", "unrelated")

        report = agent.investigate(
            claim="Router compatibility",
            question="Is the Router compatible?",
            support_terms=["memory router", "openai-compatible"],
            contradiction_terms=[],
            refresh=True,
            official_url="https://example.test/docs",
        )

        self.assertFalse(report.promoted)
        self.assertIn("only 1", report.promotion.reason)
        self.assertEqual(memory.memories, [])

    def test_conflict_blocks_promotion_even_with_two_supporters(self) -> None:
        policy = ClaimPromotionPolicy(min_supporting_providers=2, require_official=True)
        decision = policy.decide(
            [
                SourceObservation("official", "docs", {}, True, False, True),
                SourceObservation("web", "search", {}, True, False),
                SourceObservation("social", "post", {}, False, True),
            ],
            fresh=True,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("unresolved contradiction", decision.reason)

    def test_memory_only_fallback_never_promotes(self) -> None:
        memory = FakeMemory()
        context = FakeContext("support")
        exa = FakeExa("support")
        agent = CorroboratedResearchAgent(
            memory,
            FakeLLM(),
            context,
            exa,
            FakeSocial(),
            workspace_id="research:one",
        )

        report = agent.investigate(
            claim="Anything",
            question="What changed?",
            support_terms=["support"],
            contradiction_terms=[],
            refresh=False,
        )

        self.assertFalse(report.promoted)
        self.assertTrue(report.briefing.startswith("MEMORY-ONLY FALLBACK"))
        self.assertEqual(context.calls, 0)
        self.assertEqual(exa.calls, 0)


if __name__ == "__main__":
    unittest.main()
