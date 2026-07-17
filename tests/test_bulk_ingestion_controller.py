from dataclasses import replace
from datetime import datetime, timezone
import unittest

from supermemory_lab.bulk_ingestion_controller import (
    AdaptiveBulkIngestionController,
    IngestionRecord,
)
from supermemory_lab.http import ApiError


class FakeMemory:
    def __init__(self) -> None:
        self.documents = []
        self.batch_sizes = []
        self.throttle_once = False
        self.partial = False
        self.timeout_after_store = False
        self.timeout_partial_count = None

    def add_documents_batch(self, documents, **kwargs):
        self.batch_sizes.append(len(documents))
        if self.throttle_once:
            self.throttle_once = False
            raise ApiError("POST", "/v3/documents/batch", 429, "slow", "3")
        results = []
        stored_documents = documents
        if self.timeout_partial_count is not None:
            stored_documents = documents[: self.timeout_partial_count]
        for source in stored_documents:
            existing = next(
                (item for item in self.documents if item["customId"] == source["customId"]),
                None,
            )
            stored = {
                "id": existing["id"] if existing else f"doc-{len(self.documents) + 1}",
                "customId": source["customId"],
                "metadata": source["metadata"],
                "status": "done",
            }
            if existing:
                self.documents[self.documents.index(existing)] = stored
            else:
                self.documents.append(stored)
            results.append({"id": stored["id"], "status": "queued"})
        if self.timeout_after_store:
            self.timeout_after_store = False
            raise ApiError("POST", "/v3/documents/batch", None, "request timed out")
        if self.partial:
            results = results[:-1]
        return {"results": results, "success": len(results), "failed": 0}

    def list_documents(self, **kwargs):
        limit = kwargs.get("limit", 100)
        page = kwargs.get("page", 1)
        start = (page - 1) * limit
        end = start + limit
        total_pages = max(1, (len(self.documents) + limit - 1) // limit)
        return {
            "memories": self.documents[start:end],
            "pagination": {"totalPages": total_pages},
        }

    def get_processing_documents(self, **kwargs):
        return {"documents": [], "totalCount": 0}


def records(count=5):
    return [
        IngestionRecord(f"source-{index}", f"Content {index}", {"index": index})
        for index in range(count)
    ]


class BulkIngestionControllerTests(unittest.TestCase):
    def controller(self, memory, **kwargs):
        return AdaptiveBulkIngestionController(
            memory,
            container_tag="tenant:one",
            run_id="run-one",
            signing_key=b"0123456789abcdef0123456789abcdef",
            initial_batch_size=4,
            maximum_batch_size=6,
            **kwargs,
        )

    def test_throttle_honors_retry_after_and_adapts_batch_size(self):
        memory = FakeMemory()
        memory.throttle_once = True
        sleeps = []
        controller = self.controller(memory, sleep=sleeps.append)
        manifest = controller.build_manifest(records())

        checkpoint = controller.submit(manifest)

        self.assertEqual(sleeps, [3.0])
        self.assertEqual(memory.batch_sizes, [4, 2, 3])
        self.assertEqual(checkpoint.throttle_events, 1)
        self.assertEqual(checkpoint.request_attempts, 3)
        self.assertTrue(checkpoint.complete)
        self.assertTrue(controller.verify_checkpoint(manifest, checkpoint))

    def test_signed_checkpoint_resumes_only_pending_records(self):
        memory = FakeMemory()
        saved = []
        first = self.controller(memory, checkpoint_sink=saved.append)
        manifest = first.build_manifest(records())
        checkpoint = first.submit(manifest, max_accepted_batches=1)
        self.assertFalse(checkpoint.complete)
        first_ids = {item["customId"] for item in memory.documents}

        fresh = self.controller(memory)
        completed = fresh.submit(manifest, checkpoint=checkpoint)

        self.assertTrue(completed.complete)
        self.assertEqual(len(memory.documents), 5)
        self.assertTrue(first_ids <= {item["customId"] for item in memory.documents})
        self.assertTrue(fresh.reconcile(manifest).semantically_ready)

    def test_tampered_manifest_or_checkpoint_is_denied(self):
        controller = self.controller(FakeMemory())
        manifest = controller.build_manifest(records())
        checkpoint = controller.submit(manifest, max_accepted_batches=1)
        with self.assertRaises(PermissionError):
            controller.submit(replace(manifest, manifest_hash="wrong"))
        with self.assertRaises(PermissionError):
            controller.submit(manifest, checkpoint=replace(checkpoint, next_batch_size=6))

    def test_partial_acknowledgement_never_advances_checkpoint(self):
        memory = FakeMemory()
        memory.partial = True
        saved = []
        controller = self.controller(memory, checkpoint_sink=saved.append)
        manifest = controller.build_manifest(records())
        with self.assertRaises(RuntimeError):
            controller.submit(manifest)
        self.assertEqual(saved, [])

    def test_reconciliation_detects_hash_mismatch_and_processing(self):
        memory = FakeMemory()
        controller = self.controller(memory)
        manifest = controller.build_manifest(records(2))
        controller.submit(manifest)
        memory.documents[0]["metadata"]["sourceHash"] = "wrong"
        memory.documents[1]["status"] = "extracting"

        report = controller.reconcile(manifest)

        self.assertFalse(report.exact_inventory)
        self.assertFalse(report.semantically_ready)
        self.assertEqual(report.processing_count, 1)
        self.assertEqual(report.hash_mismatch_custom_ids, ("source-0",))

    def test_http_date_retry_after_is_bounded_and_parsed(self):
        memory = FakeMemory()
        controller = self.controller(
            memory, now=lambda: datetime(2026, 7, 17, tzinfo=timezone.utc)
        )
        self.assertEqual(
            controller._retry_seconds("Fri, 17 Jul 2026 00:00:10 GMT"), 10.0
        )

    def test_reconciliation_paginates_large_inventory(self):
        memory = FakeMemory()
        controller = self.controller(memory)
        manifest = controller.build_manifest(records(205))
        controller.submit(manifest)
        report = controller.reconcile(manifest)
        self.assertEqual(report.imported_count, 205)
        self.assertTrue(report.semantically_ready)

    def test_lost_acknowledgement_recovers_exact_batch_without_retry(self):
        memory = FakeMemory()
        memory.timeout_after_store = True
        saved = []
        controller = self.controller(memory, checkpoint_sink=saved.append)
        manifest = controller.build_manifest(records())

        checkpoint = controller.submit(manifest)

        self.assertTrue(checkpoint.complete)
        self.assertEqual(memory.batch_sizes, [4, 1])
        self.assertEqual(len(memory.documents), 5)
        self.assertEqual(checkpoint.request_attempts, 2)
        self.assertEqual(len(saved), 2)

    def test_partial_ambiguous_write_never_advances_checkpoint(self):
        memory = FakeMemory()
        memory.timeout_after_store = True
        memory.timeout_partial_count = 2
        saved = []
        controller = self.controller(
            memory,
            checkpoint_sink=saved.append,
            ambiguous_recovery_attempts=2,
            sleep=lambda _: None,
        )
        manifest = controller.build_manifest(records())

        with self.assertRaisesRegex(RuntimeError, "ambiguous batch write"):
            controller.submit(manifest)

        self.assertEqual(saved, [])
        self.assertEqual(memory.batch_sizes, [4])


if __name__ == "__main__":
    unittest.main()
