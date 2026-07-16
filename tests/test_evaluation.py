import unittest
from typing import Any, Dict, List

from supermemory_lab.evaluation import (
    ConsistencyMatrix,
    RetrievalQuery,
    VisibilityCase,
    contains_text,
    required_term_score,
)


class FakeMemory:
    def __init__(self) -> None:
        self.profile_calls = 0
        self.memory_calls = 0
        self.hybrid_calls = 0
        self.forgotten: List[str] = []

    def create_memories(self, container_tag: str, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"memories": [{"id": "mem_1"}]}

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        self.profile_calls += 1
        return {"profile": {"static": ["fact CANARY"]}}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        if kwargs["search_mode"] == "memories":
            self.memory_calls += 1
            return {"results": [] if self.memory_calls == 1 else [{"memory": "CANARY"}]}
        self.hybrid_calls += 1
        return {"results": [{"chunk": "CANARY"}]}

    def forget_memory(self, **kwargs: Any) -> Dict[str, Any]:
        self.forgotten.append(kwargs["memory_id"])
        return {"forgotten": True}


class EvaluationTests(unittest.TestCase):
    def test_nested_text_and_required_term_scoring(self) -> None:
        self.assertTrue(contains_text({"a": [{"memory": "hello CANARY"}]}, "CANARY"))
        self.assertFalse(contains_text({"a": [1, 2]}, "CANARY"))
        self.assertTrue(required_term_score("Use Orion and a trace ID", ["orion", "trace id"]))

    def test_consistency_matrix_tracks_each_path_and_cleans_up(self) -> None:
        now = [0.0]

        def clock() -> float:
            now[0] += 0.01
            return now[0]

        def sleep(seconds: float) -> None:
            now[0] += seconds

        memory = FakeMemory()
        result = ConsistencyMatrix(memory, clock=clock, sleeper=sleep).run_case(
            VisibilityCase("short", "CANARY", True),
            container_tag="one",
            canary="CANARY",
            timeout_seconds=5,
            poll_seconds=0.1,
        )

        self.assertIsNotNone(result["firstSeenMs"]["profile"])
        self.assertIsNotNone(result["firstSeenMs"]["memories"])
        self.assertIsNotNone(result["firstSeenMs"]["hybrid"])
        self.assertEqual(result["attempts"]["memories"], 2)
        self.assertEqual(memory.forgotten, ["mem_1"])

    def test_query_sensitivity_compares_profile_memories_and_hybrid(self) -> None:
        memory = FakeMemory()
        result = ConsistencyMatrix(memory).run_query_sensitivity(
            content="CANARY chosen tool",
            container_tag="one",
            canary="CANARY",
            queries=[RetrievalQuery("natural", "chosen tool", True)],
        )

        observation = result["queries"][0]
        self.assertTrue(observation["profileContains"])
        self.assertTrue(observation["hybridContains"])
        self.assertEqual(result["cleanupErrors"], [])


if __name__ == "__main__":
    unittest.main()
