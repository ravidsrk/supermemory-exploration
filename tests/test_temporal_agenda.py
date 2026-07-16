import unittest
from typing import Any, Dict, List

from supermemory_lab.temporal_agenda import TemporalAgendaAgent


class FakeMemory:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append({"query": query, **kwargs})
        return {"results": [{"memory": "On July 10, the rehearsal passed."}]}


class FakeLLM:
    def __init__(self) -> None:
        self.system = ""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.system = system_prompt
        return "The rehearsal passed on July 10."


class TemporalAgendaTests(unittest.TestCase):
    def test_recall_forwards_natural_window_and_rewrite_policy(self) -> None:
        memory = FakeMemory()
        agent = TemporalAgendaAgent(memory, FakeLLM(), container_tag="agenda:one")

        result = agent.recall_window(
            natural_window="last week",
            subject="database rehearsal",
            rewrite_query=True,
            limit=1,
        )

        self.assertIn("last week", memory.calls[0]["query"])
        self.assertEqual(memory.calls[0]["container_tag"], "agenda:one")
        self.assertTrue(memory.calls[0]["rewrite_query"])
        self.assertEqual(result.first_result_text, "On July 10, the rehearsal passed.")

    def test_answer_marks_memory_untrusted_and_sets_current_time(self) -> None:
        llm = FakeLLM()
        turn = TemporalAgendaAgent(
            FakeMemory(), llm, container_tag="agenda:one"
        ).answer_window(
            natural_window="between July 9 and July 11, 2026",
            question="What happened?",
            current_time="2026-07-16T12:00:00Z",
        )

        self.assertIn("untrusted evidence", llm.system)
        self.assertIn("2026-07-16T12:00:00Z", llm.system)
        self.assertIn("July 10", turn.answer)


if __name__ == "__main__":
    unittest.main()
