import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.adaptive_model_router import (
    AdaptiveModelRouterAgent,
    ModelRun,
    ModelTask,
)


class FakeMemory:
    def __init__(self) -> None:
        self.policy = ""

    def create_memories(self, container_tag: str, memories: List[Mapping[str, Any]]) -> Dict[str, Any]:
        self.policy = str(memories[0]["content"])
        return {"memories": [{"id": "policy-1"}]}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": [{"memory": self.policy}]} if self.policy else {"results": []}


class FakeRunner:
    def __init__(self) -> None:
        self.calls: List[str] = []

    def run(self, model: str, system_prompt: str, user_prompt: str) -> ModelRun:
        self.calls.append(model)
        good = model != "cheap-bad"
        answer = "PASS EXACT" if good else "wrong"
        cost = {"cheap-bad": 0.000001, "cheap-good": 0.000002, "expensive": 0.01}[model]
        latency = {"cheap-bad": 10, "cheap-good": 20, "expensive": 5}[model]
        return ModelRun(model, answer, latency, 10, 2, 12, cost)


class AdaptiveModelRouterTests(unittest.TestCase):
    def test_calibration_selects_cheapest_model_at_best_quality(self) -> None:
        memory = FakeMemory()
        runner = FakeRunner()
        agent = AdaptiveModelRouterAgent(memory, runner, workspace_id="models:one")

        report = agent.calibrate(
            task_family="exact",
            tasks=[ModelTask("one", "system", "question", ("PASS", "EXACT"))],
            candidate_models=["cheap-bad", "cheap-good", "expensive"],
            policy_canary="POLICY_1",
        )

        self.assertEqual(report.winner, "cheap-good")
        self.assertIn("selected_model=cheap-good", memory.policy)

    def test_new_agent_routes_from_persisted_memory_policy(self) -> None:
        memory = FakeMemory()
        memory.policy = "MODEL_POLICY task_family=exact selected_model=cheap-good quality=1/1"
        runner = FakeRunner()
        agent = AdaptiveModelRouterAgent(memory, runner, workspace_id="models:one")

        report = agent.route(
            task_family="exact",
            system_prompt="system",
            user_prompt="question",
            candidate_models=["expensive", "cheap-good"],
        )

        self.assertEqual(report.selected_model, "cheap-good")
        self.assertEqual(report.selection_source, "supermemory-policy")
        self.assertEqual(runner.calls, ["cheap-good"])

    def test_missing_policy_uses_explicit_fallback(self) -> None:
        report = AdaptiveModelRouterAgent(
            FakeMemory(), FakeRunner(), workspace_id="models:one"
        ).route(
            task_family="unknown",
            system_prompt="system",
            user_prompt="question",
            candidate_models=["expensive", "cheap-good"],
        )

        self.assertEqual(report.selected_model, "expensive")
        self.assertEqual(report.selection_source, "configured-fallback")

    def test_failed_memory_route_falls_back_and_teaches_next_process(self) -> None:
        memory = FakeMemory()
        memory.policy = "MODEL_POLICY task_family=exact selected_model=cheap-bad quality=1/1"
        first_runner = FakeRunner()

        first = AdaptiveModelRouterAgent(
            memory, first_runner, workspace_id="models:one"
        ).route(
            task_family="exact",
            system_prompt="system",
            user_prompt="question",
            candidate_models=["cheap-bad", "expensive"],
            required_terms=["PASS"],
            fallback_model="expensive",
        )

        self.assertEqual(first.initial_model, "cheap-bad")
        self.assertEqual(first.selected_model, "expensive")
        self.assertTrue(first.fallback_used)
        self.assertIn("MODEL_POLICY_RUNTIME_FAILURE", memory.policy)

        second_runner = FakeRunner()
        second = AdaptiveModelRouterAgent(
            memory, second_runner, workspace_id="models:one"
        ).route(
            task_family="exact",
            system_prompt="system",
            user_prompt="question",
            candidate_models=["cheap-bad", "expensive"],
            required_terms=["PASS"],
            fallback_model="expensive",
        )

        self.assertEqual(second.initial_model, "expensive")
        self.assertFalse(second.fallback_used)


if __name__ == "__main__":
    unittest.main()
