"""Run a fresh developer radar cycle and a memory-only continuity cycle."""

from datetime import datetime, timezone
import secrets

from supermemory_lab.config import load_config
from supermemory_lab.live import build_live_clients
from supermemory_lab.signal_radar import DeveloperSignalRadarAgent
from supermemory_lab.trace import RunTrace


from supermemory_lab.integrity import new_run_identity


_identity = new_run_identity


def main() -> None:
    identity = _identity()
    workspace = f"lab:signal-radar:{identity}"
    trace = RunTrace(f"signal-radar-{identity}", experiment="developer-signal-radar")
    clients = build_live_clients(load_config())
    agent = DeveloperSignalRadarAgent(
        clients.memory,
        clients.llm,
        clients.composio,
        clients.exa,
        clients.social,
        workspace_id=workspace,
        trace=trace,
    )
    topic = (
        "Practical long-term memory for AI agents: production adoption, benchmarks, "
        "failure modes, and developer sentiment"
    )
    fresh = agent.scan(
        topic,
        refresh=True,
        hackernews_query="AI agent memory",
        twitter_handle="supermemory",
        reddit_query="AI agent long term memory Supermemory",
    )
    ready = trace.capture(
        "wait_for_radar_memory",
        "supermemory",
        lambda: clients.memory.wait_for_memory(
            "developer signal radar conclusion practical long-term memory AI agents",
            container_tag=workspace,
            search_mode="hybrid",
            timeout_seconds=60,
            poll_seconds=2,
            threshold=0.0,
        ),
        summarize=lambda value: {
            "results": len(value.get("results") or []),
            "pollAttempts": value.get("_pollAttempts"),
        },
    )
    fallback = agent.scan(topic, refresh=False)
    trace.metric("freshProviders", fresh.providers_used)
    trace.metric("freshSignalCounts", fresh.fresh_signal_counts)
    trace.metric("sourcesWritten", fresh.sources_written)
    trace.metric("memoryPollAttempts", ready.get("_pollAttempts"))
    trace.metric("fallbackProviders", fallback.providers_used)
    trace.metric("fallbackContextChars", len(fallback.prior_context))
    path = trace.write()
    print(f"workspace={workspace}")
    print(f"trace={path}")
    print("FRESH BRIEFING\n" + fresh.briefing)
    print("\nMEMORY-ONLY FALLBACK\n" + fallback.briefing)


if __name__ == "__main__":
    main()
