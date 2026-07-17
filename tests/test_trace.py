from pathlib import Path
import tempfile
import unittest

from supermemory_lab.trace import ExperimentFailed, RunTrace


class RunTraceFailureTests(unittest.TestCase):
    def test_failed_evaluation_writes_trace_then_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = RunTrace("failed-evaluation", experiment="test")
            trace.metric("evaluation", {"passed": False, "reason": "synthetic"})
            with self.assertRaises(ExperimentFailed):
                trace.write(temporary)
            self.assertTrue((Path(temporary) / "failed-evaluation.json").exists())

    def test_cleanup_error_is_a_process_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = RunTrace("failed-cleanup", experiment="test")
            trace.metric("evaluation", {"passed": True})
            trace.metric("cleanup", {"container": {"error": "synthetic"}})
            with self.assertRaises(ExperimentFailed):
                trace.write(temporary)

    def test_passing_evaluation_returns_trace_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = RunTrace("passing", experiment="test")
            trace.metric("evaluation", {"passed": True})
            self.assertTrue(trace.write(temporary).exists())


if __name__ == "__main__":
    unittest.main()
