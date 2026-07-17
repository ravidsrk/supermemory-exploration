import unittest

from supermemory_lab.client import SupermemoryClient
from supermemory_lab.config import LabConfig
from supermemory_lab.live import build_live_clients


class LiveClientFactoryTests(unittest.TestCase):
    def test_memory_only_configuration_does_not_require_auxiliary_keys(self) -> None:
        clients = build_live_clients(LabConfig(supermemory_api_key="synthetic-memory-key"))

        self.assertIsInstance(clients.memory, SupermemoryClient)
        with self.assertRaisesRegex(RuntimeError, "OPENROUTER_API_KEY"):
            _ = clients.llm

    def test_provider_instances_are_cached_after_lazy_construction(self) -> None:
        clients = build_live_clients(LabConfig(supermemory_api_key="synthetic-memory-key"))
        self.assertIs(clients.memory, clients.memory)


if __name__ == "__main__":
    unittest.main()
