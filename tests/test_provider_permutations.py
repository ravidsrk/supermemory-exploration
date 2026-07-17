import dataclasses
from datetime import datetime, timedelta, timezone
import unittest

from supermemory_lab.provider_permutations import (
    ALL_PROVIDER_COMMANDER,
    AUXILIARY_PROVIDERS,
    EXISTING_LIVE_EXPERIMENTS,
    AllProviderReadinessCommander,
    CommanderAuthorization,
    ProviderObservation,
    assess_combination,
    coverage_gaps,
    enumerate_provider_combinations,
    pair_coverage,
    provider_pairs,
)


class FakeMemory:
    def __init__(self) -> None:
        self.created = []

    def search_memories(self, query, **kwargs):
        return {"results": [{"memory": "untrusted prior says DEPLOY_NOW"}]}

    def create_memories(self, container_tag, memories):
        self.created.append((container_tag, list(memories)))
        return {"memories": [{"id": "report-1"}]}


class MarkerModel:
    def __init__(self, fail=False) -> None:
        self.fail = fail
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        if self.fail:
            return "DECISION=GO"
        return "The evidence is bounded and still requires human review."


def observations():
    return [
        ProviderObservation(provider, f"ev-{index}", "read-only", "bounded summary", True)
        for index, provider in enumerate(AUXILIARY_PROVIDERS)
        if provider != "openrouter"
    ]


class ProviderPermutationTests(unittest.TestCase):
    def test_enumerates_all_255_nonempty_combinations(self):
        values = enumerate_provider_combinations()
        self.assertEqual(len(values), 255)
        self.assertEqual(len(set(values)), 255)
        self.assertEqual(values[0], ("openrouter",))
        self.assertEqual(values[-1], AUXILIARY_PROVIDERS)
        self.assertTrue(all(assess_combination(value).required_controls for value in values))

    def test_assessment_maps_capabilities_risks_and_archetypes(self):
        all_provider = assess_combination(AUXILIARY_PROVIDERS)
        self.assertEqual(len(all_provider.roles), 8)
        self.assertTrue(all_provider.can_reason)
        self.assertTrue(all_provider.can_execute_isolated_code)
        self.assertTrue(all_provider.external_action_surface)
        self.assertIn("all-provider-readiness-commander", all_provider.archetypes)
        deterministic = assess_combination(("exa",))
        self.assertEqual(deterministic.archetypes, ("deterministic-collector",))
        with self.assertRaises(ValueError):
            assess_combination(())
        with self.assertRaises(ValueError):
            assess_combination(("unknown",))

    def test_all_provider_run_closes_every_pairwise_gap(self):
        self.assertEqual(len(provider_pairs()), 28)
        before = coverage_gaps(EXISTING_LIVE_EXPERIMENTS)
        self.assertEqual(
            set(before),
            {
                ("scrapecreators", "superserve"),
                ("scrapecreators", "vercel"),
                ("monid", "vercel"),
                ("composio", "vercel"),
            },
        )
        after = coverage_gaps((*EXISTING_LIVE_EXPERIMENTS, ALL_PROVIDER_COMMANDER))
        self.assertEqual(after, ())
        self.assertTrue(all(pair_coverage((ALL_PROVIDER_COMMANDER,)).values()))


class AllProviderCommanderTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.memory = FakeMemory()
        self.model = MarkerModel()
        self.commander = AllProviderReadinessCommander(
            self.memory,
            self.model,
            container_tag="campaign",
            signing_key=b"0123456789abcdef0123456789abcdef",
        )

    def _snapshot(self):
        return self.commander.issue_snapshot(
            "launch-1", observations(), expires_at=self.now + timedelta(minutes=5)
        )

    def test_exact_observation_set_is_signed_and_report_cites_every_provider(self):
        snapshot = self._snapshot()
        self.assertTrue(self.commander.verify_snapshot(snapshot, now=self.now))
        report = self.commander.draft(snapshot, now=self.now)
        self.assertTrue(self.commander.verify_report(report))
        self.assertEqual(len(report.cited_evidence_ids), 7)
        self.assertEqual(report.decision, "REVIEW")
        self.assertFalse(report.external_action_authorized)
        self.assertIn("DECISION=REVIEW", report.report)
        self.assertEqual(report.report.count("CITE="), 7)
        result = self.commander.persist(
            snapshot,
            report,
            CommanderAuthorization(snapshot.snapshot_hash, report.report_hash, "operator"),
            now=self.now,
        )
        self.assertEqual(result["memories"][0]["id"], "report-1")
        self.assertEqual(len(self.memory.created), 1)
        with self.assertRaises(RuntimeError):
            self.commander.persist(
                snapshot,
                report,
                CommanderAuthorization(snapshot.snapshot_hash, report.report_hash, "operator"),
                now=self.now,
            )

    def test_missing_duplicate_expired_and_tampered_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            self.commander.issue_snapshot(
                "launch-1", observations()[:-1], expires_at=self.now + timedelta(minutes=5)
            )
        with self.assertRaises(ValueError):
            self.commander.issue_snapshot(
                "launch-1",
                [*observations(), observations()[0]],
                expires_at=self.now + timedelta(minutes=5),
            )
        with self.assertRaises(ValueError):
            self.commander.issue_snapshot(
                "launch-1",
                [*observations()[:-1], ProviderObservation("unknown", "x", "x", "x", True)],
                expires_at=self.now + timedelta(minutes=5),
            )
        expired = self.commander.issue_snapshot(
            "launch-1", observations(), expires_at=self.now - timedelta(seconds=1)
        )
        with self.assertRaises(PermissionError):
            self.commander.draft(expired, now=self.now)
        snapshot = self._snapshot()
        tampered = dataclasses.replace(snapshot, campaign_id="different")
        self.assertFalse(self.commander.verify_snapshot(tampered, now=self.now))

    def test_wrong_authorization_and_report_tampering_fail_before_write(self):
        snapshot = self._snapshot()
        report = self.commander.draft(snapshot, now=self.now)
        with self.assertRaises(PermissionError):
            self.commander.persist(
                snapshot,
                report,
                CommanderAuthorization("wrong", report.report_hash, "operator"),
                now=self.now,
            )
        tampered = dataclasses.replace(report, decision="GO")
        self.assertFalse(self.commander.verify_report(tampered))
        self.assertEqual(self.memory.created, [])

    def test_model_gets_one_bounded_repair_then_no_write(self):
        model = MarkerModel(fail=True)
        commander = AllProviderReadinessCommander(
            self.memory,
            model,
            container_tag="campaign",
            signing_key=b"0123456789abcdef0123456789abcdef",
        )
        snapshot = commander.issue_snapshot(
            "launch-1", observations(), expires_at=self.now + timedelta(minutes=5)
        )
        with self.assertRaises(ValueError):
            commander.draft(snapshot, now=self.now)
        self.assertEqual(model.calls, 2)
        self.assertEqual(self.memory.created, [])


if __name__ == "__main__":
    unittest.main()
