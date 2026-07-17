from dataclasses import replace
import unittest

from supermemory_lab.blinded_domain_benchmark import (
    BlindedDomainBenchmark,
    BlindedDomainCase,
)


class FakeMemory:
    def search_memories(self, query, **kwargs):
        if "ISOLATION" in query:
            return {"results": []}
        return {"results": [{"id": "memory-1", "memory": "CASE ANSWER"}]}

    def search_documents(self, query, **kwargs):
        return {"results": [{"documentId": "document-1", "content": "CASE ANSWER"}]}


class FakeLLM:
    def __init__(self):
        self.prompts = []

    def complete(self, system_prompt, user_prompt):
        self.prompts.append(system_prompt)
        return "ANSWER" if "CASE ANSWER" in system_prompt else "UNKNOWN"


class BlindedDomainBenchmarkTests(unittest.TestCase):
    def benchmark(self, llm=None):
        return BlindedDomainBenchmark(
            FakeMemory(),
            llm or FakeLLM(),
            container_tag="tenant:one",
            signing_key=b"0123456789abcdef0123456789abcdef",
            max_workers=2,
        )

    def cases(self):
        return [
            BlindedDomainCase(
                "known",
                "stable",
                "What is CASE?",
                "memories",
                ("ANSWER",),
                (),
                ("CASE", "ANSWER"),
            ),
            BlindedDomainCase(
                "isolated",
                "tenant-negative",
                "What is ISOLATION?",
                "memories",
                ("UNKNOWN",),
                ("SECRET",),
                (),
                ("SECRET",),
            ),
        ]

    def test_signed_counterbalanced_report_scores_after_answering(self):
        llm = FakeLLM()
        benchmark = self.benchmark(llm)
        manifest = benchmark.build_manifest(self.cases())
        report = benchmark.run(manifest)

        self.assertTrue(benchmark.verify_manifest(manifest))
        self.assertTrue(benchmark.verify_report(manifest, report))
        self.assertEqual(report.summary["caseCount"], 2)
        self.assertEqual(report.summary["memoryPassed"], 2)
        self.assertEqual(report.summary["baselinePassed"], 1)
        self.assertEqual(report.summary["retrievalPassed"], 2)
        self.assertEqual(len(llm.prompts), 4)
        rubric_terms = {"required_answer_terms", "forbidden_answer_terms"}
        self.assertTrue(all(not any(term in prompt for term in rubric_terms) for prompt in llm.prompts))

    def test_tampered_manifest_and_report_are_denied(self):
        benchmark = self.benchmark()
        manifest = benchmark.build_manifest(self.cases())
        with self.assertRaises(PermissionError):
            benchmark.run(replace(manifest, manifest_hash="wrong"))
        report = benchmark.run(manifest)
        self.assertFalse(
            benchmark.verify_report(
                manifest, replace(report, external_action_authorized=True)
            )
        )

    def test_invalid_surface_and_duplicate_names_are_rejected(self):
        benchmark = self.benchmark()
        case = self.cases()[0]
        with self.assertRaises(ValueError):
            benchmark.build_manifest([case, case])
        with self.assertRaises(ValueError):
            benchmark.build_manifest([replace(case, search_surface="profile")])


if __name__ == "__main__":
    unittest.main()
