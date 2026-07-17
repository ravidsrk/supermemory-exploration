import dataclasses
import unittest

from supermemory_lab.profile_schema_steward import (
    BucketEvolutionAuthorization,
    GovernedProfileSchemaSteward,
)


class FakeMemory:
    def __init__(self) -> None:
        self.own = [{"key": "existing", "description": "Existing bucket"}]
        self.org = [{"key": "org-policy", "description": "Organization policy"}]
        self.update_calls = []

    def get_container_settings(self, container_tag):
        return {"containerTag": container_tag, "profileBuckets": list(self.own)}

    def list_profile_buckets(self, container_tag):
        return {"buckets": [*self.org, *self.own]}

    def update_container_settings(self, container_tag, **kwargs):
        self.update_calls.append((container_tag, kwargs))
        self.own = list(kwargs["profile_buckets"])
        return {"containerTag": container_tag, "profileBuckets": list(self.own)}


class ProfileSchemaStewardTests(unittest.TestCase):
    def setUp(self):
        self.memory = FakeMemory()
        self.steward = GovernedProfileSchemaSteward(
            self.memory,
            container_tag="tenant:one",
            signing_key=b"0123456789abcdef0123456789abcdef",
        )

    def test_validates_bounded_suggestions(self):
        values = self.steward.validate_suggestions(
            {
                "suggestions": [
                    {"key": "goals", "description": "Current explicit goals"},
                    {"key": "work-style", "description": "Explicit work style"},
                ]
            }
        )
        self.assertEqual([value.key for value in values], ["goals", "work-style"])
        with self.assertRaises(ValueError):
            self.steward.validate_suggestions({"suggestions": []})

    def test_additive_exact_plan_preserves_existing_and_applies_once(self):
        snapshot = self.steward.capture()
        plan = self.steward.propose(
            snapshot, [{"key": "escalations", "description": "Escalation contracts"}]
        )
        self.assertTrue(self.steward.verify_snapshot(snapshot))
        self.assertTrue(self.steward.verify_plan(plan))
        authorization = BucketEvolutionAuthorization(
            snapshot.snapshot_hash, plan.plan_hash, "schema-owner"
        )
        self.steward.apply(snapshot, plan, authorization)
        self.assertEqual({item["key"] for item in self.memory.own}, {"existing", "escalations"})
        with self.assertRaises(RuntimeError):
            self.steward.apply(snapshot, plan, authorization)

    def test_effective_collision_and_invalid_keys_fail(self):
        snapshot = self.steward.capture()
        with self.assertRaises(ValueError):
            self.steward.propose(
                snapshot, [{"key": "org-policy", "description": "collision"}]
            )
        with self.assertRaises(ValueError):
            self.steward.propose(
                snapshot, [{"key": "INVALID KEY", "description": "bad"}]
            )

    def test_wrong_authorization_and_schema_drift_fail_before_update(self):
        snapshot = self.steward.capture()
        plan = self.steward.propose(
            snapshot, [{"key": "goals", "description": "Explicit goals"}]
        )
        with self.assertRaises(PermissionError):
            self.steward.apply(
                snapshot,
                plan,
                BucketEvolutionAuthorization("wrong", plan.plan_hash, "owner"),
            )
        self.memory.own.append({"key": "drift", "description": "Concurrent change"})
        with self.assertRaises(RuntimeError):
            self.steward.apply(
                snapshot,
                plan,
                BucketEvolutionAuthorization(
                    snapshot.snapshot_hash, plan.plan_hash, "owner"
                ),
            )
        self.assertEqual(self.memory.update_calls, [])

    def test_tampered_plan_and_existing_mutation_fail(self):
        snapshot = self.steward.capture()
        plan = self.steward.propose(
            snapshot, [{"key": "goals", "description": "Explicit goals"}]
        )
        tampered = dataclasses.replace(
            plan,
            resulting_own_buckets=(
                dataclasses.replace(snapshot.own_buckets[0], description="mutated"),
                *plan.additions,
            ),
        )
        self.assertFalse(self.steward.verify_plan(tampered))


if __name__ == "__main__":
    unittest.main()
