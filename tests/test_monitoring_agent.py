import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.monitoring_agent import WebsiteChangeMemoryAgent


class FakeMemory:
    def __init__(self) -> None:
        self.documents: List[Any] = []

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.documents.append((content, kwargs))
        return {"id": "doc_1"}


class FakeContext:
    def __init__(self) -> None:
        self.run_triggered = False
        self.deleted = False

    def monitor_limits(self) -> Dict[str, Any]:
        return {"monitors_used": 0, "monitors_limit": 50, "plan": "starter"}

    def create_page_monitor(self, **kwargs: Any) -> Dict[str, Any]:
        self.create_kwargs = kwargs
        return {"id": "mon_1", "status": "active"}

    def list_monitor_runs(self, monitor_id: str, **kwargs: Any) -> Dict[str, Any]:
        runs: List[Mapping[str, Any]] = [{"id": "run_1", "status": "completed"}]
        if self.run_triggered:
            runs.append({"id": "run_2", "status": "completed"})
        return {"data": runs}

    def run_monitor(self, monitor_id: str) -> Dict[str, Any]:
        self.run_triggered = True
        return {"monitor_id": monitor_id, "run_id": "run_2"}

    def list_monitor_changes(self, monitor_id: str, **kwargs: Any) -> Dict[str, Any]:
        return {"data": []}

    def delete_monitor(self, monitor_id: str) -> Dict[str, Any]:
        self.deleted = True
        return {"id": monitor_id}


class MonitoringAgentTests(unittest.TestCase):
    def test_baseline_control_persists_rag_evidence_and_deletes_monitor(self) -> None:
        memory = FakeMemory()
        context = FakeContext()
        report = WebsiteChangeMemoryAgent(
            memory, context, workspace_id="monitor:one"
        ).run_control_cycle(name="example", url="https://example.com")

        self.assertTrue(report.baseline_completed)
        self.assertTrue(report.second_run_completed)
        self.assertEqual(report.change_count, 0)
        self.assertTrue(context.deleted)
        self.assertEqual(memory.documents[0][1]["task_type"], "superrag")
        self.assertIn('"changeCount": 0', memory.documents[0][0])


if __name__ == "__main__":
    unittest.main()
