import unittest
from typing import Any, Dict, List, Mapping, Optional

from supermemory_lab.personalization_agent import EvolvingPreferenceAgent


class FakeMemory:
    def __init__(self) -> None:
        self.calls: List[tuple] = []

    def update_container_settings(self, tag: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("settings", tag, kwargs))
        return {"containerTag": tag, **kwargs}

    def add_conversation(
        self,
        conversation_id: str,
        messages: List[Mapping[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        self.calls.append(("conversation", conversation_id, messages, kwargs))
        return {"accepted": True}

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("profile", container_tag, kwargs))
        return {
            "profile": {
                "buckets": {
                    "communication-preferences": [
                        "[Recent] Prefers daily Markdown summaries"
                    ]
                }
            }
        }

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("search", query, kwargs))
        return {"results": [{"memory": "Prefers daily Markdown summaries"}]}

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.calls.append(("create", container_tag, memories))
        return {"memories": [{"id": "mem_1"}]}

    def update_memory(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("update", kwargs))
        return {"id": "mem_2", "version": 2}


class FakeLLM:
    def __init__(self) -> None:
        self.system_prompt: Optional[str] = None

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        return "I will provide daily Markdown summaries."


class PersonalizationAgentTests(unittest.TestCase):
    def test_configures_container_specific_extraction_policy(self) -> None:
        memory = FakeMemory()
        agent = EvolvingPreferenceAgent(memory, FakeLLM(), container_tag="user:one")

        agent.configure(name="Synthetic user")

        call = memory.calls[0]
        self.assertEqual(call[0:2], ("settings", "user:one"))
        self.assertIn("later user corrections", call[2]["entity_context"])
        self.assertEqual(len(call[2]["profile_buckets"]), 3)

    def test_upserts_full_conversation_and_uses_profile_plus_search(self) -> None:
        memory = FakeMemory()
        llm = FakeLLM()
        agent = EvolvingPreferenceAgent(memory, llm, container_tag="user:one")
        history = [
            {"role": "user", "content": "I prefer weekly PDF reports."},
            {"role": "user", "content": "Correction: I prefer daily Markdown."},
        ]

        agent.record_history("conversation-1", history, revision=2)
        result = agent.answer("How should reports be delivered?")

        conversation = memory.calls[0]
        self.assertEqual(conversation[1], "conversation-1")
        self.assertEqual(conversation[2], history)
        self.assertEqual(conversation[3]["metadata"]["revision"], 2)
        self.assertIn("daily Markdown", result.answer)
        self.assertIn("PROFILE MEMORY", llm.system_prompt or "")
        self.assertIn("SEARCH EVIDENCE", llm.system_prompt or "")
        self.assertIn("later explicit correction", llm.system_prompt or "")

    def test_normalized_preference_is_versioned_instead_of_duplicated(self) -> None:
        memory = FakeMemory()
        agent = EvolvingPreferenceAgent(memory, FakeLLM(), container_tag="user:one")

        created = agent.record_explicit_preference("Prefers weekly PDF reports")
        updated = agent.correct_explicit_preference(
            created["memories"][0]["id"],
            content="Prefers daily Markdown reports and no PDF",
        )

        self.assertEqual(memory.calls[0][0:2], ("create", "user:one"))
        self.assertEqual(
            memory.calls[0][2][0]["metadata"]["profileBucket"],
            "communication-preferences",
        )
        self.assertEqual(memory.calls[1][0], "update")
        self.assertEqual(memory.calls[1][1]["memory_id"], "mem_1")
        self.assertEqual(updated["version"], 2)


if __name__ == "__main__":
    unittest.main()
