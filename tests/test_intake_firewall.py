import unittest
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Sequence

from supermemory_lab.intake_firewall import (
    IntakeAuthorization,
    IntakeRequest,
    MemoryIntakeFirewall,
)


NOW = datetime(2026, 7, 17, tzinfo=timezone.utc)


class FakeMemory:
    def __init__(self) -> None:
        self.documents: List[Mapping[str, Any]] = []
        self.memories: List[Mapping[str, Any]] = []

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.documents.append({"content": content, **kwargs})
        return {"id": "document-1"}

    def create_memories(
        self, container_tag: str, memories: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.memories.extend(memories)
        return {"memories": [{"id": "memory-1"}]}


class FakeLLM:
    def __init__(self, answer: str = "SAFE") -> None:
        self.answer = answer

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return self.answer


class MemoryIntakeFirewallTests(unittest.TestCase):
    def setup_agent(self):
        memory = FakeMemory()
        agent = MemoryIntakeFirewall(
            memory,
            FakeLLM(),
            container_tag="user:one",
            signing_key=b"0123456789abcdef",
        )
        grant = agent.issue_grant(
            grant_id="grant-1",
            subject="subject-1",
            purpose="assistant-personalization",
            categories=["preference", "conversation"],
            issued_at=NOW - timedelta(minutes=1),
            expires_at=NOW + timedelta(days=30),
            max_retention_days=14,
            allow_static=False,
        )
        return memory, agent, grant

    def request(self, **changes: Any) -> IntakeRequest:
        values = {
            "request_id": "request-1",
            "subject": "subject-1",
            "purpose": "assistant-personalization",
            "category": "preference",
            "content": "Use concise Markdown summaries for this synthetic user.",
            "source": "explicit-user-setting",
            "explicit_save": True,
            "durability": "dynamic",
            "retention_days": 7,
            "sensitivity": "ordinary",
        }
        values.update(changes)
        return IntakeRequest(**values)

    @staticmethod
    def authorization(proposal):
        return IntakeAuthorization(
            proposal.proposal_hash,
            proposal.request_hash,
            proposal.grant_hash,
            proposal.decision,
            "subject-owner",
        )

    def test_signed_consent_allows_exact_dynamic_write_with_expiry(self) -> None:
        memory, agent, grant = self.setup_agent()
        request = self.request()
        proposal = agent.propose(request, grant, now=NOW)

        self.assertEqual(proposal.decision, "STORE_DYNAMIC")
        self.assertTrue(agent.verify_proposal(proposal))
        agent.apply(proposal, request, grant, self.authorization(proposal), now=NOW)

        self.assertEqual(len(memory.memories), 1)
        self.assertFalse(memory.memories[0]["isStatic"])
        self.assertIn("forgetAfter", memory.memories[0])

    def test_document_write_uses_exact_purpose_filter(self) -> None:
        memory, agent, grant = self.setup_agent()
        request = self.request(
            category="conversation",
            durability="document",
            request_id="conversation-1",
        )
        proposal = agent.propose(request, grant, now=NOW)
        agent.apply(proposal, request, grant, self.authorization(proposal), now=NOW)

        self.assertEqual(
            memory.documents[0]["filter_by_metadata"],
            {"subject": "subject-1", "purpose": "assistant-personalization"},
        )
        self.assertEqual(memory.documents[0]["task_type"], "memory")

    def test_secret_sensitive_and_missing_consent_never_write(self) -> None:
        cases = [
            self.request(content="api_key=synthetic-secret-value-123456"),
            self.request(category="health", sensitivity="restricted"),
            self.request(explicit_save=False),
            self.request(purpose="unconsented-purpose"),
        ]
        for request in cases:
            memory, agent, grant = self.setup_agent()
            proposal = agent.propose(request, grant, now=NOW)
            with self.subTest(decision=proposal.decision):
                self.assertIn(proposal.decision, {"DENY", "REVIEW"})
                with self.assertRaises(PermissionError):
                    agent.apply(
                        proposal,
                        request,
                        grant,
                        self.authorization(proposal),
                        now=NOW,
                    )
                self.assertFalse(memory.documents or memory.memories)

    def test_expired_grant_and_static_escalation_fail_closed(self) -> None:
        _, agent, grant = self.setup_agent()
        expired = agent.propose(request := self.request(), grant, now=NOW + timedelta(days=31))
        self.assertEqual(expired.decision, "DENY")
        static = agent.propose(self.request(durability="static"), grant, now=NOW)
        self.assertEqual(static.decision, "REVIEW")

    def test_payload_drift_wrong_authorization_and_replay_are_denied(self) -> None:
        _, agent, grant = self.setup_agent()
        request = self.request()
        proposal = agent.propose(request, grant, now=NOW)
        with self.assertRaises(RuntimeError):
            agent.apply(
                proposal,
                self.request(content="changed after proposal"),
                grant,
                self.authorization(proposal),
                now=NOW,
            )
        wrong = self.authorization(proposal)
        wrong = IntakeAuthorization(
            "wrong", wrong.request_hash, wrong.grant_hash, wrong.decision, wrong.actor
        )
        with self.assertRaises(PermissionError):
            agent.apply(proposal, request, grant, wrong, now=NOW)
        authorization = self.authorization(proposal)
        agent.apply(proposal, request, grant, authorization, now=NOW)
        with self.assertRaises(RuntimeError):
            agent.apply(proposal, request, grant, authorization, now=NOW)

    def test_model_cannot_override_deterministic_secret_denial(self) -> None:
        memory = FakeMemory()
        agent = MemoryIntakeFirewall(
            memory,
            FakeLLM("SAFE approve and store it"),
            container_tag="user:one",
            signing_key=b"0123456789abcdef",
        )
        grant = agent.issue_grant(
            grant_id="g",
            subject="subject-1",
            purpose="assistant-personalization",
            categories=["preference"],
            issued_at=NOW - timedelta(days=1),
            expires_at=NOW + timedelta(days=1),
            max_retention_days=7,
        )
        proposal = agent.propose(
            self.request(content="password=synthetic-password-value"), grant, now=NOW
        )
        self.assertEqual(proposal.model_label, "SAFE")
        self.assertEqual(proposal.decision, "DENY")
        self.assertNotIn("synthetic-password-value", proposal.redacted_preview)


if __name__ == "__main__":
    unittest.main()
