import unittest

from supermemory_lab.probes import _redact, _summarize_search


class ProbeSafetyTests(unittest.TestCase):
    def test_redacts_secret_shaped_keys_recursively(self) -> None:
        data = {
            "authorization": "Bearer secret",
            "nested": {"apiKey": "secret", "safe": "value"},
        }

        redacted = _redact(data)

        self.assertEqual(redacted["authorization"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["apiKey"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["safe"], "value")

    def test_redacts_bare_key_field_from_scoped_key_response(self) -> None:
        redacted = _redact({"id": "key_id", "key": "sm_scoped_secret"})

        self.assertEqual(redacted["id"], "key_id")
        self.assertEqual(redacted["key"], "[REDACTED]")

    def test_search_summary_preserves_result_kind_and_scores(self) -> None:
        summary = _summarize_search(
            {
                "timing": 42,
                "total": 2,
                "results": [
                    {"id": "m1", "memory": "fact", "similarity": 0.9},
                    {"id": "c1", "chunk": "source", "similarity": 0.8},
                ],
            }
        )

        self.assertEqual(summary["resultCount"], 2)
        self.assertEqual(summary["results"][0]["kind"], "memory")
        self.assertEqual(summary["results"][1]["kind"], "chunk")


if __name__ == "__main__":
    unittest.main()
