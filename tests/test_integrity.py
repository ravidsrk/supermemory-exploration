import unittest

from supermemory_lab.integrity import (
    canonical_json,
    digest_json,
    digest_parts,
    new_run_identity,
    sign_json,
    verify_json_signature,
)


class IntegrityUtilityTests(unittest.TestCase):
    def test_canonical_digest_and_signature_are_stable(self) -> None:
        left = {"b": [2, 1], "a": "value"}
        right = {"a": "value", "b": [2, 1]}
        key = b"0123456789abcdef"

        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(digest_json(left), digest_json(right))
        signature = sign_json(key, left)
        self.assertTrue(verify_json_signature(key, right, signature))
        self.assertNotEqual(digest_parts("ab", "c"), digest_parts("a", "bc"))

    def test_run_identity_has_timestamp_and_random_suffix(self) -> None:
        first = new_run_identity()
        second = new_run_identity()
        self.assertRegex(first, r"^\d{14}-[0-9a-f]{6}$")
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
