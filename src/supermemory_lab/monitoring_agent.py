"""Reversible website monitoring that persists observations as Supermemory evidence."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, List, Mapping, Optional

from .agents import MemoryBackend
from .providers.context_dev import ContextDevClient
from .trace import RunTrace


@dataclass(frozen=True)
class MonitorExperimentReport:
    baseline_completed: bool
    second_run_completed: bool
    change_count: int
    sources_written: int


def _data(response: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    for key in ("data", "items", "runs", "changes"):
        value = response.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


class WebsiteChangeMemoryAgent:
    """Runs a Context.dev baseline/control cycle and stores the observed state as RAG."""

    def __init__(
        self,
        memory: MemoryBackend,
        context: ContextDevClient,
        *,
        workspace_id: str,
        trace: Optional[RunTrace] = None,
    ) -> None:
        self._memory = memory
        self._context = context
        self._workspace_id = workspace_id
        self._trace = trace

    def run_control_cycle(
        self,
        *,
        name: str,
        url: str,
        timeout_seconds: float = 120,
        poll_seconds: float = 3,
    ) -> MonitorExperimentReport:
        monitor_id: Optional[str] = None
        deleted = False
        sources_written = 0
        try:
            limits = self._capture(
                "read_monitor_limits",
                "context.dev",
                self._context.monitor_limits,
                lambda value: {
                    "used": value.get("monitors_used"),
                    "limit": value.get("monitors_limit"),
                    "plan": value.get("plan"),
                },
            )
            created = self._capture(
                "create_page_monitor",
                "context.dev",
                lambda: self._context.create_page_monitor(
                    name=name,
                    url=url,
                    frequency=1,
                    unit="days",
                    tags=["supermemory-field-lab"],
                ),
                lambda value: {
                    "id": value.get("id"),
                    "status": value.get("status"),
                },
            )
            value = created.get("id")
            if not isinstance(value, str):
                raise RuntimeError("Context.dev monitor response did not include an id")
            monitor_id = value
            baseline_runs = self._wait_for_completed_runs(
                monitor_id,
                minimum=1,
                timeout_seconds=timeout_seconds,
                poll_seconds=poll_seconds,
                step_name="wait_for_baseline",
            )
            baseline_completed = len(baseline_runs) >= 1

            self._capture(
                "trigger_control_run",
                "context.dev",
                lambda: self._context.run_monitor(monitor_id),
                lambda response: {
                    "monitorId": response.get("monitor_id"),
                    "runId": response.get("run_id") or response.get("id"),
                },
            )
            completed_runs = self._wait_for_completed_runs(
                monitor_id,
                minimum=2,
                timeout_seconds=timeout_seconds,
                poll_seconds=poll_seconds,
                step_name="wait_for_control_run",
            )
            changes = self._capture(
                "list_detected_changes",
                "context.dev",
                lambda: self._context.list_monitor_changes(monitor_id, limit=25),
                lambda response: {"changes": len(_data(response))},
            )
            change_count = len(_data(changes))
            captured_at = datetime.now(timezone.utc).isoformat()
            observation: Dict[str, Any] = {
                "capturedAt": captured_at,
                "provider": "context.dev",
                "targetUrl": url,
                "monitorType": "page-exact",
                "accountPlan": limits.get("plan"),
                "baselineCompleted": baseline_completed,
                "completedRunCount": len(completed_runs),
                "changeCount": change_count,
                "controlInterpretation": (
                    "No page change detected across immediate repeated observations."
                    if change_count == 0
                    else "At least one page change record was returned."
                ),
            }
            self._capture(
                "persist_monitor_observation",
                "supermemory",
                lambda: self._memory.add_document(
                    json.dumps(observation, sort_keys=True),
                    container_tag=self._workspace_id,
                    custom_id=f"monitor-observation-{monitor_id}",
                    metadata={
                        "kind": "website-monitor-observation",
                        "provider": "context.dev",
                        "capturedAt": captured_at,
                    },
                    task_type="superrag",
                ),
                lambda response: {"accepted": bool(response)},
            )
            sources_written = 1
            return MonitorExperimentReport(
                baseline_completed=baseline_completed,
                second_run_completed=len(completed_runs) >= 2,
                change_count=change_count,
                sources_written=sources_written,
            )
        finally:
            if monitor_id:
                try:
                    self._capture(
                        "delete_page_monitor",
                        "context.dev",
                        lambda: self._context.delete_monitor(monitor_id),
                        lambda response: {"deleted": True},
                    )
                    deleted = True
                except Exception:
                    deleted = False
            if self._trace:
                self._trace.metric("monitorDeleted", deleted)
                self._trace.metric("sourcesWritten", sources_written)

    def _wait_for_completed_runs(
        self,
        monitor_id: str,
        *,
        minimum: int,
        timeout_seconds: float,
        poll_seconds: float,
        step_name: str,
    ) -> List[Mapping[str, Any]]:
        def wait() -> List[Mapping[str, Any]]:
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                response = self._context.list_monitor_runs(monitor_id, limit=25)
                completed = [
                    run for run in _data(response) if run.get("status") == "completed"
                ]
                if len(completed) >= minimum:
                    return completed
                time.sleep(poll_seconds)
            raise TimeoutError(
                f"monitor {monitor_id} did not reach {minimum} completed runs"
            )

        return self._capture(
            step_name,
            "context.dev",
            wait,
            lambda runs: {"completedRuns": len(runs)},
        )

    def _capture(self, name: str, provider: str, action: Any, summarize: Any) -> Any:
        if self._trace:
            return self._trace.capture(name, provider, action, summarize=summarize)
        return action()
