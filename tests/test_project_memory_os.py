import unittest
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence

from supermemory_lab.project_memory_os import (
    ArtifactVerification,
    ProjectMemoryOS,
    TransitionAuthorization,
)


class FakeMemory:
    def __init__(self) -> None:
        self.by_container: Dict[str, List[Mapping[str, Any]]] = {}

    def create_memories(
        self, container_tag: str, memories: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.by_container.setdefault(container_tag, []).extend(memories)
        return {"memories": [{"id": f"m-{len(self.by_container[container_tag])}"}]}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": self.by_container.get(kwargs["container_tag"], [])}


class FakeLLM:
    def __init__(self) -> None:
        self.answer = "STATE planned OWNER agent NEXT active"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.answer


class RepairLLM:
    def __init__(self, answers: Sequence[str]) -> None:
        self.answers = list(answers)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.answers.pop(0)


class ProjectMemoryOSTests(unittest.TestCase):
    def agent(self, memory: FakeMemory, llm: FakeLLM) -> ProjectMemoryOS:
        return ProjectMemoryOS(
            memory,
            llm,
            project_container="project:one",
            organization_container="org:one",
            user_container="user:one",
            project_id="p1",
            signing_key=b"0123456789abcdef",
        )

    def apply(self, agent: ProjectMemoryOS, target: str, artifact=None) -> None:
        proposal = agent.propose_transition(
            target_state=target,
            owner="agent",
            due_at="2026-08-01T00:00:00+00:00",
            instruction="Propose state",
            required_markers=["STATE"],
            artifact=artifact,
        )
        agent.apply_transition(
            proposal,
            TransitionAuthorization(
                proposal.target_state,
                proposal.predecessor_digest,
                proposal.summary_digest,
                proposal.artifact_digest,
                "owner",
            ),
        )

    def test_signed_chain_resumes_across_fresh_process(self) -> None:
        memory, llm = FakeMemory(), FakeLLM()
        agent = self.agent(memory, llm)
        self.apply(agent, "planned")
        llm.answer = "STATE active OWNER agent NEXT review"
        self.apply(agent, "active")

        resumed = self.agent(memory, llm).resume()
        self.assertEqual([item.state for item in resumed.chain], ["planned", "active"])
        self.assertEqual(resumed.next_state, "review")

    def test_invalid_transition_and_wrong_authorization_fail_closed(self) -> None:
        memory, llm = FakeMemory(), FakeLLM()
        agent = self.agent(memory, llm)
        with self.assertRaises(PermissionError):
            agent.propose_transition(
                target_state="done",
                owner="agent",
                due_at="2026-08-01T00:00:00+00:00",
                instruction="skip",
                required_markers=["STATE"],
            )
        proposal = agent.propose_transition(
            target_state="planned",
            owner="agent",
            due_at="2026-08-01T00:00:00+00:00",
            instruction="plan",
            required_markers=["STATE"],
        )
        with self.assertRaises(PermissionError):
            agent.apply_transition(
                proposal,
                TransitionAuthorization(
                    "planned", "GENESIS", "wrong", "", "owner"
                ),
            )

    def test_review_and_done_require_verified_artifact(self) -> None:
        memory, llm = FakeMemory(), FakeLLM()
        agent = self.agent(memory, llm)
        self.apply(agent, "planned")
        self.apply(agent, "active")
        with self.assertRaises(PermissionError):
            agent.propose_transition(
                target_state="review",
                owner="reviewer",
                due_at="2026-08-01T00:00:00+00:00",
                instruction="review",
                required_markers=["STATE"],
            )
        artifact = ArtifactVerification("a1", "digest", True, "sandbox")
        self.apply(agent, "review", artifact)
        self.apply(agent, "done", artifact)
        self.assertEqual(agent.resume().current_state, "done")

    def test_forged_checkpoint_is_ignored(self) -> None:
        memory, llm = FakeMemory(), FakeLLM()
        memory.by_container["project:one"] = [
            {"content": 'PROJECT_CHECKPOINT {"project_id":"p1"}'}
        ]
        resumed = self.agent(memory, llm).resume()
        self.assertEqual(resumed.invalid_records_ignored, 1)
        self.assertEqual(resumed.chain, ())

    def test_brief_uses_trusted_policy_and_never_authorizes(self) -> None:
        memory, llm = FakeMemory(), FakeLLM()
        agent = self.agent(memory, llm)
        self.apply(agent, "planned")
        llm.answer = "Use canonical Python policy; human action remains required."
        brief = agent.build_brief(
            now=datetime(2026, 7, 20, tzinfo=timezone.utc),
            canonical_organization_policy="Python only",
        )
        self.assertEqual(brief.current_state, "planned")
        self.assertEqual(brief.due_status, "on-track")
        self.assertFalse(brief.action_authorized)

    def test_one_format_repair_is_bounded_and_still_contract_checked(self) -> None:
        memory = FakeMemory()
        repaired = self.agent(
            memory,
            RepairLLM(["I planned it.", "STATE=planned OWNER=agent NEXT=active"]),
        )
        proposal = repaired.propose_transition(
            target_state="planned",
            owner="agent",
            due_at="2026-08-01T00:00:00+00:00",
            instruction="plan",
            required_markers=["STATE=planned", "OWNER=agent", "NEXT=active"],
        )
        self.assertIn("STATE=planned", proposal.summary)

        denied = self.agent(memory, RepairLLM(["invalid", "still invalid"]))
        with self.assertRaises(ValueError):
            denied.propose_transition(
                target_state="planned",
                owner="agent",
                due_at="2026-08-01T00:00:00+00:00",
                instruction="plan",
                required_markers=["STATE=planned"],
            )


if __name__ == "__main__":
    unittest.main()
