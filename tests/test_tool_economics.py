import unittest
from typing import Any, Dict, List, Mapping, Sequence

from supermemory_lab.tool_economics import ToolEconomicsPortfolioAgent


class FakeMemory:
    def __init__(self) -> None:
        self.items: List[str] = []
        self.batches: List[Any] = []

    def add_documents_batch(
        self, documents: Sequence[Mapping[str, Any]], **kwargs: Any
    ) -> Dict[str, Any]:
        self.batches.append((documents, kwargs))
        return {"results": [{"id": str(index)} for index, _ in enumerate(documents)]}

    def create_memories(self, container_tag: str, memories: List[Mapping[str, Any]]) -> Dict[str, Any]:
        self.items.extend(str(item["content"]) for item in memories)
        return {"memories": [{"id": "memory"}]}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": [{"memory": item} for item in self.items]}

    def wait_for_memory(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        required = kwargs.get("required_text", query)
        return {"results": [{"memory": item} for item in self.items if required in item]}


class FakeLLM:
    def __init__(self) -> None:
        self.system_prompt = ""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        return "Exa selected; Composio cost is unknown and remains shadow-only."


class FakeMonid:
    def discover(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": [{"provider": "hn", "endpoint": "/search"}]}

    def inspect(self, provider: str, endpoint: str) -> Dict[str, Any]:
        return {"method": "GET", "price": {"amount": {"value": 0.011}}}

    def run(self, provider: str, endpoint: str, tool_input: Mapping[str, Any]) -> Dict[str, Any]:
        query = tool_input["queryParams"]["q"]
        return {"output": {"items": [{"title": f"{query} story"}]}}


class FakeComposio:
    def get_tool(self, slug: str) -> Dict[str, Any]:
        return {"slug": slug, "no_auth": True}

    def execute_tool(self, slug: str, **kwargs: Any) -> Dict[str, Any]:
        query = kwargs["arguments"]["query"]
        return {"data": {"hits": [{"title": f"{query} post"}]}, "successful": True}


class FakeExa:
    def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {
            "results": [{"title": f"{query} result"}],
            "costDollars": {"total": 0.007},
        }


class ToolEconomicsTests(unittest.TestCase):
    def _agent(self, memory: FakeMemory, llm: FakeLLM) -> ToolEconomicsPortfolioAgent:
        return ToolEconomicsPortfolioAgent(
            memory,
            llm,
            FakeMonid(),
            FakeComposio(),
            FakeExa(),
            workspace_id="portfolio:1",
            allowed_monid_provider="hn",
            allowed_monid_endpoint="/search",
            max_direct_cost=0.02,
        )

    def test_selects_cheapest_valid_known_cost_and_shadows_unknown_cost(self) -> None:
        memory, llm = FakeMemory(), FakeLLM()

        report = self._agent(memory, llm).calibrate("supermemory")

        self.assertEqual(report.selected_route, "exa-hackernews")
        self.assertEqual(report.eligible_routes, ("exa-hackernews", "monid-hackernews"))
        self.assertEqual(report.shadow_routes, ("composio-hackernews",))
        self.assertTrue(report.policy_visible)
        self.assertEqual(report.sources_written, 3)
        self.assertIn("Unknown price is UNKNOWN", llm.system_prompt)

    def test_new_process_routes_from_memory_and_revalidates_contract(self) -> None:
        memory = FakeMemory()
        self._agent(memory, FakeLLM()).calibrate("supermemory")

        outcome = self._agent(memory, FakeLLM()).route_with_remembered_policy("supermemory")

        self.assertEqual(outcome.selected_route, "exa-hackernews")
        self.assertTrue(outcome.valid)
        self.assertFalse(outcome.fallback_used)
        self.assertEqual(outcome.policy_source, "supermemory-policy+runtime-contract")


if __name__ == "__main__":
    unittest.main()
