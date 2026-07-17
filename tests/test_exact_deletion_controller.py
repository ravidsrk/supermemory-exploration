from dataclasses import replace
import unittest

from supermemory_lab.exact_deletion_controller import (
    DeletionAuthorization,
    ExactDeletionController,
)


class FakeMemory:
    def __init__(self):
        self.calls = []
        self.fail_partial = False

    def bulk_delete_documents(self, document_ids):
        self.calls.append(list(document_ids))
        deleted = len(document_ids) - (1 if self.fail_partial else 0)
        return {
            "success": not self.fail_partial,
            "deletedCount": deleted,
            "errors": [] if not self.fail_partial else [{"id": document_ids[-1]}],
        }


class ExactDeletionControllerTests(unittest.TestCase):
    def controller(self, memory, **kwargs):
        return ExactDeletionController(
            memory,
            signing_key=b"0123456789abcdef0123456789abcdef",
            **kwargs,
        )

    def plan(self, controller, count=250):
        return controller.build_plan(
            container_tag="tenant:one",
            source_manifest_hash="manifest-hash",
            document_ids=[f"doc-{index:04d}" for index in range(count)],
        )

    def test_chunks_at_exact_hundred_and_completes(self):
        memory = FakeMemory()
        controller = self.controller(memory)
        plan = self.plan(controller)
        checkpoint = controller.apply(
            plan,
            DeletionAuthorization(plan.plan_hash, plan.source_manifest_hash, "owner"),
        )
        self.assertEqual([len(call) for call in memory.calls], [100, 100, 50])
        self.assertTrue(checkpoint.complete)
        self.assertTrue(controller.verify_checkpoint(plan, checkpoint))

    def test_fresh_process_resumes_signed_checkpoint(self):
        memory = FakeMemory()
        saved = []
        first = self.controller(memory, checkpoint_sink=saved.append)
        plan = self.plan(first)
        paused = first.apply(
            plan,
            DeletionAuthorization(plan.plan_hash, plan.source_manifest_hash, "owner"),
            max_batches=1,
        )
        completed = self.controller(memory).apply(
            plan,
            DeletionAuthorization(plan.plan_hash, plan.source_manifest_hash, "owner"),
            checkpoint=paused,
        )
        self.assertTrue(completed.complete)
        self.assertEqual([len(call) for call in memory.calls], [100, 100, 50])

    def test_completed_checkpoint_is_idempotent(self):
        memory = FakeMemory()
        controller = self.controller(memory)
        plan = self.plan(controller, 2)
        authorization = DeletionAuthorization(
            plan.plan_hash, plan.source_manifest_hash, "owner"
        )
        completed = controller.apply(plan, authorization)
        calls = len(memory.calls)
        same = self.controller(memory).apply(
            plan, authorization, checkpoint=completed
        )
        self.assertEqual(same, completed)
        self.assertEqual(len(memory.calls), calls)

    def test_wrong_authorization_tamper_duplicate_and_partial_fail(self):
        memory = FakeMemory()
        controller = self.controller(memory)
        plan = self.plan(controller, 2)
        with self.assertRaises(PermissionError):
            controller.apply(
                plan, DeletionAuthorization("wrong", plan.source_manifest_hash, "owner")
            )
        with self.assertRaises(PermissionError):
            controller.apply(
                replace(plan, document_ids=("other",)),
                DeletionAuthorization(plan.plan_hash, plan.source_manifest_hash, "owner"),
            )
        with self.assertRaises(ValueError):
            controller.build_plan(
                container_tag="tenant",
                source_manifest_hash="hash",
                document_ids=["same", "same"],
            )
        memory.fail_partial = True
        with self.assertRaises(RuntimeError):
            controller.apply(
                plan,
                DeletionAuthorization(plan.plan_hash, plan.source_manifest_hash, "owner"),
            )


if __name__ == "__main__":
    unittest.main()
