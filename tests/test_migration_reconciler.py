import unittest
from typing import Any, Dict, List, Mapping, Sequence

from supermemory_lab.authorization import TestingAuthorizationLedger

from supermemory_lab.migration_reconciler import (
    GovernedMigrationReconciler,
    MigrationRecord,
    RollbackAuthorization,
)


class FakeMemory:
    def __init__(self) -> None:
        self.documents: List[Mapping[str, Any]] = []
        self.checkpoints: List[Mapping[str, Any]] = []

    def add_documents_batch(
        self, documents: Sequence[Mapping[str, Any]], **kwargs: Any
    ) -> Dict[str, Any]:
        for document in documents:
            existing = next(
                (item for item in self.documents if item["customId"] == document["customId"]),
                None,
            )
            stored = {
                "id": existing["id"] if existing else f"d{len(self.documents) + 1}",
                "customId": document["customId"],
                "metadata": document["metadata"],
            }
            if existing:
                self.documents[self.documents.index(existing)] = stored
            else:
                self.documents.append(stored)
        return {
            "results": [{"id": item["id"], "status": "queued"} for item in self.documents],
            "success": len(documents),
            "failed": 0,
        }

    def list_documents(self, **kwargs: Any) -> Dict[str, Any]:
        return {"memories": self.documents}

    def bulk_delete_documents(self, document_ids: Sequence[str]) -> Dict[str, Any]:
        self.documents = [item for item in self.documents if item["id"] not in document_ids]
        return {"success": True, "deleted": len(document_ids)}

    def create_memories(
        self, container_tag: str, memories: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.checkpoints.extend(memories)
        return {"memories": [{"id": "checkpoint"}]}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": self.checkpoints}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "Two records reconciled exactly; rollback still requires approval."


def records() -> List[MigrationRecord]:
    return [
        MigrationRecord("source-1", "First record", {"kind": "note"}),
        MigrationRecord("source-2", "Second record", {"kind": "note"}),
    ]


class MigrationReconcilerTests(unittest.TestCase):
    def agent(self, memory: FakeMemory) -> GovernedMigrationReconciler:
        return GovernedMigrationReconciler(
            memory,
            FakeLLM(),
            target_container="target",
            control_container="control",
            migration_id="migration-one",
            signing_key=b"0123456789abcdef",
            authorization_ledger=TestingAuthorizationLedger(trust_first_use=True),
        )

    def test_manifest_rejects_duplicate_or_empty_source_ids(self) -> None:
        agent = self.agent(FakeMemory())
        with self.assertRaises(ValueError):
            agent.build_manifest([])
        with self.assertRaises(ValueError):
            agent.build_manifest(
                [MigrationRecord("same", "one", {}), MigrationRecord("same", "two", {})]
            )

    def test_import_is_idempotent_by_custom_id_and_reconciles(self) -> None:
        memory = FakeMemory()
        agent = self.agent(memory)
        manifest = agent.build_manifest(records())
        agent.import_manifest(manifest)
        agent.import_manifest(manifest)
        report = agent.reconcile(manifest)

        self.assertEqual(len(memory.documents), 2)
        self.assertTrue(report.exact)
        self.assertEqual(report.imported_count, 2)

    def test_fresh_process_verifies_checkpoint(self) -> None:
        memory = FakeMemory()
        agent = self.agent(memory)
        manifest = agent.build_manifest(records())
        checkpoint = agent.import_manifest(manifest)

        loaded = self.agent(memory).load_checkpoint()
        self.assertEqual(loaded.manifest_hash, manifest.manifest_hash)
        self.assertTrue(agent.verify_checkpoint(checkpoint))

    def test_hash_mismatch_blocks_rollback(self) -> None:
        memory = FakeMemory()
        agent = self.agent(memory)
        manifest = agent.build_manifest(records())
        agent.import_manifest(manifest)
        memory.documents[0]["metadata"]["sourceHash"] = "wrong"  # type: ignore[index]
        report = agent.reconcile(manifest)

        self.assertFalse(report.exact)
        with self.assertRaises(PermissionError):
            agent.prepare_rollback(report)

    def test_exact_rollback_requires_authorization_and_denies_replay(self) -> None:
        memory = FakeMemory()
        agent = self.agent(memory)
        manifest = agent.build_manifest(records())
        agent.import_manifest(manifest)
        plan = agent.prepare_rollback(agent.reconcile(manifest))
        with self.assertRaises(PermissionError):
            agent.apply_rollback(
                manifest,
                plan,
                RollbackAuthorization("wrong", plan.manifest_hash, "owner"),
            )
        result = agent.apply_rollback(
            manifest,
            plan,
            RollbackAuthorization(plan.plan_hash, plan.manifest_hash, "owner"),
        )
        self.assertEqual(result["auditEvent"]["documentIds"], list(plan.document_ids))
        self.assertEqual(memory.documents, [])
        with self.assertRaises(RuntimeError):
            agent.apply_rollback(
                manifest,
                plan,
                RollbackAuthorization(plan.plan_hash, plan.manifest_hash, "owner"),
            )


if __name__ == "__main__":
    unittest.main()
