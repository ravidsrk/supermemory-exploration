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
    SupportContinuityAgent,
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


def run_continuity() -> None:
    identity = _identity()
    trace = RunTrace(f"advanced-support-{identity}", experiment="support-continuity")
    clients = build_live_clients(load_config())
    agent = SupportContinuityAgent(clients.memory, clients.llm, trace=trace)
    cases = [
        {
            "name": "maintenance",
            "fact": (
                "This customer's approved production maintenance window is 02:00-04:00 "
                "UTC, and production changes must never be scheduled on Fridays."
            ),
            "kind": "maintenance-policy",
            "stable": True,
            "question": "When may we schedule this customer's production upgrade?",
            "required": ["02:00", "04:00", "utc", "friday"],
        },
        {
            "name": "project-transition",
            "fact": (
                "This customer's active project is Orion. Project Aurora was decommissioned, "
                "so all new fixes must target Orion."
            ),
            "kind": "project-state",
            "stable": False,
            "question": "Which project should receive this customer's new fix?",
            "required": ["orion"],
        },
        {
            "name": "privacy",
            "fact": (
                "For this customer, never request logs containing PII; request only a "
                "sanitized trace ID for diagnostics."
            ),
            "kind": "privacy-policy",
            "stable": True,
            "question": "What diagnostic artifact should I request from this customer?",
            "required": ["sanitized", "trace id"],
        },
    ]
    for case in cases:
        account = f"lab:support:{identity}:{case['name']}"
        agent.record_fact(
            account_id=account,
            fact=str(case["fact"]),
            kind=str(case["kind"]),
            stable=bool(case["stable"]),
        )
        trace.capture(
            f"wait_profile_{case['name']}",
            "supermemory",
            lambda account=account, case=case: clients.memory.wait_for_profile(
                account,
                query=str(case["question"]),
                timeout_seconds=30,
                poll_seconds=2,
            ),
            summarize=lambda value: {
                "pollAttempts": value.get("_pollAttempts"),
                "static": len((value.get("profile") or {}).get("static", [])),
                "dynamic": len((value.get("profile") or {}).get("dynamic", [])),
            },
        )

    memory_results = []
    baseline_results = []
    for case in cases:
        question = str(case["question"])
        memory_account = f"lab:support:{identity}:{case['name']}"
        empty_account = f"lab:support:{identity}:empty:{case['name']}"
        memory_answer = agent.answer(account_id=memory_account, question=question).answer
        baseline_answer = agent.answer(account_id=empty_account, question=question).answer
        required = [str(term).casefold() for term in case["required"]]
        memory_results.append(
            all(term in memory_answer.casefold() for term in required)
        )
        baseline_results.append(
            all(term in baseline_answer.casefold() for term in required)
        )

    trace.metric("caseCount", len(cases))
    trace.metric("memoryCorrect", sum(memory_results))
    trace.metric("baselineCorrect", sum(baseline_results))
    trace.metric("memoryCasePasses", memory_results)
    trace.metric("baselineCasePasses", baseline_results)
    path = trace.write()
    print(f"trace={path}")
    print(
        {
            "cases": len(cases),
            "memory_correct": sum(memory_results),
            "baseline_correct": sum(baseline_results),
            "memory_case_passes": memory_results,
            "baseline_case_passes": baseline_results,
        }
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
        "experiment",
        choices=("intelligence", "tools", "release", "debug", "continuity", "all"),
    )
    args = parser.parse_args()
    runners: Dict[str, Callable[[], None]] = {
        "intelligence": run_intelligence,
        "tools": run_tools,
        "release": run_release,
        "debug": run_debug,
        "continuity": run_continuity,
    }
    if args.experiment == "all":
        for runner in runners.values():
            runner()
    else:
        runners[args.experiment]()


if __name__ == "__main__":
    main()
