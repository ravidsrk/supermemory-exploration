import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.release_triage import ReleaseTriageRehearsalAgent


class FakeMemory:
    def __init__(self) -> None:
        self.runbook = ""
        self.calls: List[Any] = []

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(("document", content, kwargs))
        return {"id": "doc"}

    def create_memories(
        self, container_tag: str, memories: List[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        self.calls.append(("memory", container_tag, memories))
        self.runbook += " ".join(str(item["content"]) for item in memories)
        return {"memories": [{"id": "mem"}]}

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        return {"profile": {"static": [self.runbook], "dynamic": []}}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return """import hashlib
import hmac

def verify_webhook(secret, raw_body, timestamp, signature, now):
    if abs(now - timestamp) > 300:
        return False
    message = f"{timestamp}.".encode("utf-8") + raw_body
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
"""


class FakeVercel:
    def list_projects(self, **kwargs: Any) -> Dict[str, Any]:
        return {"projects": [{"id": "p1"}, {"id": "p2"}]}

    def list_deployments(self, **kwargs: Any) -> Dict[str, Any]:
        return {"deployments": [{"state": "READY"}, {"state": "ERROR"}]}


class FakeSuperServe:
    def __init__(self) -> None:
        self.test_runs = 0
        self.deleted = False
        self.network: Mapping[str, Any] = {}

    def create_sandbox(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        self.network = kwargs["network"]
        return {"id": "box", "access_token": "token", "status": "active"}

    def command_transport(self, sandbox_id: str, access_token: str) -> object:
        return object()

    def exec(self, transport: object, command: str, **kwargs: Any) -> Dict[str, Any]:
        if command.startswith("python3 -m unittest"):
            self.test_runs += 1
            return {"exit_code": 1 if self.test_runs == 1 else 0, "stderr": "tests"}
        return {"exit_code": 0}

    def delete_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        self.deleted = True
        return {}


class ReleaseTriageTests(unittest.TestCase):
    def test_separates_observed_release_state_from_verified_rehearsal(self) -> None:
        memory = FakeMemory()
        sandbox = FakeSuperServe()
        report = ReleaseTriageRehearsalAgent(
            memory,
            FakeLLM(),
            FakeVercel(),
            sandbox,
            workspace_id="release:triage",
        ).run(sandbox_name="triage-test")

        self.assertEqual(report.observed_project_count, 2)
        self.assertEqual(report.observed_state_counts, {"READY": 1, "ERROR": 1})
        self.assertTrue(report.rehearsal_initially_failed)
        self.assertFalse(report.rehearsal_repair_attempted)
        self.assertTrue(report.rehearsal_patch_passed)
        self.assertEqual(sandbox.network["deny_out"], ["0.0.0.0/0"])
        self.assertTrue(sandbox.deleted)
        snapshot = [call for call in memory.calls if call[0] == "document"][0][1]
        self.assertIn("not production diagnosis", snapshot.casefold())
        lesson = [call for call in memory.calls if call[0] == "memory"][-1][2][0]
        self.assertTrue(lesson["metadata"]["testPassed"])

    def test_failed_first_patch_gets_one_repair_before_verified_storage(self) -> None:
        class RepairSuperServe(FakeSuperServe):
            def exec(self, transport: object, command: str, **kwargs: Any) -> Dict[str, Any]:
                if command.startswith("python3 -m unittest"):
                    self.test_runs += 1
                    return {
                        "exit_code": 0 if self.test_runs == 3 else 1,
                        "stderr": "future timestamp still accepted",
                    }
                return {"exit_code": 0}

        memory = FakeMemory()
        sandbox = RepairSuperServe()
        report = ReleaseTriageRehearsalAgent(
            memory,
            FakeLLM(),
            FakeVercel(),
            sandbox,
            workspace_id="release:repair",
        ).run(sandbox_name="triage-repair")

        self.assertTrue(report.rehearsal_repair_attempted)
        self.assertTrue(report.rehearsal_patch_passed)
        self.assertEqual(sandbox.test_runs, 3)
        verified = [
            call
            for call in memory.calls
            if call[0] == "memory"
            and call[2][0]["metadata"]["kind"] == "verified-release-rehearsal"
        ]
        self.assertEqual(len(verified), 1)


if __name__ == "__main__":
    unittest.main()
