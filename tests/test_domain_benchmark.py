import unittest
from typing import Any, Dict

from supermemory_lab.domain_benchmark import (
    DomainCase,
    DomainCaseResult,
    DomainMemoryQaAgent,
    percentile,
    summarize_results,
    terms_pass,
)


class FakeMemory:
    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": [{"memory": "Current value NEW_1; old value removed"}]}


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return "Current answer NEW_1" if self.calls == 1 else "UNKNOWN"


class DomainBenchmarkTests(unittest.TestCase):
    def test_term_scoring_is_case_insensitive_and_enforces_forbidden(self) -> None:
        self.assertTrue(terms_pass("The answer is Alpha", required=["alpha"], forbidden=["beta"]))
        self.assertFalse(terms_pass("Alpha and beta", required=["alpha"], forbidden=["beta"]))

    def test_term_scoring_accepts_semantically_equivalent_date_format(self) -> None:
        self.assertTrue(
            terms_pass(
                "The launch is September 1, 2026.",
                required=["2026-09-01"],
                forbidden=["2026-08-15"],
            )
        )

    def test_agent_scores_memory_and_matched_no_memory_baseline(self) -> None:
        case = DomainCase(
            "updated-fact",
            "update",
            "What is current?",
            ["NEW_1"],
            ["OLD_1"],
            ["NEW_1"],
            ["OLD_1"],
        )
        agent = DomainMemoryQaAgent(FakeMemory(), FakeLLM(), container_tag="one")

        result = agent.run_case(case)

        self.assertTrue(result.memory_passed)
        self.assertFalse(result.baseline_passed)
        self.assertTrue(result.retrieval_passed)
        self.assertGreater(result.estimated_context_tokens, 0)

    def test_summary_reports_lift_categories_and_nearest_rank_latency(self) -> None:
        rows = [
            DomainCaseResult(
                str(index),
                "stable" if index < 2 else "update",
                "answer",
                "baseline",
                index != 2,
                False,
                True,
                float(index * 100),
                1,
                1,
                100,
                25,
            )
            for index in range(1, 4)
        ]

        summary = summarize_results(rows)

        self.assertEqual(summary["memoryAccuracyPct"], 66.7)
        self.assertEqual(summary["accuracyLiftPoints"], 66.7)
        self.assertEqual(summary["searchLatencyP50Ms"], 200.0)
        self.assertEqual(percentile([100, 200, 300], 0.95), 300.0)
        self.assertEqual(summary["categories"]["stable"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
