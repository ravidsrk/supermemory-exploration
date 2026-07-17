import os
from pathlib import Path
import tempfile
import unittest
from typing import Any, Dict, List, Mapping, Optional, Tuple

from supermemory_lab.config import load_config
from supermemory_lab.providers import (
    ComposioClient,
    ContextDevClient,
    ExaClient,
    MonidClient,
    ScrapeCreatorsClient,
    SuperServeClient,
    VercelClient,
)


class RecordingTransport:
    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None) -> None:
        self.calls: List[Tuple[str, str, Optional[Mapping[str, Any]]]] = []
        self.responses = responses or [{}]

    def request(
        self,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.calls.append((method, path, body))
        return self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]


class ProviderAdapterTests(unittest.TestCase):
    def test_search_and_brand_request_shapes(self) -> None:
        transport = RecordingTransport()
        ExaClient(transport).search("memory agents", include_domains=["example.com"])
        ContextDevClient(transport).brand("supermemory.ai")

        self.assertEqual(transport.calls[0][1], "/search")
        self.assertEqual(transport.calls[0][2]["includeDomains"], ["example.com"])
        self.assertIn("domain=supermemory.ai", transport.calls[1][1])
        self.assertIn("maxSpeed=true", transport.calls[1][1])

    def test_context_markdown_scrape_uses_current_get_contract(self) -> None:
        transport = RecordingTransport()

        ContextDevClient(transport).scrape_markdown(
            "https://example.com/docs?section=memory"
        )

        method, path, body = transport.calls[0]
        self.assertEqual(method, "GET")
        self.assertTrue(path.startswith("/web/scrape/markdown?"))
        self.assertIn("url=https%3A%2F%2Fexample.com%2Fdocs%3Fsection%3Dmemory", path)
        self.assertIsNone(body)

    def test_context_monitor_lifecycle_uses_exact_page_schema(self) -> None:
        transport = RecordingTransport()
        client = ContextDevClient(transport)
        client.create_page_monitor(
            name="pricing", url="https://example.com/pricing", tags=["lab"]
        )
        client.run_monitor("mon/one")
        client.list_monitor_runs("mon/one", status="completed")
        client.delete_monitor("mon/one")

        body = transport.calls[0][2]
        self.assertEqual(body["target"]["type"], "page")
        self.assertEqual(body["change_detection"], {"type": "exact"})
        self.assertEqual(body["schedule"]["unit"], "days")
        self.assertEqual(transport.calls[1][1], "/monitors/mon%2Fone/run")
        self.assertIn("status=completed", transport.calls[2][1])
        self.assertEqual(transport.calls[3][0], "DELETE")

    def test_social_endpoints_encode_parameters(self) -> None:
        transport = RecordingTransport()
        client = ScrapeCreatorsClient(transport)
        client.twitter_tweets("supermemory", trim=True)
        client.reddit_search("AI memory", timeframe="week")

        self.assertIn("handle=supermemory", transport.calls[0][1])
        self.assertIn("trim=true", transport.calls[0][1])
        self.assertIn("query=AI+memory", transport.calls[1][1])
        self.assertIn("timeframe=week", transport.calls[1][1])

    def test_tool_catalogs_do_not_execute_during_discovery(self) -> None:
        monid_transport = RecordingTransport()
        composio_transport = RecordingTransport()

        MonidClient(monid_transport).discover("send a report")
        ComposioClient(composio_transport).list_tools(query="read repository")

        self.assertEqual(monid_transport.calls[0][1], "/v1/discover")
        self.assertTrue(composio_transport.calls[0][1].startswith("/api/v3/tools?"))
        self.assertNotIn("execute", composio_transport.calls[0][1])

    def test_composio_execution_uses_explicit_user_arguments_and_version(self) -> None:
        transport = RecordingTransport()
        client = ComposioClient(transport)

        client.get_tool("HACKERNEWS_GET_LATEST_POSTS")
        client.execute_tool(
            "HACKERNEWS_GET_LATEST_POSTS",
            user_id="field-lab",
            arguments={"page": 0, "size": 3},
        )

        self.assertIn("toolkit_versions=latest", transport.calls[0][1])
        self.assertEqual(
            transport.calls[1][1],
            "/api/v3/tools/execute/HACKERNEWS_GET_LATEST_POSTS",
        )
        self.assertEqual(transport.calls[1][2]["version"], "latest")
        self.assertEqual(transport.calls[1][2]["user_id"], "field-lab")

    def test_operational_adapters_are_read_only_by_default(self) -> None:
        transport = RecordingTransport()
        VercelClient(transport).list_deployments(project_id="prj_1")
        SuperServeClient(transport).list_sandboxes(limit=2)

        self.assertEqual(transport.calls[0][0], "GET")
        self.assertIn("projectId=prj_1", transport.calls[0][1])
        self.assertEqual(transport.calls[1][0], "GET")

    def test_config_loads_optional_provider_keys_without_rendering_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.local"
            path.write_text(
                "SUPERMEMORY_API_KEY=sm-test\n"
                "EXA_API_KEY=exa-test\n"
                "VERCEL_TOKEN=vercel-test\n",
                encoding="utf-8",
            )
            names = ("SUPERMEMORY_API_KEY", "EXA_API_KEY", "VERCEL_TOKEN")
            prior = {name: os.environ.pop(name, None) for name in names}
            try:
                config = load_config(str(path))
            finally:
                for name, original in prior.items():
                    if original is not None:
                        os.environ[name] = original

        self.assertEqual(config.exa_api_key, "exa-test")
        self.assertEqual(config.vercel_token, "vercel-test")


if __name__ == "__main__":
    unittest.main()
