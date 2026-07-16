import unittest
from typing import Any, Dict, List, Mapping, Sequence

from supermemory_lab.contract_drift import (
    ContractDriftSentinel,
    IssueSignal,
    compare_snapshots,
    snapshot_from_openapi,
)


def spec(*, required: bool = False, extra: bool = False) -> Mapping[str, Any]:
    paths: Dict[str, Any] = {
        "/v4/search": {
            "post": {
                "operationId": "search",
                "requestBody": {"required": required, "content": {}},
            }
        }
    }
    if extra:
        paths["/v4/profile"] = {"post": {"operationId": "profile"}}
    return {"paths": paths}


class FakeMemory:
    def __init__(self) -> None:
        self.writes: List[Mapping[str, Any]] = []
        self.search_results: List[Mapping[str, Any]] = []

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.writes.append({"content": content, **kwargs})
        return {"id": "doc"}

    def create_memories(
        self, container_tag: str, memories: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.writes.extend(memories)
        self.search_results.extend(memories)
        return {"memories": [{"id": "memory"}]}

    def search_memories(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": self.search_results}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "Reported wrapper failures require outage and deduplication contract tests."


class ContractDriftTests(unittest.TestCase):
    def sentinel(self, memory: FakeMemory) -> ContractDriftSentinel:
        return ContractDriftSentinel(
            memory,
            FakeLLM(),
            container_tag="contracts:one",
            sentinel_id="sentinel-one",
            signing_key=b"0123456789abcdef",
        )

    def test_snapshot_diff_detects_added_removed_and_request_changes(self) -> None:
        baseline = snapshot_from_openapi(
            spec(required=False, extra=True),
            captured_at="one",
            source_commit="a",
        )
        current = snapshot_from_openapi(
            spec(required=True), captured_at="two", source_commit="b"
        )
        diff = compare_snapshots(baseline, current)

        self.assertEqual(diff.removed, ("POST /v4/profile",))
        self.assertEqual(diff.request_changed, ("POST /v4/search",))

    def test_request_change_blocks_upgrade(self) -> None:
        baseline = snapshot_from_openapi(
            spec(required=False), captured_at="one", source_commit="a"
        )
        current = snapshot_from_openapi(
            spec(required=True), captured_at="two", source_commit="b"
        )
        advice = self.sentinel(FakeMemory()).assess(
            baseline, current, evidence_ids=["E1"]
        )

        self.assertEqual(advice.recommendation, "BLOCK-UPGRADE")
        self.assertFalse(advice.action_authorized)

    def test_critical_issue_holds_even_without_schema_drift(self) -> None:
        issue = IssueSignal("1287", "Middleware crashes when API is unreachable", "url")
        baseline = snapshot_from_openapi(
            spec(), captured_at="one", source_commit="a", issues=[issue]
        )
        current = snapshot_from_openapi(
            spec(), captured_at="two", source_commit="a", issues=[issue]
        )
        advice = self.sentinel(FakeMemory()).assess(baseline, current, evidence_ids=[])

        self.assertEqual(advice.recommendation, "HOLD-FOR-CONTRACT-TESTS")
        self.assertIn("1287", advice.reasons[0])

    def test_signed_advice_round_trips_and_becomes_stale(self) -> None:
        memory = FakeMemory()
        sentinel = self.sentinel(memory)
        baseline = snapshot_from_openapi(spec(), captured_at="one", source_commit="a")
        current = snapshot_from_openapi(spec(), captured_at="two", source_commit="a")
        advice = sentinel.assess(baseline, current, evidence_ids=["E1", "E1"])
        sentinel.persist(baseline, current, advice)

        status, loaded = sentinel.load(current)
        self.assertEqual(status, "current-advice")
        self.assertTrue(sentinel.verify(loaded))
        changed = snapshot_from_openapi(
            spec(extra=True), captured_at="three", source_commit="b"
        )
        self.assertEqual(sentinel.load(changed)[0], "stale-contract-evidence")

    def test_tampered_advice_is_rejected(self) -> None:
        sentinel = self.sentinel(FakeMemory())
        snapshot = snapshot_from_openapi(spec(), captured_at="one", source_commit="a")
        advice = sentinel.assess(snapshot, snapshot, evidence_ids=[])
        tampered = advice.__class__(
            advice.advice_id,
            advice.baseline_digest,
            advice.current_digest,
            "UPGRADE-NOW",
            advice.reasons,
            advice.evidence_ids,
            advice.explanation,
            True,
            advice.signature,
        )

        self.assertFalse(sentinel.verify(tampered))


if __name__ == "__main__":
    unittest.main()
