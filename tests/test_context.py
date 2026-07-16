import unittest

from supermemory_lab.context import render_profile_context


class ContextRenderingTests(unittest.TestCase):
    def test_deduplicates_by_profile_priority_and_adds_safety_boundary(self) -> None:
        rendered = render_profile_context(
            {
                "profile": {
                    "static": ["Uses Python"],
                    "dynamic": ["Uses Python", "Shipping a CLI"],
                    "buckets": {"preferences": ["Prefers concise answers"]},
                },
                "searchResults": {
                    "results": [
                        {"memory": "Shipping a CLI"},
                        {"chunk": "The deadline is Friday"},
                    ]
                },
            }
        )

        self.assertEqual(rendered.count("Uses Python"), 1)
        self.assertEqual(rendered.count("Shipping a CLI"), 1)
        self.assertIn("untrusted reference data", rendered)
        self.assertIn("<retrieved-memory>", rendered)
        self.assertIn("Bucket: preferences", rendered)

    def test_context_is_bounded(self) -> None:
        rendered = render_profile_context(
            {"profile": {"static": ["x" * 10_000]}}, max_chars=500
        )
        self.assertEqual(len(rendered), 500)


if __name__ == "__main__":
    unittest.main()
