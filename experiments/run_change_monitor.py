"""Run a reversible Context.dev monitor baseline/control cycle."""

from datetime import datetime, timezone
import json
import secrets

from supermemory_lab.config import load_config
from supermemory_lab.live import build_live_clients
from supermemory_lab.monitoring_agent import WebsiteChangeMemoryAgent
from supermemory_lab.trace import RunTrace


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3)
    run_id = f"change-monitor-{stamp}-{suffix}"
    trace = RunTrace(run_id, experiment="context-dev-monitor-control")
    clients = build_live_clients(load_config())
    report = WebsiteChangeMemoryAgent(
        clients.memory,
        clients.context,
        workspace_id=f"lab:monitor:{run_id}",
        trace=trace,
    ).run_control_cycle(
        name=f"Supermemory field lab {suffix}",
        url="https://example.com/",
        timeout_seconds=120,
        poll_seconds=3,
    )
    trace.metric("baselineCompleted", report.baseline_completed)
    trace.metric("secondRunCompleted", report.second_run_completed)
    trace.metric("changeCount", report.change_count)
    path = trace.write()
    print(
        json.dumps(
            {
                "trace": str(path),
                "baselineCompleted": report.baseline_completed,
                "secondRunCompleted": report.second_run_completed,
                "changeCount": report.change_count,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
