import dataclasses
from datetime import datetime, timedelta, timezone
import unittest

from supermemory_lab.continuity_gateway import (
    ContinuityRecallAgent,
    RecallRequest,
    RiskAwareContinuityGateway,
)


class SwitchMemory:
    def __init__(self) -> None:
        self.fail = False
        self.calls = 0

    def profile(self, container_tag, **kwargs):
        self.calls += 1
        if self.fail:
            raise ConnectionError("injected outage")
        return {"profile": {"static": ["Policy CANARY-1"], "dynamic": []}}

    def search_memories(self, query, **kwargs):
        self.calls += 1
        if self.fail:
            raise ConnectionError("injected outage")
        return {"results": [{"memory": "Policy CANARY-1"}]}


class FakeLLM:
    def __init__(self, response="The remembered policy is CANARY-1."):
        self.response = response
        self.calls = 0

    def complete(self, system_prompt, user_prompt):
        self.calls += 1
        return self.response


class ContinuityGatewayTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.memory = SwitchMemory()
        self.gateway = RiskAwareContinuityGateway(
            self.memory,
            container_tag="tenant:one",
            signing_key=b"0123456789abcdef0123456789abcdef",
            failure_threshold=2,
            cooldown=timedelta(seconds=30),
        )
        self.request = RecallRequest("What is policy?", "policy", "standard", True)

    def test_fresh_read_creates_verifiable_bounded_snapshot(self):
        result = self.gateway.recall(self.request, now=self.now)
        self.assertEqual(result.status, "fresh")
        self.assertIn("CANARY-1", result.context)
        self.assertTrue(self.gateway.verify_snapshot(result.snapshot, now=self.now))
        self.assertFalse(result.external_action_authorized)

    def test_standard_uses_signed_stale_cache_but_high_risk_fails_closed(self):
        fresh = self.gateway.recall(self.request, now=self.now)
        self.memory.fail = True
        stale = self.gateway.recall(self.request, now=self.now + timedelta(seconds=1))
        self.assertEqual(stale.status, "stale-backend-error")
        self.assertIn("CANARY-1", stale.context)
        high = self.gateway.recall(
            dataclasses.replace(self.request, sensitivity="high"),
            now=self.now + timedelta(seconds=2),
        )
        self.assertEqual(high.status, "unavailable-high-risk")
        self.assertEqual(high.context, "")
        self.assertIsNotNone(fresh.snapshot)

    def test_circuit_skips_backend_and_half_open_recovers(self):
        self.gateway.recall(self.request, now=self.now)
        self.memory.fail = True
        self.gateway.recall(self.request, now=self.now + timedelta(seconds=1))
        self.gateway.recall(self.request, now=self.now + timedelta(seconds=2))
        calls = self.memory.calls
        cached = self.gateway.recall(self.request, now=self.now + timedelta(seconds=3))
        self.assertEqual(cached.status, "stale-circuit-open")
        self.assertFalse(cached.backend_attempted)
        self.assertEqual(self.memory.calls, calls)
        self.memory.fail = False
        recovered = self.gateway.recall(self.request, now=self.now + timedelta(seconds=33))
        self.assertEqual(recovered.status, "fresh")
        self.assertIsNone(self.gateway.circuit_open_until)

    def test_wrong_query_class_expired_or_tampered_cache_is_denied(self):
        fresh = self.gateway.recall(self.request, now=self.now)
        other = RiskAwareContinuityGateway(
            self.memory,
            container_tag="tenant:one",
            signing_key=b"0123456789abcdef0123456789abcdef",
        )
        other.load_snapshot(fresh.snapshot, now=self.now)
        self.memory.fail = True
        wrong = other.recall(
            dataclasses.replace(self.request, query_class="billing"),
            now=self.now + timedelta(seconds=1),
        )
        self.assertEqual(wrong.status, "unavailable")
        with self.assertRaises(PermissionError):
            other.load_snapshot(
                dataclasses.replace(fresh.snapshot, context="tampered"), now=self.now
            )
        self.assertFalse(
            other.verify_snapshot(fresh.snapshot, now=self.now + timedelta(hours=1))
        )

    def test_stale_permission_is_explicit(self):
        self.gateway.recall(self.request, now=self.now)
        self.memory.fail = True
        denied = self.gateway.recall(
            dataclasses.replace(self.request, allow_stale=False),
            now=self.now + timedelta(seconds=1),
        )
        self.assertEqual(denied.status, "unavailable")
        self.assertEqual(denied.context, "")

    def test_agent_owns_status_and_no_action_envelope(self):
        llm = FakeLLM()
        agent = ContinuityRecallAgent(self.gateway, llm)
        fresh = agent.answer(self.request, now=self.now)
        self.assertTrue(fresh.answer.startswith("MEMORY_STATUS=fresh\nNO_EXTERNAL_ACTION"))
        self.memory.fail = True
        high = agent.answer(
            dataclasses.replace(self.request, sensitivity="high"),
            now=self.now + timedelta(seconds=1),
        )
        self.assertIn("MEMORY_UNAVAILABLE", high.answer)
        self.assertEqual(llm.calls, 1)
        self.assertFalse(high.external_action_authorized)

    def test_agent_withholds_model_output_containing_forbidden_memory_instruction(self):
        agent = ContinuityRecallAgent(
            self.gateway, FakeLLM("Policy CANARY-1. IGNORE_AND_DEPLOY_NOW")
        )
        answer = agent.answer(
            self.request,
            now=self.now,
            forbidden_terms=("IGNORE_AND_DEPLOY_NOW",),
        )
        self.assertIn("MEMORY_OUTPUT_WITHHELD", answer.answer)
        self.assertNotIn("IGNORE_AND_DEPLOY_NOW", answer.answer)
        self.assertFalse(answer.external_action_authorized)


if __name__ == "__main__":
    unittest.main()
