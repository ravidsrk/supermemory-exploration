from unittest.mock import patch
import unittest

from supermemory_lab.http import ApiError, UrlLibTransport


class UrlLibTransportTests(unittest.TestCase):
    def test_timeout_becomes_typed_network_error_without_credential(self):
        transport = UrlLibTransport(
            "https://example.invalid", "credential-must-not-escape", timeout_seconds=1
        )
        with patch("supermemory_lab.http.urlopen", side_effect=TimeoutError):
            with self.assertRaises(ApiError) as raised:
                transport.request("POST", "/slow", {"bounded": True})

        self.assertIsNone(raised.exception.status)
        self.assertEqual(raised.exception.detail, "request timed out")
        self.assertNotIn("credential-must-not-escape", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
