import json
import unittest
from typing import Any, Dict, List

from supermemory_lab.due_diligence_campaign import (
    BudgetExceeded,
    BudgetLedger,
    BudgetedDueDiligenceCampaign,
    CampaignBudget,
    CampaignCheckpoint,
    CampaignEvidence,
)


KEY = b"due-diligence-test-signing-key-32"


class FakeMemory:
    def __init__(self) -> None:
        self.documents: List[Dict[str, Any]] = []
        self.memories: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.documents.append({"content": content, **kwargs})
        return {"id": f"doc-{len(self.documents)}"}

    def create_memories(self, container_tag: str, memories: Any) -> Dict[str, Any]:
        self.memories.extend(memories)
        return {"memories": [{"id": f"mem-{len(self.memories)}"}]}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        if "DUE_DILIGENCE_CHECKPOINT" in query and self.memories:
            return {"results": [{"id": "m", "memory": self.memories[-1]["content"]}]}
        return {"results": self.results}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "Official [E1], community [E2], and risk [E3]. No action is authorized."


class NullProvider:
    pass


def campaign(memory: FakeMemory) -> BudgetedDueDiligenceCampaign:
    null = NullProvider()
    return BudgetedDueDiligenceCampaign(
        memory,
        FakeLLM(),
        null,
        null,
        null,
        null,
        null,
        container_tag="dd:1",
        campaign_id="campaign-1",
        signing_key=KEY,
        budget=CampaignBudget(9, 0.1),
    )


def checkpoint(agent: BudgetedDueDiligenceCampaign) -> CampaignCheckpoint:
    items = (
        CampaignEvidence("E1", "context", "official.example", True, True, "now", "d1"),
        CampaignEvidence("E2", "reddit", "community", False, True, "now", "d2"),
        CampaignEvidence("E3", "exa", "github.com", False, True, "now", "d3"),
        CampaignEvidence("E4", "monid", "news.ycombinator.com", False, True, "now", "d4"),
    )
    return agent.sign_checkpoint(
        CampaignCheckpoint("campaign-1", 1, "acquired", items, {}, 4, 0.02, ("reddit",))
    )


class DueDiligenceCampaignTests(unittest.TestCase):
    def test_budget_counts_unknown_cost_and_denies_overrun(self) -> None:
        ledger = BudgetLedger(CampaignBudget(2, 0.05))
        ledger.reserve("unknown", None)
        ledger.reserve("priced", 0.04)
        self.assertEqual(ledger.calls, 2)
        self.assertEqual(ledger.unknown_cost_calls, ["unknown"])
        with self.assertRaises(BudgetExceeded):
            ledger.reserve("extra", 0.0)

    def test_monetary_budget_fails_before_charge(self) -> None:
        ledger = BudgetLedger(CampaignBudget(5, 0.01))
        with self.assertRaises(BudgetExceeded):
            ledger.reserve("expensive", 0.02)
        self.assertEqual(ledger.calls, 0)

    def test_signed_checkpoint_round_trips_across_process(self) -> None:
        memory = FakeMemory()
        first = campaign(memory)
        value = checkpoint(first)
        first.persist_checkpoint(value)

        loaded = campaign(memory).load_checkpoint()

        self.assertEqual(loaded.campaign_id, "campaign-1")
        self.assertEqual([item.evidence_id for item in loaded.evidence], ["E1", "E2", "E3", "E4"])

    def test_forged_checkpoint_is_rejected(self) -> None:
        memory = FakeMemory()
        value = checkpoint(campaign(memory))
        raw = value.__dict__.copy()
        raw["signature"] = "forged"
        memory.memories = [
            {"content": "DUE_DILIGENCE_CHECKPOINT " + json.dumps(raw, default=lambda x: x.__dict__)}
        ]
        with self.assertRaises(LookupError):
            campaign(memory).load_checkpoint()

    def test_fresh_diverse_evidence_is_ready_but_never_authorizes(self) -> None:
        agent = campaign(FakeMemory())
        report = agent.synthesize(checkpoint(agent), question="Should we pilot?", fresh_cycle=True)

        self.assertEqual(report.status, "ready")
        self.assertEqual(report.publisher_count, 4)
        self.assertFalse(report.action_authorized)

    def test_memory_only_report_is_stale_and_not_promoted(self) -> None:
        memory = FakeMemory()
        agent = campaign(memory)
        report = agent.synthesize(checkpoint(agent), question="Should we pilot?", fresh_cycle=False)
        result = agent.persist_report(report)

        self.assertEqual(report.status, "stale-only")
        self.assertTrue(report.report.startswith("MEMORY-ONLY FALLBACK"))
        self.assertEqual(result, {"promoted": False})
        self.assertEqual(memory.memories, [])

    def test_partial_fresh_portfolio_is_labeled_degraded_and_not_promoted(self) -> None:
        memory = FakeMemory()
        agent = campaign(memory)
        full = checkpoint(agent)
        partial = agent.sign_checkpoint(
            CampaignCheckpoint(
                full.campaign_id,
                full.sequence,
                full.phase,
                full.evidence[:3],
                {"monid": "401 Invalid API key"},
                3,
                0.01,
                ("reddit",),
            )
        )
        report = agent.synthesize(partial, question="Should we pilot?", fresh_cycle=True)
        result = agent.persist_report(report)

        self.assertEqual(report.status, "degraded-partial")
        self.assertEqual(result, {"promoted": False})


if __name__ == "__main__":
    unittest.main()
