from dataclasses import replace
import unittest

from supermemory_lab.authorization import TestingAuthorizationLedger

from supermemory_lab.connector_onboarding_governor import (
    ConnectorAuthorization,
    GovernedConnectorOnboarding,
    ResourceAuthorization,
)


class FakeMemory:
    def __init__(self):
        self.resources = [
            {
                "id": 2,
                "name": "org/private",
                "full_name": "org/private",
                "default_branch": "main",
                "private": True,
            },
            {
                "id": 1,
                "name": "org/docs",
                "full_name": "org/docs",
                "default_branch": "main",
                "private": False,
            },
        ]
        self.configured = []
        self.deleted = []

    def create_connection(self, provider, **kwargs):
        return {"id": "connection-1", "authLink": "https://oauth.example/secret"}

    def get_connection(self, connection_id):
        return {"id": connection_id, "provider": "github"}

    def fetch_connection_resources(self, connection_id, **kwargs):
        return {"resources": self.resources, "total_count": len(self.resources)}

    def configure_connection_resources(self, connection_id, resources):
        self.configured.append((connection_id, list(resources)))
        return {"success": True, "message": "configured", "webhooksRegistered": 1}

    def delete_connection(self, connection_id, *, delete_documents=True):
        self.deleted.append((connection_id, delete_documents))
        return {"id": connection_id, "provider": "github"}


class ConnectorOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.memory = FakeMemory()
        self.agent = GovernedConnectorOnboarding(
            self.memory,
            signing_key=b"0123456789abcdef0123456789abcdef",
            authorization_ledger=TestingAuthorizationLedger(trust_first_use=True),
        )
        self.intent = self.agent.issue_intent(
            provider="github",
            container_tags=("tenant:one",),
            redirect_url="https://app.example/callback",
            document_limit=20,
            metadata={"purpose": "docs"},
        )
        self.authorization = ConnectorAuthorization(self.intent.intent_hash, "owner")

    def test_oauth_link_is_hashed_and_never_retained(self):
        pending = self.agent.begin(self.intent, self.authorization)
        self.assertTrue(pending.auth_required)
        self.assertEqual(len(pending.auth_link_hash), 64)
        self.assertNotIn("oauth.example", str(pending))
        self.assertTrue(self.agent.verify_pending(pending))

    def test_exact_resource_selection_applies_once(self):
        pending = self.agent.begin(self.intent, self.authorization)
        snapshot = self.agent.capture_resources(pending)
        plan = self.agent.plan(snapshot, ["1"])
        response = self.agent.apply(
            pending,
            snapshot,
            plan,
            ResourceAuthorization(plan.plan_hash, snapshot.resource_digest, "owner"),
        )
        self.assertTrue(response["success"])
        self.assertEqual(self.memory.configured[0][1][0]["id"], 1)
        with self.assertRaises(RuntimeError):
            self.agent.apply(
                pending,
                snapshot,
                plan,
                ResourceAuthorization(plan.plan_hash, snapshot.resource_digest, "owner"),
            )

    def test_unknown_selection_wrong_authorization_and_drift_fail(self):
        pending = self.agent.begin(self.intent, self.authorization)
        snapshot = self.agent.capture_resources(pending)
        with self.assertRaises(PermissionError):
            self.agent.plan(snapshot, ["999"])
        plan = self.agent.plan(snapshot, ["1"])
        with self.assertRaises(PermissionError):
            self.agent.apply(
                pending,
                snapshot,
                plan,
                ResourceAuthorization("wrong", snapshot.resource_digest, "owner"),
            )
        self.memory.resources.append({"id": 3, "name": "org/new"})
        with self.assertRaises(RuntimeError):
            self.agent.apply(
                pending,
                snapshot,
                plan,
                ResourceAuthorization(plan.plan_hash, snapshot.resource_digest, "owner"),
            )

    def test_non_github_resource_selection_and_forgery_are_denied(self):
        pending = self.agent.begin(self.intent, self.authorization)
        with self.assertRaises(PermissionError):
            self.agent.capture_resources(replace(pending, provider="notion"))
        with self.assertRaises(PermissionError):
            self.agent.begin(
                replace(self.intent, document_limit=10), self.authorization
            )

    def test_disconnect_preserves_documents_by_default(self):
        pending = self.agent.begin(self.intent, self.authorization)
        self.agent.disconnect_preserving_documents(pending, self.authorization)
        self.assertEqual(self.memory.deleted, [("connection-1", False)])

    def test_intent_validates_provider_scope_limit_and_redirect(self):
        with self.assertRaises(ValueError):
            self.agent.issue_intent(
                provider="github",
                container_tags=(),
                redirect_url="http://unsafe.example",
                document_limit=0,
                metadata={},
            )


if __name__ == "__main__":
    unittest.main()
