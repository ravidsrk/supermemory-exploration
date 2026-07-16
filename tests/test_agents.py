import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.agents import (
    DecisionJournal,
    HandoffBoard,
    PersonalizedAgent,
    ResearchNotebookAgent,
)


class FakeLLM:
    def __init__(self, answer: str = "model answer") -> None:
        self.answer = answer
        self.calls: List[Any] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.answer


class FakeMemory:
    def __init__(self) -> None:
        self.calls: List[Any] = []
        self.profile_response: Dict[str, Any] = {
            "profile": {"static": ["User prefers Python"], "dynamic": []},
            "searchResults": {"results": []},
        }
        self.search_response: Dict[str, Any] = {"results": []}

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("profile", container_tag, kwargs))
        return self.profile_response

    def add_conversation(
        self,
        conversation_id: str,
        messages: List[Mapping[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self.calls.append(("conversation", conversation_id, list(messages), kwargs))
        return {"id": "doc_1"}

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("document", content, kwargs))
        return {"id": "doc_1"}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("search", query, kwargs))
        return self.search_response

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.calls.append(("create", container_tag, list(memories)))
        return {"memories": [{"id": "mem_1"}]}

    def update_memory(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("update", kwargs))
        return {"id": kwargs.get("memory_id")}


class AgentPatternTests(unittest.TestCase):
    def test_personalized_agent_retrieves_then_persists_same_user_scope(self) -> None:
        memory = FakeMemory()
        llm = FakeLLM()
        agent = PersonalizedAgent(memory, llm, instructions="Be helpful.")

        turn = agent.answer(
            user_id="user_alex", conversation_id="conv_1", message="Which stack?"
        )

        self.assertEqual(turn.answer, "model answer")
        self.assertEqual(memory.calls[0][0:2], ("profile", "user_alex"))
        self.assertEqual(memory.calls[1][3]["container_tags"], ["user_alex"])
        self.assertIn("User prefers Python", llm.calls[0][0])

    def test_research_notebook_uses_rag_only_ingestion_and_hybrid_recall(self) -> None:
        memory = FakeMemory()
        llm = FakeLLM()
        agent = ResearchNotebookAgent(memory, llm, notebook_id="research_alpha")

        agent.ingest_source("paper text", source_id="paper_1")
        agent.answer("What did the paper find?")

        self.assertEqual(memory.calls[0][2]["task_type"], "superrag")
        self.assertEqual(memory.calls[1][2]["search_mode"], "hybrid")
        self.assertTrue(memory.calls[1][2]["rerank"])

    def test_handoff_board_writes_exact_fact_with_agent_metadata(self) -> None:
        memory = FakeMemory()
        board = HandoffBoard(memory, board_id="team_red")

        board.publish(
            from_agent="researcher",
            task_id="task_42",
            fact="API rate limit is 60 rpm",
        )
        board.recall("rate limit")

        created = memory.calls[0][2][0]
        self.assertEqual(created["metadata"]["fromAgent"], "researcher")
        self.assertEqual(created["metadata"]["taskId"], "task_42")
        self.assertTrue(memory.calls[1][2]["aggregate"])

    def test_decision_journal_revises_by_memory_id(self) -> None:
        memory = FakeMemory()
        journal = DecisionJournal(memory, project_id="project_alpha")

        journal.record("Use PostgreSQL", owner="cto")
        journal.revise("mem_1", "Use PostgreSQL 18", reason="version policy")

        self.assertTrue(memory.calls[0][2][0]["isStatic"])
        self.assertEqual(memory.calls[1][1]["memory_id"], "mem_1")
        self.assertEqual(memory.calls[1][1]["container_tag"], "project_alpha")
        self.assertEqual(memory.calls[1][1]["new_content"], "Use PostgreSQL 18")


if __name__ == "__main__":
    unittest.main()
