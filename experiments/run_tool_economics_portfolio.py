"""Live Monid/Composio/Exa read-route economics and remembered selection policy."""

from datetime import datetime, timezone
import json
import secrets
from typing import Any, Dict

from supermemory_lab.config import load_config
from supermemory_lab.evaluation import contains_text
from supermemory_lab.live import build_live_clients
from supermemory_lab.tool_economics import ToolEconomicsPortfolioAgent
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def main() -> None:
    identity = _identity()
    workspace = f"lab:tool-portfolio:{identity}"
    clients = build_live_clients(load_config())
    trace = RunTrace(f"tool-portfolio-{identity}", experiment="tool-economics-portfolio")
    evaluation: Dict[str, Any] = {}
    cleanup: Dict[str, Any] = {}

    try:
        agent = ToolEconomicsPortfolioAgent(
            clients.memory,
            clients.llm,
            clients.monid,
            clients.composio,
            clients.exa,
            workspace_id=workspace,
            allowed_monid_provider="api.kadec0.xyz",
            allowed_monid_endpoint="/v1/hackernews",
            max_direct_cost=0.02,
        )
        report = trace.capture(
            "calibrate_read_tool_portfolio",
            "monid+composio+exa+supermemory+openrouter",
            lambda: agent.calibrate("supermemory"),
            summarize=lambda value: {
                "selectedRoute": value.selected_route,
                "eligibleRoutes": list(value.eligible_routes),
                "shadowRoutes": list(value.shadow_routes),
                "policyVisible": value.policy_visible,
                "metrics": [
                    {
                        "route": item.route,
                        "valid": item.valid,
                        "costDollars": item.cost_dollars,
                        "costKnown": item.cost_known,
                        "latencyMs": item.latency_ms,
                        "items": item.item_count,
                        "relevant": item.relevant_count,
                    }
                    for item in value.metrics
                ],
            },
        )
        restarted = ToolEconomicsPortfolioAgent(
            clients.memory,
            clients.llm,
            clients.monid,
            clients.composio,
            clients.exa,
            workspace_id=workspace,
            allowed_monid_provider="api.kadec0.xyz",
            allowed_monid_endpoint="/v1/hackernews",
            max_direct_cost=0.02,
        )
        outcome = trace.capture(
            "route_from_policy_in_new_process",
            "supermemory+exa+monid",
            lambda: restarted.route_with_remembered_policy("supermemory agents"),
            summarize=lambda value: {
                "selectedRoute": value.selected_route,
                "attemptedRoutes": list(value.attempted_routes),
                "fallbackUsed": value.fallback_used,
                "valid": value.valid,
                "items": value.item_count,
                "relevant": value.relevant_count,
                "policySource": value.policy_source,
            },
        )
        outcome_visible = trace.capture(
            "verify_route_outcome_memory",
            "supermemory",
            lambda: clients.memory.wait_for_memory(
                "Verified tool route outcome",
                container_tag=workspace,
                search_mode="memories",
                threshold=0.0,
                required_text="Verified tool route outcome",
                timeout_seconds=45,
                poll_seconds=1,
            ),
            summarize=lambda value: {
                "visible": contains_text(value, "Verified tool route outcome"),
                "attempts": value.get("_pollAttempts"),
            },
        )
        metric_by_route = {item.route: item for item in report.metrics}
        monid = metric_by_route["monid-hackernews"]
        composio = metric_by_route["composio-hackernews"]
        exa = metric_by_route["exa-hackernews"]
        conclusion = report.conclusion.casefold()
        evaluation = {
            "allThreeRoutesValid": all(item.valid for item in report.metrics),
            "monidCostDollars": monid.cost_dollars,
            "monidCostKnown": monid.cost_known,
            "composioCostUnknown": not composio.cost_known
            and composio.cost_dollars is None,
            "exaCostDollars": exa.cost_dollars,
            "selectedRoute": report.selected_route,
            "eligibleRoutes": list(report.eligible_routes),
            "shadowRoutes": list(report.shadow_routes),
            "policyVisible": report.policy_visible,
            "newProcessRouteValid": outcome.valid,
            "newProcessSelectedRoute": outcome.selected_route,
            "newProcessUsedRememberedPolicy": outcome.policy_source
            == "supermemory-policy+runtime-contract",
            "outcomeVisible": contains_text(outcome_visible, "Verified tool route outcome"),
            "conclusionDoesNotCallUnknownPriceFree": "composio is free" not in conclusion,
            "sourcesWritten": report.sources_written,
        }
        evaluation["passed"] = all(
            [
                evaluation["allThreeRoutesValid"],
                monid.cost_dollars is not None and monid.cost_dollars <= 0.02,
                evaluation["monidCostKnown"],
                evaluation["composioCostUnknown"],
                exa.cost_dollars is not None and exa.cost_dollars <= 0.02,
                report.selected_route in report.eligible_routes,
                "composio-hackernews" in report.shadow_routes,
                report.policy_visible,
                outcome.valid,
                evaluation["newProcessUsedRememberedPolicy"],
                evaluation["outcomeVisible"],
                evaluation["conclusionDoesNotCallUnknownPriceFree"],
                report.sources_written == 3,
            ]
        )
        trace.metric("evaluation", evaluation)
    finally:
        try:
            cleanup = clients.memory.delete_container(workspace)
        except Exception as error:
            cleanup = {"error": type(error).__name__, "detail": str(error)[:200]}
        trace.metric("cleanup", cleanup)

    path = trace.write()
    print(json.dumps({"trace": str(path), "evaluation": evaluation, "cleanup": cleanup}, indent=2))


if __name__ == "__main__":
    main()
