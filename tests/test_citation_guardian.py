import dataclasses
from datetime import datetime, timedelta, timezone
import unittest

from supermemory_lab.citation_guardian import (
    CitationAuthorization,
    SourceRevisionCitationGuardian,
)


V1 = "Policy REVISION=V1. CURRENT_WINDOW=02:00-03:00 UTC. One owner approves."
V2 = "Policy REVISION=V2. CURRENT_WINDOW=04:00-05:00 UTC. Two owners approve."


class FakeMemory:
    def __init__(self) -> None:
        self.content = V1
        self.created = []

    def get_document_chunks(self, document_id):
        return {"chunks": [{"id": "chunk-1", "position": 0, "content": self.content}]}

    def create_memories(self, container_tag, memories):
        self.created.extend(memories)
        return {"memories": [{"id": "answer-1"}]}


class FakeLLM:
    def __init__(self, answers):
        self.answers = list(answers)

    def complete(self, system_prompt, user_prompt):
        return self.answers.pop(0)


def answer(revision="V1", window="02:00-03:00", quote=V1, chunk="chunk-1"):
    return (
        '{"revisionId":"%s","answer":"CURRENT_WINDOW=%s UTC",'
        '"citations":[{"chunkId":"%s","quote":"%s"}]}'
        % (revision, window, chunk, quote)
    )


class CitationGuardianTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.memory = FakeMemory()

    def guardian(self, answers):
        return SourceRevisionCitationGuardian(
            self.memory,
            FakeLLM(answers),
            container_tag="policy",
            signing_key=b"0123456789abcdef0123456789abcdef",
        )

    def snapshot(self, guardian, revision="V1", required=("REVISION=V1",), forbidden=()):
        return guardian.issue_snapshot(
            document_id="doc-1",
            revision_id=revision,
            effective_at=self.now - timedelta(minutes=1),
            expires_at=self.now + timedelta(hours=1),
            required_source_terms=required,
            forbidden_source_terms=forbidden,
        )

    def test_exact_current_quote_is_signed_and_persisted_once(self):
        guardian = self.guardian([answer()])
        snapshot = self.snapshot(guardian)
        report = guardian.draft_answer(
            snapshot,
            question="What is the window?",
            now=self.now,
            required_answer_terms=("CURRENT_WINDOW=02:00-03:00 UTC",),
            forbidden_answer_terms=("REVISION=V2",),
        )
        self.assertTrue(guardian.verify_snapshot(snapshot, now=self.now))
        self.assertTrue(guardian.verify_answer(report))
        authorization = CitationAuthorization(
            snapshot.snapshot_hash, report.report_hash, "policy-owner"
        )
        guardian.persist(snapshot, report, authorization, now=self.now)
        self.assertEqual(len(self.memory.created), 1)
        with self.assertRaises(RuntimeError):
            guardian.persist(snapshot, report, authorization, now=self.now)

    def test_source_change_invalidates_old_snapshot_before_persist(self):
        guardian = self.guardian([answer()])
        snapshot = self.snapshot(guardian)
        report = guardian.draft_answer(
            snapshot,
            question="What is the window?",
            now=self.now,
            required_answer_terms=("CURRENT_WINDOW=02:00-03:00 UTC",),
        )
        self.memory.content = V2
        with self.assertRaises(RuntimeError):
            guardian.persist(
                snapshot,
                report,
                CitationAuthorization(
                    snapshot.snapshot_hash, report.report_hash, "policy-owner"
                ),
                now=self.now,
            )
        self.assertEqual(self.memory.created, [])

    def test_stale_source_term_blocks_new_snapshot(self):
        guardian = self.guardian([])
        with self.assertRaises(ValueError):
            self.snapshot(
                guardian,
                revision="V2",
                required=("REVISION=V2",),
                forbidden=("REVISION=V1",),
            )

    def test_unknown_or_inexact_citation_and_stale_answer_fail(self):
        invalid = [
            answer(quote="not an exact quote"),
            answer(chunk="unknown"),
            answer(window="04:00-05:00"),
            answer(revision="V2"),
        ]
        for value in invalid:
            with self.subTest(value=value):
                guardian = self.guardian([value])
                snapshot = self.snapshot(guardian)
                with self.assertRaises(ValueError):
                    guardian.draft_answer(
                        snapshot,
                        question="What is the window?",
                        now=self.now,
                        required_answer_terms=("CURRENT_WINDOW=02:00-03:00 UTC",),
                        forbidden_answer_terms=("04:00-05:00",),
                    )

    def test_wrong_authorization_tampering_and_expiry_fail_closed(self):
        guardian = self.guardian([answer()])
        snapshot = self.snapshot(guardian)
        report = guardian.draft_answer(
            snapshot,
            question="What is the window?",
            now=self.now,
            required_answer_terms=("CURRENT_WINDOW=02:00-03:00 UTC",),
        )
        with self.assertRaises(PermissionError):
            guardian.persist(
                snapshot,
                report,
                CitationAuthorization("wrong", report.report_hash, "owner"),
                now=self.now,
            )
        self.assertFalse(
            guardian.verify_answer(dataclasses.replace(report, answer="tampered"))
        )
        self.assertFalse(
            guardian.verify_snapshot(snapshot, now=self.now + timedelta(hours=2))
        )

    def test_json_repair_is_bounded(self):
        guardian = self.guardian(["not json", answer()])
        snapshot = self.snapshot(guardian)
        report = guardian.draft_answer(
            snapshot,
            question="What is the window?",
            now=self.now,
            required_answer_terms=("CURRENT_WINDOW=02:00-03:00 UTC",),
        )
        self.assertTrue(guardian.verify_answer(report))


if __name__ == "__main__":
    unittest.main()
