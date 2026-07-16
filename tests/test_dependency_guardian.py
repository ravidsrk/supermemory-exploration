import unittest
from typing import Any, Dict, List, Mapping

from supermemory_lab.dependency_guardian import DependencyRiskGuardianAgent


class FakeMemory:
    def __init__(self) -> None:
        self.documents: List[Dict[str, Any]] = []
        self.memories: List[Dict[str, Any]] = []

    def profile(self, container_tag: str, **kwargs: Any) -> Dict[str, Any]:
        return {"profile": {"static": ["Require CVE evidence and sandbox tests"], "dynamic": []}}

    def add_document(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        self.documents.append({"content": content, **kwargs})
        return {"id": "doc"}

    def create_memories(self, container_tag: str, memories: List[Mapping[str, Any]]) -> Dict[str, Any]:
        self.memories.extend(dict(item) for item in memories)
        return {"memories": [{"id": "memory"}]}


class FakeMonid:
    def __init__(self, method: str = "GET") -> None:
        self.method = method
        self.run_calls = 0

    def inspect(self, provider: str, endpoint: str) -> Dict[str, Any]:
        return {"method": self.method, "price": {"amount": {"value": 0.05}}}

    def run(self, provider: str, endpoint: str, tool_input: Mapping[str, Any]) -> Dict[str, Any]:
        self.run_calls += 1
        return {"successful": True, "output": {"vulnerabilities": []}}


class FakeComposio:
    def get_tool(self, slug: str) -> Dict[str, Any]:
        return {"slug": slug, "no_auth": True}

    def execute_tool(self, slug: str, **kwargs: Any) -> Dict[str, Any]:
        return {"successful": True, "data": {"hits": []}}


class FakeExa:
    def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        return {"results": [{"title": "official release"}]}


class FakeCommand:
    pass


class FakeSuperServe:
    def __init__(self, exit_code: int = 0) -> None:
        self.exit_code = exit_code
        self.deleted = False

    def create_sandbox(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        return {"id": "box", "access_token": "sandbox-token", "status": "running"}

    def command_transport(self, sandbox_id: str, access_token: str) -> FakeCommand:
        return FakeCommand()

    def exec(self, transport: Any, command: str, **kwargs: Any) -> Dict[str, Any]:
        if "base64 -d" in command:
            return {"exit_code": 0, "stdout": "", "stderr": ""}
        return {"exit_code": self.exit_code, "stdout": "SMOKE_OK", "stderr": ""}

    def delete_sandbox(self, sandbox_id: str) -> Dict[str, Any]:
        self.deleted = True
        return {"success": True}


class FakeLLM:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return "Evidence is encouraging, but a human must authorize any upgrade."


class DependencyGuardianTests(unittest.TestCase):
    def _agent(self, memory: FakeMemory, monid: FakeMonid, sandbox: FakeSuperServe) -> DependencyRiskGuardianAgent:
        return DependencyRiskGuardianAgent(
            memory,
            FakeLLM(),
            monid,
            FakeComposio(),
            FakeExa(),
            sandbox,
            workspace_id="deps:one",
            allowed_monid_tool="security:/cve",
            max_monid_price=0.06,
        )

    def test_collects_sources_tests_sandbox_and_never_authorizes_upgrade(self) -> None:
        memory = FakeMemory()
        sandbox = FakeSuperServe()
        report = self._agent(memory, FakeMonid(), sandbox).assess(
            package="urllib3",
            version="2.7.0",
            monid_provider="security",
            monid_endpoint="/cve",
            monid_input={"queryParams": {"package": "urllib3"}},
            smoke_script="print('SMOKE_OK')",
            sandbox_name="box",
        )

        self.assertTrue(report.sandbox_passed)
        self.assertTrue(report.sandbox_deleted)
        self.assertFalse(report.upgrade_authorized)
        self.assertEqual(len(memory.documents), 4)
        self.assertEqual(len(memory.memories), 1)
        self.assertTrue(sandbox.deleted)

    def test_non_get_tool_is_rejected_before_execution(self) -> None:
        monid = FakeMonid(method="POST")

        with self.assertRaises(PermissionError):
            self._agent(FakeMemory(), monid, FakeSuperServe()).assess(
                package="urllib3",
                version="2.7.0",
                monid_provider="security",
                monid_endpoint="/cve",
                monid_input={},
                smoke_script="pass",
                sandbox_name="box",
            )

        self.assertEqual(monid.run_calls, 0)

    def test_price_cap_is_enforced(self) -> None:
        agent = DependencyRiskGuardianAgent(
            FakeMemory(),
            FakeLLM(),
            FakeMonid(),
            FakeComposio(),
            FakeExa(),
            FakeSuperServe(),
            workspace_id="deps:one",
            allowed_monid_tool="security:/cve",
            max_monid_price=0.01,
        )
        with self.assertRaises(PermissionError):
            agent.assess(
                package="urllib3",
                version="2.7.0",
                monid_provider="security",
                monid_endpoint="/cve",
                monid_input={},
                smoke_script="pass",
                sandbox_name="box",
            )


if __name__ == "__main__":
    unittest.main()
