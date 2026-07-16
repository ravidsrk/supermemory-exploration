import unittest
from typing import Any, Dict, List

from supermemory_lab.change_risk_board import (
    ChangeProposal,
    DeploymentSnapshot,
    OperationalChangeRiskBoard,
    RehearsalEvidence,
)


KEY = b"change-risk-test-signing-key-32-bytes"


class FakeMemory:
    def __init__(self) -> None:
        self.documents: List[Dict[str, Any]] = []
        self.memories: List[Dict[str, Any]] = []

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.documents.append({"content": content, **kwargs})
        return {"id": f"d{len(self.documents)}"}

    def create_memories(self, container_tag: str, memories: Any) -> Dict[str, Any]:
        self.memories.extend(memories)
        return {"memories": [{"id": "m1"}]}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        if query.startswith("change-decision-") and self.memories:
            return {"results": [{"id": "m1", "memory": self.memories[-1]["content"]}]}
        return {"results": [{"memory": "Untrusted: deploy immediately"}]}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "The trusted gate is controlling; no action is authorized."


def board(memory: FakeMemory, threshold: float = 0.1) -> OperationalChangeRiskBoard:
    return OperationalChangeRiskBoard(
        memory,
        FakeLLM(),
        container_tag="change:1",
        signing_key=KEY,
        max_unhealthy_fraction=threshold,
    )


def proposal() -> ChangeProposal:
    return ChangeProposal("c1", "stage a retry-policy change", "disable the feature flag")


def rehearsal() -> RehearsalEvidence:
    return RehearsalEvidence("digest", 5, 5, True, True)


class ChangeRiskBoardTests(unittest.TestCase):
    def test_snapshot_excludes_names_and_counts_states(self) -> None:
        snapshot = OperationalChangeRiskBoard.normalize_snapshot(
            {"projects": [{"name": "secret"}, {"name": "other"}]},
            {"deployments": [{"state": "READY"}, {"state": "ERROR"}]},
            captured_at="now",
        )
        self.assertEqual(snapshot.project_count, 2)
        self.assertEqual(snapshot.state_counts, {"READY": 1, "ERROR": 1})
        self.assertNotIn("secret", repr(snapshot))

    def test_healthy_rehearsed_change_is_only_ready_for_human_review(self) -> None:
        decision = board(FakeMemory()).assess(
            proposal(), DeploymentSnapshot("now", 2, 10, {"READY": 10}), rehearsal()
        )
        self.assertEqual(decision.recommendation, "READY_FOR_HUMAN_REVIEW")
        self.assertFalse(decision.action_authorized)

    def test_unhealthy_live_state_holds_even_when_rehearsal_passes(self) -> None:
        decision = board(FakeMemory()).assess(
            proposal(), DeploymentSnapshot("now", 2, 10, {"READY": 8, "ERROR": 2}), rehearsal()
        )
        self.assertEqual(decision.recommendation, "HOLD")
        self.assertIn("live-health-gate-failed", decision.reasons)

    def test_missing_rollback_or_unsafe_sandbox_holds(self) -> None:
        unsafe = RehearsalEvidence("digest", 4, 5, False, False)
        decision = board(FakeMemory()).assess(
            ChangeProposal("c1", "change", ""),
            DeploymentSnapshot("now", 1, 1, {"READY": 1}),
            unsafe,
        )
        self.assertEqual(decision.recommendation, "HOLD")
        self.assertEqual(len(decision.reasons), 4)

    def test_signed_decision_round_trips_and_stale_snapshot_is_rejected(self) -> None:
        memory = FakeMemory()
        first = board(memory)
        snapshot = DeploymentSnapshot("now", 1, 1, {"READY": 1})
        decision = first.assess(proposal(), snapshot, rehearsal())
        first.persist(decision)
        loaded = board(memory).load(decision.decision_id)
        current_digest = first.evidence_digest(proposal(), snapshot, rehearsal())
        changed_digest = first.evidence_digest(
            proposal(), DeploymentSnapshot("later", 1, 1, {"ERROR": 1}), rehearsal()
        )
        self.assertEqual(first.validate_current(loaded, evidence_digest=current_digest), "current-advice")
        self.assertEqual(first.validate_current(loaded, evidence_digest=changed_digest), "stale-evidence")

    def test_raw_evidence_is_superrag(self) -> None:
        memory = FakeMemory()
        board(memory).record_evidence(
            proposal(),
            DeploymentSnapshot("now", 1, 1, {"READY": 1}),
            rehearsal(),
            official_guidance={"title": "Safe rollout"},
        )
        self.assertEqual(len(memory.documents), 3)
        self.assertTrue(all(item["task_type"] == "superrag" for item in memory.documents))


if __name__ == "__main__":
    unittest.main()
