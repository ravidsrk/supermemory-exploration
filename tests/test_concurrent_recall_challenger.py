from dataclasses import replace
import time
import unittest

from supermemory_lab.concurrent_recall_challenger import (
    ConcurrentRecallChallenger,
    RecallProbe,
)


class FakeMemory:
    def __init__(self, *, leak=False, fail_surface=""):
        self.leak = leak
        self.fail_surface = fail_surface

    def _response(self, surface):
        time.sleep(0.005)
        if surface == self.fail_surface:
            raise ConnectionError("synthetic read failure")
        value = "EXPECTED"
        if self.leak:
            value += " FORBIDDEN"
        return value

    def search_memories(self, query, **kwargs):
        surface = kwargs["search_mode"]
        return {"results": [{"memory": self._response(surface)}]}

    def search_documents(self, query, **kwargs):
        return {"results": [{"content": self._response("documents")}]}

    def profile(self, container_tag, **kwargs):
        return {"profile": {"static": [self._response("profile")], "dynamic": []}}


def probes():
    return [
        RecallProbe(
            f"probe-{surface}", surface, "EXPECTED", "EXPECTED", ("FORBIDDEN",)
        )
        for surface in ("memories", "hybrid", "documents", "profile")
    ]


class ConcurrentRecallChallengerTests(unittest.TestCase):
    def challenger(self, memory):
        return ConcurrentRecallChallenger(
            memory,
            container_tag="tenant:one",
            signing_key=b"0123456789abcdef0123456789abcdef",
        )

    def test_concurrent_four_surface_report_is_signed_and_bounded(self):
        challenger = self.challenger(FakeMemory())
        challenge = challenger.build_challenge(probes(), rounds=3, max_workers=4)
        report = challenger.run(challenge)

        self.assertTrue(challenger.verify_challenge(challenge))
        self.assertTrue(challenger.verify_report(challenge, report))
        self.assertEqual(len(report.samples), 12)
        self.assertEqual(len(report.surface_metrics), 4)
        self.assertEqual(report.success_rate, 1.0)
        self.assertEqual(report.leak_count, 0)
        self.assertGreater(report.peak_in_flight, 1)
        self.assertLessEqual(report.peak_in_flight, 4)
        self.assertFalse(report.external_action_authorized)

    def test_failure_and_leak_are_counted_without_raw_report_content(self):
        challenger = self.challenger(
            FakeMemory(leak=True, fail_surface="documents")
        )
        challenge = challenger.build_challenge(probes(), rounds=1, max_workers=4)
        report = challenger.run(challenge)

        self.assertEqual(report.error_count, 1)
        self.assertEqual(report.leak_count, 3)
        self.assertEqual(report.success_rate, 0.0)
        self.assertNotIn("FORBIDDEN", str(report))

    def test_tampering_and_unbounded_challenges_are_denied(self):
        challenger = self.challenger(FakeMemory())
        challenge = challenger.build_challenge(probes(), rounds=1, max_workers=2)
        with self.assertRaises(PermissionError):
            challenger.run(replace(challenge, max_workers=3))
        report = challenger.run(challenge)
        self.assertFalse(
            challenger.verify_report(
                challenge, replace(report, external_action_authorized=True)
            )
        )
        with self.assertRaises(ValueError):
            challenger.build_challenge(probes(), rounds=101, max_workers=2)
        with self.assertRaises(ValueError):
            challenger.build_challenge(probes(), rounds=1, max_workers=33)


if __name__ == "__main__":
    unittest.main()
