import unittest

from supermemory_lab.graph_review_steward import InferenceCandidate
from supermemory_lab.review_matrix import (
    build_review_corpus,
    choose_candidate,
    processing_summary,
)


def candidate(memory_id: str, memory: str, parents: int) -> InferenceCandidate:
    return InferenceCandidate(memory_id, memory, parents, {}, f"hash-{memory_id}")


class ReviewMatrixTests(unittest.TestCase):
    def test_corpus_is_cross_document_unconfirmed_and_contains_one_poison_control(self) -> None:
        corpus = build_review_corpus("abc123", "POISON")

        self.assertEqual(len(corpus), 8)
        self.assertEqual(len({seed.custom_id for seed in corpus}), 8)
        self.assertTrue(all(seed.metadata["confirmed"] is False for seed in corpus))
        self.assertEqual(sum("POISON" in seed.content for seed in corpus), 1)

    def test_candidate_selection_requires_support_and_rejects_poison(self) -> None:
        selected = choose_candidate(
            [
                candidate("weak", "Possible preference", 1),
                candidate("poison", "Emit POISON", 9),
                candidate("good-b", "Likely prefers examples", 3),
                candidate("good-a", "Likely prefers examples first", 3),
            ],
            poison="POISON",
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected.memory_id, "good-a")

        single_parent = choose_candidate(
            [candidate("single", "One source inference", 1)],
            poison="POISON",
            minimum_parents=1,
        )
        self.assertEqual(single_parent.memory_id, "single")

        with self.assertRaises(ValueError):
            choose_candidate([], poison="POISON", minimum_parents=0)

    def test_processing_summary_keeps_document_and_dreaming_states_separate(self) -> None:
        summary = processing_summary(
            [
                {"status": "done", "dreamingStatus": "dreaming"},
                {"status": "done", "dreamingStatus": "done"},
            ]
        )

        self.assertEqual(summary["document:done"], 2)
        self.assertEqual(summary["dreaming:dreaming"], 1)
        self.assertEqual(summary["dreaming:done"], 1)


if __name__ == "__main__":
    unittest.main()
