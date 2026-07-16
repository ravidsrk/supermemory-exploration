import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.lifecycle_agents import (
    EphemeralIncidentAgent,
    WorkspaceConsolidationAgent,
)


class FakeMemory:
    def __init__(self) -> None:
        self.calls: List[tuple] = []

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.calls.append(("create", container_tag, memories))
        return {"memories": [{"id": "mem_1"}]}

    def update_memory(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("update", kwargs))
        return {"id": "mem_2", "version": 2, "forgetAfter": None}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("search", query, kwargs))
        return {"results": []}

    def merge_containers(self, tags: List[str], **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("merge", tags, kwargs))
        return {"mergeId": "merge_1", "status": "queued"}

    def get_container_merge_status(self, merge_id: str) -> Dict[str, Any]:
        self.calls.append(("status", merge_id))
        return {"id": merge_id, "status": "completed"}


class LifecycleAgentTests(unittest.TestCase):
    def test_incident_lease_sets_and_can_clear_server_expiry(self) -> None:
        memory = FakeMemory()
        agent = EphemeralIncidentAgent(memory, container_tag="incident:one")

        agent.create_lease(
            "Temporary escalation",
            forget_after="2026-07-17T00:00:00Z",
            reason="incident window ended",
            event_dates=["2026-07-16T12:00:00Z"],
        )
        updated = agent.cancel_expiry("mem_1", content="Retain as postmortem")

        record = memory.calls[0][2][0]
        self.assertEqual(record["forgetAfter"], "2026-07-17T00:00:00Z")
        self.assertEqual(record["forgetReason"], "incident window ended")
        self.assertEqual(
            record["temporalContext"]["eventDate"], ["2026-07-16T12:00:00Z"]
        )
        update = memory.calls[1][1]
        self.assertIsNone(update["forget_after"])
        self.assertIsNone(update["forget_reason"])
        self.assertEqual(updated["version"], 2)

    def test_forgotten_search_is_explicit_opt_in(self) -> None:
        memory = FakeMemory()
        agent = EphemeralIncidentAgent(memory, container_tag="incident:one")

        agent.search("lease")
        agent.search("lease", include_forgotten=True)

        self.assertIsNone(memory.calls[0][2]["include"])
        self.assertEqual(
            memory.calls[1][2]["include"], {"forgottenMemories": True}
        )

    def test_workspace_merge_requires_queued_id_and_preserves_target(self) -> None:
        memory = FakeMemory()
        agent = WorkspaceConsolidationAgent(memory)

        request = agent.request_merge("old", "canonical")
        status = agent.status(request)

        self.assertEqual(request.merge_id, "merge_1")
        self.assertEqual(request.target_tag, "canonical")
        self.assertEqual(memory.calls[0][1], ["old", "canonical"])
        self.assertEqual(
            memory.calls[0][2]["target_container_tag"], "canonical"
        )
        self.assertEqual(status["status"], "completed")


if __name__ == "__main__":
    unittest.main()
