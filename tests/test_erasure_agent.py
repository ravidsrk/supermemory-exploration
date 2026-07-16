import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.erasure_agent import ErasurePreview, GovernedErasureAgent


class FakeMemory:
    def __init__(self, responses: List[Dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: List[tuple] = []

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("search", query, kwargs))
        return self.responses.pop(0)

    def forget_matching(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("forget", query, kwargs))
        return self.responses.pop(0)


class ErasureAgentTests(unittest.TestCase):
    def test_filtered_search_forwards_nested_filter_without_rewriting(self) -> None:
        memory = FakeMemory([{"results": []}])
        agent = GovernedErasureAgent(memory, container_tag="tenant:one")
        filters = {
            "AND": [
                {"key": "tenant", "value": "acme"},
                {
                    "OR": [
                        {
                            "filterType": "numeric",
                            "key": "priority",
                            "value": "8",
                            "numericOperator": ">=",
                        }
                    ]
                },
            ]
        }

        agent.filtered_search("governed record", filters)

        self.assertEqual(memory.calls[0][2]["filters"], filters)
        self.assertEqual(memory.calls[0][2]["threshold"], 0.0)

    def test_preview_authorizes_only_exact_bounded_candidate_set(self) -> None:
        preview_response = {
            "dryRun": True,
            "count": 1,
            "forgetBatchId": None,
            "candidates": [
                {"id": "mem_1", "memory": "Erase TARGET_1", "score": 0.99}
            ],
        }
        apply_response = {
            "dryRun": False,
            "count": 1,
            "forgetBatchId": "batch_1",
            "forgotten": [
                {"id": "mem_1", "memory": "Erase TARGET_1", "score": 0.99}
            ],
        }
        memory = FakeMemory([preview_response, apply_response])
        agent = GovernedErasureAgent(memory, container_tag="tenant:one")

        preview = agent.preview(
            "forget TARGET_1",
            required_tokens=["TARGET_1"],
            protected_tokens=["KEEP_1"],
            max_candidates=1,
        )
        applied = agent.apply(preview, reason="synthetic erasure test")

        self.assertTrue(preview.authorized)
        self.assertEqual(applied["forgetBatchId"], "batch_1")
        self.assertTrue(memory.calls[0][2]["dry_run"])
        self.assertFalse(memory.calls[1][2]["dry_run"])
        self.assertEqual(memory.calls[1][2]["max_forget"], 1)

    def test_preview_fails_closed_on_protected_candidate(self) -> None:
        memory = FakeMemory(
            [
                {
                    "dryRun": True,
                    "count": 2,
                    "candidates": [
                        {"id": "1", "memory": "TARGET_1", "score": 0.9},
                        {"id": "2", "memory": "KEEP_1", "score": 0.8},
                    ],
                }
            ]
        )
        agent = GovernedErasureAgent(memory, container_tag="tenant:one")

        preview = agent.preview(
            "target",
            required_tokens=["TARGET_1"],
            protected_tokens=["KEEP_1"],
            max_candidates=2,
        )

        self.assertFalse(preview.authorized)
        with self.assertRaises(PermissionError):
            agent.apply(preview, reason="must not execute")

    def test_apply_detects_candidate_drift(self) -> None:
        memory = FakeMemory(
            [
                {
                    "dryRun": False,
                    "count": 1,
                    "forgotten": [
                        {"id": "other", "memory": "unexpected", "score": 0.7}
                    ],
                }
            ]
        )
        agent = GovernedErasureAgent(memory, container_tag="tenant:one")
        preview = ErasurePreview(
            "target",
            [{"id": "approved", "memory": "TARGET", "score": 0.9}],
            True,
            "approved",
            0.5,
        )

        with self.assertRaises(RuntimeError):
            agent.apply(preview, reason="test")


if __name__ == "__main__":
    unittest.main()
