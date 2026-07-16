import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.evaluation import RetrievalQuery
from supermemory_lab.retrieval_tuning import (
    RetrievalPolicy,
    RetrievalPolicyTuner,
    TunedRecallAgent,
)


class FakeMemory:
    def __init__(self) -> None:
        self.forgotten: List[str] = []
        self.calls: List[Any] = []

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        return {"memories": [{"id": "mem_1"}]}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append((query, kwargs))
        if "unrelated" in query:
            return {"results": []}
        if kwargs.get("rewrite_query"):
            return {"results": [{"memory": "Chosen CANARY policy"}]}
        return {"results": []}

    def forget_memory(self, **kwargs: Any) -> Dict[str, Any]:
        self.forgotten.append(kwargs["memory_id"])
        return {"forgotten": True}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "Use the chosen policy."


class RetrievalTuningTests(unittest.TestCase):
    def test_tuner_scores_grid_selects_recall_and_cleans_up(self) -> None:
        memory = FakeMemory()
        no_rewrite = RetrievalPolicy("memories", 0.5, False, False)
        rewrite = RetrievalPolicy("memories", 0.5, False, True)
        result = RetrievalPolicyTuner(memory).run(
            container_tag="tuning",
            content="Chosen CANARY policy",
            canary="CANARY",
            queries=[
                RetrievalQuery("positive", "chosen policy", True),
                RetrievalQuery("control", "unrelated control", False),
            ],
            policies=[no_rewrite, rewrite],
        )

        self.assertEqual(result["searchCount"], 4)
        self.assertTrue(result["winner"]["policy"]["rewrite_query"])
        self.assertEqual(result["winner"]["correct"], 2)
        self.assertEqual(memory.forgotten, ["mem_1"])

    def test_tuned_agent_applies_every_policy_knob(self) -> None:
        memory = FakeMemory()
        policy = RetrievalPolicy("hybrid", 0.7, True, True, limit=4)
        report = TunedRecallAgent(
            memory,
            FakeLLM(),
            workspace_id="agent-memory",
            policy=policy,
            query_prefix="safe tool-decision policy",
        ).answer("chosen policy")

        query = memory.calls[-1][0]
        kwargs = memory.calls[-1][1]
        self.assertTrue(query.startswith("safe tool-decision policy"))
        self.assertEqual(kwargs["search_mode"], "hybrid")
        self.assertEqual(kwargs["threshold"], 0.7)
        self.assertTrue(kwargs["rerank"])
        self.assertTrue(kwargs["rewrite_query"])
        self.assertEqual(kwargs["limit"], 4)
        self.assertIn("CANARY", report.retrieved_context)
        self.assertEqual(report.retrieval_query, query)


if __name__ == "__main__":
    unittest.main()
