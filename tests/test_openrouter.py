import unittest

from supermemory_lab.openrouter import OpenRouterClient

from .fakes import RecordingTransport


class OpenRouterClientTests(unittest.TestCase):
    def test_extracts_assistant_message(self) -> None:
        transport = RecordingTransport(
            [{"choices": [{"message": {"content": "  hello  "}}]}]
        )
        client = OpenRouterClient(transport, model="example/model")

        answer = client.complete("system", "user")

        self.assertEqual(answer, "hello")
        self.assertEqual(transport.calls[0][1], "/chat/completions")
        self.assertEqual(transport.calls[0][2]["model"], "example/model")


if __name__ == "__main__":
    unittest.main()
