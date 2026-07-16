"""Run practical multi-provider agents and write ignored, secret-safe traces."""

import argparse
from datetime import datetime, timezone
import secrets
import time
from typing import Callable, Dict

from supermemory_lab.advanced_agents import (
    CompetitiveIntelligenceAgent,
    ReleaseMemoryAgent,
    SandboxedDebuggingAgent,
    ToolSelectionAgent,
)
from supermemory_lab.config import load_config
from supermemory_lab.live import build_live_clients
from supermemory_lab.trace import RunTrace


def _identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"


def run_intelligence() -> None:
    identity = _identity()
    trace = RunTrace(f"advanced-intel-{identity}", experiment="competitive-intelligence")
    clients = build_live_clients(load_config())
    workspace = f"lab:intel:supermemory:{identity}"
    agent = CompetitiveIntelligenceAgent(
        clients.memory,
        clients.llm,
        clients.context,
        clients.exa,
        clients.social,
        workspace_id=workspace,
        trace=trace,
    )
    question = (
        "What is Supermemory's current positioning for agent builders, which concrete "
        "capabilities are users discussing, and what adoption risks or evidence gaps remain?"
    )
    report = agent.research(
        domain="supermemory.ai",
        question=question,
        twitter_handle="supermemory",
        reddit_query="supermemory AI memory agents",
    )
    trace.metric("sourcesWritten", report.sources_written)
    trace.metric("providersUsed", report.providers_used)
    path = trace.write()
    print(f"workspace={workspace}")
    print(f"trace={path}")
    print(report.answer)


def run_tools() -> None:
    identity = _identity()
    trace = RunTrace(f"advanced-tools-{identity}", experiment="tool-selection-memory")
    clients = build_live_clients(load_config())
    workspace = f"lab:tools:{identity}"
    agent = ToolSelectionAgent(
        clients.memory,
        clients.llm,
        clients.monid,
        clients.composio,
        workspace_id=workspace,
        trace=trace,
    )
    request = (
        "Find a read-only tool that can inspect a public GitHub repository and summarize "
        "recent issues. Prefer visible schemas, predictable cost, and no OAuth if possible."
    )
    fresh = agent.select(request, refresh=True)
    started = time.perf_counter()
    searchable = trace.capture(
        "wait_for_tool_profile",
        "supermemory",
        lambda: clients.memory.wait_for_profile(
            workspace,
            query="public GitHub repository recent issues tool",
            timeout_seconds=30,
            poll_seconds=2,
        ),
        summarize=lambda value: {
            "dynamic": len((value.get("profile") or {}).get("dynamic", [])),
            "static": len((value.get("profile") or {}).get("static", [])),
            "pollAttempts": value.get("_pollAttempts"),
        },
    )
    trace.metric("profileReadyMs", round((time.perf_counter() - started) * 1000, 1))
    trace.metric("profilePollAttempts", searchable.get("_pollAttempts"))
    try:
        search_started = time.perf_counter()
        search_ready = clients.memory.wait_for_memory(
            "public GitHub repository recent issues tool",
            container_tag=workspace,
            search_mode="hybrid",
            timeout_seconds=10,
            poll_seconds=2,
        )
        trace.metric("hybridReadyWithin10s", True)
        trace.metric("hybridReadyMs", round((time.perf_counter() - search_started) * 1000, 1))
        trace.metric("hybridPollAttempts", search_ready.get("_pollAttempts"))
    except TimeoutError:
        trace.metric("hybridReadyWithin10s", False)
    recalled = agent.select(request, refresh=False)
    trace.metric("freshProviders", fresh.providers_used)
    trace.metric("memoryOnlyProviders", recalled.providers_used)
    trace.metric("memoryOnlyContextChars", len(recalled.recalled_context))
    path = trace.write()
    print(f"workspace={workspace}")
    print(f"trace={path}")
    print("FRESH SELECTION\n" + fresh.answer)
    print("\nMEMORY-ONLY FOLLOW-UP\n" + recalled.answer)


def run_release() -> None:
    identity = _identity()
    trace = RunTrace(f"advanced-release-{identity}", experiment="release-memory")
    clients = build_live_clients(load_config())
    workspace = f"lab:release:{identity}"
    agent = ReleaseMemoryAgent(
        clients.memory,
        clients.llm,
        clients.vercel,
        workspace_id=workspace,
        trace=trace,
    )
    report = agent.review(
        "Summarize current deployment health. Separate observed state from anything that "
        "would require build logs, and identify the most useful facts to remember next run."
    )
    trace.metric("providersUsed", report.providers_used)
    path = trace.write()
    print(f"workspace={workspace}")
    print(f"trace={path}")
    print(report.answer)


def run_debug() -> None:
    identity = _identity()
    trace = RunTrace(f"advanced-debug-{identity}", experiment="sandbox-debug-transfer")
    clients = build_live_clients(load_config())
    workspace = f"lab:debug:{identity}"
    agent = SandboxedDebuggingAgent(
        clients.memory,
        clients.llm,
        clients.superserve,
        workspace_id=workspace,
        trace=trace,
    )
    report = agent.run(sandbox_name=f"sm-debug-{identity[-13:]}")
    trace.metric("firstFixPassed", report.first_fix_passed)
    trace.metric("noMemoryTransferPassed", report.no_memory_transfer_passed)
    trace.metric("memoryTransferPassed", report.memory_transfer_passed)
    trace.metric("profileContextChars", report.profile_context_chars)
    path = trace.write()
    print(f"workspace={workspace}")
    print(f"trace={path}")
    print(
        {
            "first_fix_passed": report.first_fix_passed,
            "no_memory_transfer_passed": report.no_memory_transfer_passed,
            "memory_transfer_passed": report.memory_transfer_passed,
            "profile_context_chars": report.profile_context_chars,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "experiment", choices=("intelligence", "tools", "release", "debug", "all")
    )
    args = parser.parse_args()
    runners: Dict[str, Callable[[], None]] = {
        "intelligence": run_intelligence,
        "tools": run_tools,
        "release": run_release,
        "debug": run_debug,
    }
    if args.experiment == "all":
        for runner in runners.values():
            runner()
    else:
        runners[args.experiment]()


if __name__ == "__main__":
    main()
