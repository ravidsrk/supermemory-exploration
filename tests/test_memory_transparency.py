import unittest
from typing import Any, Dict, List, Mapping, Sequence

from supermemory_lab.authorization import TestingAuthorizationLedger

from supermemory_lab.memory_transparency import (
    ErasureAuthorization,
    MemoryTransparencyAgent,
)


class FakeMemory:
    def __init__(self) -> None:
        self.documents: List[Mapping[str, Any]] = [
            {"id": "d1", "customId": "source-1", "status": "done", "metadata": {}}
        ]
        self.memories: List[Mapping[str, Any]] = [
            {
                "id": "m2",
                "memory": "Current preference",
                "version": 2,
                "history": [
                    {
                        "id": "m1",
                        "memory": "Old preference",
                        "version": 1,
                        "parentMemoryId": None,
                    }
                ],
            }
        ]
        self.chunks = {"d1": ["Source one"]}
        self.deleted: List[str] = []
        self.forgotten: List[str] = []

    def list_documents(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "memories": self.documents,
            "pagination": {"totalItems": len(self.documents)},
        }

    def get_document_chunks(self, document_id: str) -> Dict[str, Any]:
        return {
            "chunks": [
                {"position": index, "content": content}
                for index, content in enumerate(self.chunks[document_id])
            ]
        }

    def list_memory_entries(
        self, container_tags: Sequence[str], **kwargs: Any
    ) -> Dict[str, Any]:
        return {"memoryEntries": self.memories, "total": len(self.memories)}

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        return {"profile": {"static": ["one"], "dynamic": [], "buckets": {}}}

    def bulk_delete_documents(self, document_ids: Sequence[str]) -> Dict[str, Any]:
        self.deleted.extend(document_ids)
        self.documents = [item for item in self.documents if item["id"] not in document_ids]
        return {"success": True, "deleted": len(document_ids)}

    def forget_memory(self, *, memory_id: str, container_tag: str) -> Dict[str, Any]:
        self.forgotten.append(memory_id)
        self.memories = [item for item in self.memories if item["id"] != memory_id]
        return {"id": memory_id, "isForgotten": True}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "The export contains one source and one current fact with an older version."


class MemoryTransparencyTests(unittest.TestCase):
    def agent(self, memory: FakeMemory) -> MemoryTransparencyAgent:
        return MemoryTransparencyAgent(
            memory,
            FakeLLM(),
            container_tag="user:one",
            subject="subject-one",
            signing_key=b"secret",
            authorization_ledger=TestingAuthorizationLedger(trust_first_use=True),
        )

    def test_export_contains_sources_current_memory_and_history(self) -> None:
        export = self.agent(FakeMemory()).build_export()

        self.assertEqual(export.documents[0].chunk_count, 1)
        self.assertEqual(export.memories[0].version, 2)
        self.assertEqual(export.memories[0].history[0].version, 1)
        self.assertEqual(export.profile_counts["static"], 1)

    def test_forged_export_is_rejected(self) -> None:
        agent = self.agent(FakeMemory())
        export = agent.build_export()
        forged = export.__class__(
            export.container_tag,
            "another-subject",
            export.documents,
            export.memories,
            export.profile_counts,
            export.inventory_hash,
            export.signature,
        )

        self.assertFalse(agent.verify_export(forged))
        with self.assertRaises(PermissionError):
            agent.prepare_erasure(forged, memory_ids=["m2"])

    def test_plan_rejects_unknown_or_empty_ids(self) -> None:
        agent = self.agent(FakeMemory())
        export = agent.build_export()

        with self.assertRaises(ValueError):
            agent.prepare_erasure(export)
        with self.assertRaises(PermissionError):
            agent.prepare_erasure(export, memory_ids=["other"])

    def test_exact_authorization_erases_once_and_audits(self) -> None:
        memory = FakeMemory()
        agent = self.agent(memory)
        export = agent.build_export()
        plan = agent.prepare_erasure(export, document_ids=["d1"], memory_ids=["m2"])

        with self.assertRaises(PermissionError):
            agent.apply_erasure(
                plan, ErasureAuthorization("wrong", plan.inventory_hash, "owner")
            )
        result = agent.apply_erasure(
            plan,
            ErasureAuthorization(plan.plan_hash, plan.inventory_hash, "owner"),
        )

        self.assertEqual(memory.deleted, ["d1"])
        self.assertEqual(memory.forgotten, ["m2"])
        self.assertEqual(result["auditEvent"]["event"], "memory-erasure-applied")
        with self.assertRaises(RuntimeError):
            agent.apply_erasure(
                plan,
                ErasureAuthorization(plan.plan_hash, plan.inventory_hash, "owner"),
            )

    def test_inventory_drift_denies_old_plan(self) -> None:
        memory = FakeMemory()
        agent = self.agent(memory)
        export = agent.build_export()
        plan = agent.prepare_erasure(export, memory_ids=["m2"])
        memory.memories.append({"id": "m3", "memory": "New fact", "version": 1})

        with self.assertRaises(RuntimeError):
            agent.apply_erasure(
                plan,
                ErasureAuthorization(plan.plan_hash, plan.inventory_hash, "owner"),
            )


if __name__ == "__main__":
    unittest.main()
