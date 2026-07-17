import unittest

from supermemory_lab.authorization import TestingAuthorizationLedger
from supermemory_lab.framework_integrations import (
    FRAMEWORK_CONTRACTS,
    MemoryIntegrationBridge,
)


class FakeMemory:
    def __init__(self) -> None:
        self.profile_calls = []
        self.conversations = []
        self.memories = []

    def profile(self, container_tag, **kwargs):
        self.profile_calls.append((container_tag, kwargs))
        return {"profile": {"static": ["Prefers concise answers"]}}

    def add_conversation(self, conversation_id, messages, **kwargs):
        self.conversations.append((conversation_id, messages, kwargs))
        return {"id": conversation_id}

    def create_memories(self, container_tag, memories):
        self.memories.extend(memories)
        return {"memories": [{"id": "m1"}]}


class FrameworkIntegrationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = FakeMemory()
        self.ledger = TestingAuthorizationLedger()
        self.bridge = MemoryIntegrationBridge(
            self.memory,
            container_tag="tenant:one",
            custom_id="conversation:one",
            authorization_ledger=self.ledger,
        )

    def test_every_advertised_surface_has_runnable_recall_and_capture(self) -> None:
        for contract in FRAMEWORK_CONTRACTS:
            with self.subTest(surface=contract.surface):
                config = self.bridge.framework_config(contract.surface)
                context = self.bridge.before_turn(contract.surface, "How should I answer?")
                result = self.bridge.after_turn(
                    contract.surface,
                    [
                        {"role": "user", "content": "Be concise"},
                        {"role": "assistant", "content": "Understood"},
                    ],
                )
                self.assertFalse(config["failOpen"])
                self.assertTrue(context.endswith("</retrieved-memory>"))
                self.assertEqual(result["id"], "conversation:one")

        self.assertEqual(len(self.memory.profile_calls), len(FRAMEWORK_CONTRACTS))
        self.assertEqual(len(self.memory.conversations), len(FRAMEWORK_CONTRACTS))
        self.assertTrue(
            all(call[0] == "tenant:one" for call in self.memory.profile_calls)
        )

    def test_current_wrapper_contract_requires_identity_and_fails_closed(self) -> None:
        vercel = self.bridge.framework_config("vercel-ai-sdk")
        mastra = self.bridge.framework_config("mastra")
        self.assertEqual(vercel["mode"], "full")
        self.assertFalse(vercel["skipMemoryOnError"])
        self.assertEqual(mastra["addMemory"], "always")
        with self.assertRaises(ValueError):
            MemoryIntegrationBridge(
                self.memory,
                container_tag="tenant:one",
                custom_id="",
                authorization_ledger=self.ledger,
            )

    def test_mcp_contract_and_explicit_write_authorization(self) -> None:
        config = self.bridge.framework_config("mcp")
        self.assertEqual(config["tools"], ("memory", "recall"))
        self.assertIn("context", config["prompts"])
        schemas = self.bridge.mcp_tool_schemas()
        self.assertFalse(schemas["memory"]["inputSchema"]["additionalProperties"])
        with self.assertRaises(PermissionError):
            self.bridge.invoke_memory_tool("Store this", actor="operator")
        self.ledger.grant(
            scope="integration.memory.create",
            actor="operator",
            resource_hash=self.bridge.memory_write_resource("Store this"),
        )
        self.bridge.invoke_memory_tool("Store this", actor="operator")
        self.assertEqual(len(self.memory.memories), 1)
        with self.assertRaises(RuntimeError):
            self.bridge.invoke_memory_tool("Store this", actor="operator")

    def test_unknown_surface_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.bridge.framework_config("unknown")


if __name__ == "__main__":
    unittest.main()
