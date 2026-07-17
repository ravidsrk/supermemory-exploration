"""Execute two explicitly allowlisted public tools and retain observations in memory."""

from datetime import datetime, timezone
import secrets
from typing import Any, Mapping

from supermemory_lab.config import load_config
from supermemory_lab.live import build_live_clients
from supermemory_lab.safe_tool_agent import SafePublicToolAgent
from supermemory_lab.trace import RunTrace


from supermemory_lab.integrity import new_run_identity


_identity = new_run_identity


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _bitcoin_price(response: Mapping[str, Any]) -> Any:
    output = _mapping(response.get("output"))
    coins = _mapping(output.get("coins"))
    bitcoin = _mapping(coins.get("coingecko:bitcoin"))
    return bitcoin.get("price")


def _story_count(response: Mapping[str, Any]) -> int:
    data = response.get("data")
    if isinstance(data, list):
        return len(data)
    mapped = _mapping(data)
    for key in ("hits", "items", "posts", "data"):
        value = mapped.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def main() -> None:
    identity = _identity()
    workspace = f"lab:safe-tools:{identity}"
    trace = RunTrace(f"safe-tools-{identity}", experiment="safe-public-tool-execution")
    clients = build_live_clients(load_config())
    agent = SafePublicToolAgent(
        clients.memory,
        clients.monid,
        clients.composio,
        workspace_id=workspace,
        max_monid_price=0.005,
        allowed_monid_tools={"defillama:/prices/current/{coins}"},
        allowed_composio_tools={"HACKERNEWS_GET_LATEST_POSTS"},
        trace=trace,
    )

    report = agent.execute_snapshot(
        monid_provider="defillama",
        monid_endpoint="/prices/current/{coins}",
        monid_input={
            "body": {},
            "queryParams": {},
            "pathParams": {"coins": "coingecko:bitcoin"},
        },
        composio_tool_slug="HACKERNEWS_GET_LATEST_POSTS",
        composio_arguments={"page": 0, "size": 3, "tags": ["story"]},
        composio_user_id="supermemory-field-lab",
    )
    trace.metric("bitcoinPriceObserved", _bitcoin_price(report.monid_result))
    trace.metric("hackerNewsStoryCount", _story_count(report.composio_result))
    trace.metric("sourcesWritten", report.sources_written)
    trace.metric("providersUsed", report.providers_used)
    path = trace.write()
    print(f"workspace={workspace}")
    print(f"trace={path}")
    print(f"bitcoin_price_observed={_bitcoin_price(report.monid_result)}")
    print(f"hacker_news_story_count={_story_count(report.composio_result)}")


if __name__ == "__main__":
    main()
