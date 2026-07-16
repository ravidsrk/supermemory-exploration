"""Observe Vercel read-only and verify a memory-guided fix in a disposable sandbox."""

from datetime import datetime, timezone
import json
import secrets

from supermemory_lab.config import load_config
from supermemory_lab.live import build_live_clients
from supermemory_lab.release_triage import ReleaseTriageRehearsalAgent
from supermemory_lab.trace import RunTrace


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    identity = f"{stamp}-{secrets.token_hex(3)}"
    workspace = f"lab:release-triage:{identity}"
    trace = RunTrace(
        f"release-triage-{identity}", experiment="release-triage-sandbox-rehearsal"
    )
    clients = build_live_clients(load_config())
    report = ReleaseTriageRehearsalAgent(
        clients.memory,
        clients.llm,
        clients.vercel,
        clients.superserve,
        workspace_id=workspace,
        trace=trace,
    ).run(sandbox_name=f"release-triage-{identity}")
    trace.metric("observedProjectCount", report.observed_project_count)
    trace.metric("observedDeploymentCount", report.observed_deployment_count)
    trace.metric("observedStateCounts", report.observed_state_counts)
    trace.metric("rehearsalInitiallyFailed", report.rehearsal_initially_failed)
    trace.metric("rehearsalRepairAttempted", report.rehearsal_repair_attempted)
    trace.metric("rehearsalPatchPassed", report.rehearsal_patch_passed)
    trace.metric("recalledRunbookChars", report.recalled_runbook_chars)
    path = trace.write()
    print(
        json.dumps(
            {
                "trace": str(path),
                "workspace": workspace,
                "observedProjectCount": report.observed_project_count,
                "observedDeploymentCount": report.observed_deployment_count,
                "observedStateCounts": report.observed_state_counts,
                "rehearsalInitiallyFailed": report.rehearsal_initially_failed,
                "rehearsalRepairAttempted": report.rehearsal_repair_attempted,
                "rehearsalPatchPassed": report.rehearsal_patch_passed,
                "sandboxDeleted": report.sandbox_deleted,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
