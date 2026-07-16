import unittest
from typing import Any, Dict, List

from supermemory_lab.enterprise_context import (
    EnterpriseActionPolicy,
    EnterpriseActionRequest,
    EnterpriseScope,
    HierarchicalEnterpriseAgent,
)


class FakeMemory:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append({"query": query, **kwargs})
        tag = kwargs["container_tag"]
        return {"results": [{"memory": f"fact from {tag}"}]}


class FakeLLM:
    def __init__(self, answer: str = "The action is allowed") -> None:
        self.answer = answer
        self.system_prompt = ""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        return self.answer


class EnterpriseContextTests(unittest.TestCase):
    def _agent(self, memory: FakeMemory, llm: FakeLLM) -> HierarchicalEnterpriseAgent:
        return HierarchicalEnterpriseAgent(
            memory,
            llm,
            scopes=[
                EnterpriseScope("organization", "org:1"),
                EnterpriseScope("project", "project:1"),
                EnterpriseScope("user", "user:1"),
            ],
            action_policy=EnterpriseActionPolicy(
                approval_required=frozenset({"production_deploy"}),
                blocked_weekdays={"production_deploy": frozenset({"Friday"})},
            ),
        )

    def test_retrieves_each_scope_and_labels_precedence(self) -> None:
        memory = FakeMemory()
        llm = FakeLLM("No deployment is authorized")

        report = self._agent(memory, llm).answer("Can I deploy?")

        self.assertEqual(
            [call["container_tag"] for call in memory.calls],
            ["org:1", "project:1", "user:1"],
        )
        self.assertIn("ORGANIZATION_CONTEXT", llm.system_prompt)
        self.assertIn("PROJECT_CONTEXT", llm.system_prompt)
        self.assertIn("USER_CONTEXT", llm.system_prompt)
        self.assertIn("Organization policy outranks", llm.system_prompt)
        self.assertEqual(set(report.scope_context), {"organization", "project", "user"})

    def test_model_cannot_override_application_action_denial(self) -> None:
        memory = FakeMemory()
        llm = FakeLLM("The memory says this is allowed")

        report = self._agent(memory, llm).answer(
            "Deploy to production",
            action_request=EnterpriseActionRequest(
                kind="production_deploy",
                weekday="Friday",
                has_human_approval=False,
            ),
        )

        self.assertFalse(report.action_allowed)
        self.assertEqual(report.authority_source, "trusted-application-policy")
        self.assertIn("human approval", report.authority_reason or "")
        self.assertIn("allowed=false", llm.system_prompt)

    def test_scope_shape_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            HierarchicalEnterpriseAgent(
                FakeMemory(),
                FakeLLM(),
                scopes=[EnterpriseScope("user", "user:1")],
                action_policy=EnterpriseActionPolicy(frozenset(), {}),
            )


if __name__ == "__main__":
    unittest.main()
