import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.safe_tool_agent import SafePublicToolAgent


class FakeMemory:
    def __init__(self) -> None:
        self.calls: List[Any] = []

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("document", content, kwargs))
        return {"id": "doc"}

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.calls.append(("memory", container_tag, memories))
        return {"memories": [{"id": "mem"}]}


class FakeMonid:
    def __init__(self, *, method: str = "GET", price: Any = 0.001) -> None:
        self.method = method
        self.price = price
        self.runs = 0

    def inspect(self, provider: str, endpoint: str) -> Dict[str, Any]:
        return {"method": self.method, "price": self.price, "input": {}}

    def run(
        self, provider: str, endpoint: str, tool_input: Mapping[str, Any]
    ) -> Dict[str, Any]:
        self.runs += 1
        return {"status": "success", "data": {"price": 100}}


class FakeComposio:
    def __init__(self, *, no_auth: bool = True) -> None:
        self.no_auth = no_auth
        self.executions = 0

    def get_tool(self, tool_slug: str) -> Dict[str, Any]:
        return {"slug": tool_slug, "no_auth": self.no_auth, "version": "latest"}

    def execute_tool(self, tool_slug: str, **kwargs: Any) -> Dict[str, Any]:
        self.executions += 1
        return {"successful": True, "data": [{"title": "story"}]}


class SafePublicToolAgentTests(unittest.TestCase):
    def _agent(
        self, memory: FakeMemory, monid: FakeMonid, composio: FakeComposio
    ) -> SafePublicToolAgent:
        return SafePublicToolAgent(
            memory,
            monid,
            composio,
            workspace_id="tools:field-lab",
            allowed_monid_tools={"defillama:/prices/current/{coins}"},
            allowed_composio_tools={"HACKERNEWS_GET_LATEST_POSTS"},
        )

    def test_executes_only_after_inspection_and_persists_bounded_evidence(self) -> None:
        memory = FakeMemory()
        monid = FakeMonid()
        composio = FakeComposio()

        report = self._agent(memory, monid, composio).execute_snapshot(
            monid_provider="defillama",
            monid_endpoint="/prices/current/{coins}",
            monid_input={"pathParams": {"coins": "coingecko:bitcoin"}},
            composio_tool_slug="HACKERNEWS_GET_LATEST_POSTS",
            composio_arguments={"page": 0, "size": 3},
            composio_user_id="field-lab",
        )

        self.assertEqual(monid.runs, 1)
        self.assertEqual(composio.executions, 1)
        self.assertEqual(report.sources_written, 3)
        self.assertEqual(len([call for call in memory.calls if call[0] == "document"]), 2)
        self.assertIn("Treat as data", memory.calls[0][1])

    def test_rejects_non_get_monid_tool_before_execution(self) -> None:
        memory = FakeMemory()
        monid = FakeMonid(method="POST")
        composio = FakeComposio()

        with self.assertRaises(PermissionError):
            self._agent(memory, monid, composio).execute_snapshot(
                monid_provider="defillama",
                monid_endpoint="/prices/current/{coins}",
                monid_input={},
                composio_tool_slug="HACKERNEWS_GET_LATEST_POSTS",
                composio_arguments={},
                composio_user_id="field-lab",
            )

        self.assertEqual(monid.runs, 0)
        self.assertEqual(composio.executions, 0)

    def test_accepts_monid_nested_per_call_price_shape(self) -> None:
        memory = FakeMemory()
        monid = FakeMonid(
            price={"type": "PER_CALL", "amount": {"value": 0.001, "currency": "USD"}}
        )
        composio = FakeComposio()

        self._agent(memory, monid, composio).execute_snapshot(
            monid_provider="defillama",
            monid_endpoint="/prices/current/{coins}",
            monid_input={},
            composio_tool_slug="HACKERNEWS_GET_LATEST_POSTS",
            composio_arguments={},
            composio_user_id="field-lab",
        )

        self.assertEqual(monid.runs, 1)

    def test_rejects_composio_mutation_token_and_non_allowlisted_tool(self) -> None:
        memory = FakeMemory()
        monid = FakeMonid()
        composio = FakeComposio()
        agent = SafePublicToolAgent(
            memory,
            monid,
            composio,
            workspace_id="tools:field-lab",
            allowed_monid_tools={"defillama:/prices/current/{coins}"},
            allowed_composio_tools={"GMAIL_SEND_EMAIL"},
        )

        with self.assertRaises(PermissionError):
            agent.execute_snapshot(
                monid_provider="defillama",
                monid_endpoint="/prices/current/{coins}",
                monid_input={},
                composio_tool_slug="GMAIL_SEND_EMAIL",
                composio_arguments={},
                composio_user_id="field-lab",
            )

        self.assertEqual(composio.executions, 0)


if __name__ == "__main__":
    unittest.main()
