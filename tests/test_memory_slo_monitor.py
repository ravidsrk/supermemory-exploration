from dataclasses import replace
import unittest

from supermemory_lab.memory_slo_monitor import (
    CanarySpec,
    MemorySLOCanaryMonitor,
    SLOPolicy,
)


class FakeMemory:
    def __init__(self, *, leak=False, fail=False):
        self.leak = leak
        self.fail = fail

    def _response(self):
        if self.fail:
            raise ConnectionError("synthetic outage")
        text = "EXPECTED-CANARY"
        if self.leak:
            text += " FORBIDDEN-TENANT"
        return text

    def search_memories(self, query, **kwargs):
        return {"results": [{"memory": self._response()}]}

    def search_documents(self, query, **kwargs):
        return {"results": [{"content": self._response()}]}

    def profile(self, container_tag, **kwargs):
        return {"profile": {"static": [self._response()], "dynamic": []}}


class FakeLLM:
    def __init__(self):
        self.calls = 0
        self.prompts = []

    def complete(self, system_prompt, user_prompt):
        self.calls += 1
        self.prompts.append(user_prompt)
        return "Investigate retrieval isolation and latency before changing production."


def specs():
    return [
        CanarySpec(
            f"canary-{surface}",
            surface,
            "EXPECTED-CANARY",
            "EXPECTED-CANARY",
            ("FORBIDDEN-TENANT",),
        )
        for surface in ("memories", "hybrid", "documents", "profile")
    ]


class MemorySLOMonitorTests(unittest.TestCase):
    def monitor(self, memory, llm=None, **kwargs):
        return MemorySLOCanaryMonitor(
            memory,
            llm or FakeLLM(),
            container_tag="tenant:one",
            signing_key=b"0123456789abcdef0123456789abcdef",
            **kwargs,
        )

    def test_healthy_four_surface_report_is_signed_and_skips_llm(self):
        llm = FakeLLM()
        monitor = self.monitor(FakeMemory(), llm)
        report = monitor.run(
            specs(), rounds=2, policy=SLOPolicy(1.0, 10_000.0, 0)
        )

        self.assertTrue(monitor.verify_report(report))
        self.assertEqual(report.success_rate, 1.0)
        self.assertEqual(len(report.samples), 8)
        self.assertEqual(len(report.surface_metrics), 4)
        self.assertEqual(report.violations, ())
        self.assertEqual(monitor.explain(report), "NO_EXTERNAL_ACTION\nMEMORY_SLO_HEALTHY")
        self.assertEqual(llm.calls, 0)

    def test_leak_is_hard_violation_and_model_sees_metrics_not_raw_memory(self):
        llm = FakeLLM()
        monitor = self.monitor(FakeMemory(leak=True), llm)
        report = monitor.run(
            specs()[:1], rounds=1, policy=SLOPolicy(1.0, 10_000.0, 0)
        )
        explanation = monitor.explain(report)

        self.assertEqual(report.leak_count, 1)
        self.assertTrue(any("leak_count" in item for item in report.violations))
        self.assertNotIn("FORBIDDEN-TENANT", llm.prompts[0])
        self.assertTrue(explanation.startswith("NO_EXTERNAL_ACTION"))
        self.assertEqual(llm.calls, 1)

    def test_outage_and_latency_breach_reduce_slo(self):
        ticks = iter([0.0, 0.100, 0.100, 0.300])
        monitor = self.monitor(FakeMemory(fail=True), clock=lambda: next(ticks))
        report = monitor.run(
            specs()[:1], rounds=2, policy=SLOPolicy(1.0, 150.0, 0)
        )

        self.assertEqual(report.success_rate, 0.0)
        self.assertEqual(report.p95_ms, 200.0)
        self.assertTrue(any("p95_ms" in item for item in report.violations))
        self.assertTrue(all(sample.error_type == "ConnectionError" for sample in report.samples))

    def test_tampered_report_is_denied(self):
        monitor = self.monitor(FakeMemory())
        report = monitor.run(
            specs()[:1], rounds=1, policy=SLOPolicy(1.0, 10_000.0, 0)
        )
        tampered = replace(report, success_rate=0.0)
        self.assertFalse(monitor.verify_report(tampered))
        with self.assertRaises(PermissionError):
            monitor.explain(tampered)

    def test_invalid_specs_and_policy_are_rejected(self):
        monitor = self.monitor(FakeMemory())
        with self.assertRaises(ValueError):
            monitor.run([], rounds=1, policy=SLOPolicy())
        with self.assertRaises(ValueError):
            monitor.run(
                [CanarySpec("one", "wrong", "q", "x")],
                rounds=1,
                policy=SLOPolicy(),
            )


if __name__ == "__main__":
    unittest.main()
