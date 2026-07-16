import json
import unittest

from supermemory_lab.router import MemoryRouterClient


class FakeHeaders(dict):
    pass


class FakeResponse:
    def __init__(self) -> None:
        self.headers = FakeHeaders(
            {
                "x-supermemory-context-modified": "true",
                "x-supermemory-chunks-retrieved": "2",
            }
        )

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {"choices": [{"message": {"content": "Remembered answer"}}]}
        ).encode("utf-8")


class MemoryRouterTests(unittest.TestCase):
    def test_routes_provider_and_supermemory_credentials_separately(self) -> None:
        captured = {}

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

        client = MemoryRouterClient(
            supermemory_api_key="sm_test",
            provider_api_key="or_test",
            provider_base_url="https://openrouter.ai/api/v1",
            model="test/model",
            opener=opener,
        )
        result = client.complete(
            user_id="user_1",
            conversation_id="conversation_1",
            messages=[{"role": "user", "content": "What do you remember?"}],
        )

        request = captured["request"]
        self.assertEqual(
            request.full_url,
            "https://api.supermemory.ai/v3/https://openrouter.ai/api/v1/chat/completions",
        )
        self.assertEqual(request.get_header("Authorization"), "Bearer or_test")
        self.assertEqual(request.get_header("X-supermemory-api-key"), "sm_test")
        self.assertEqual(request.get_header("X-sm-user-id"), "user_1")
        self.assertEqual(result["text"], "Remembered answer")
        self.assertEqual(result["diagnostics"]["x-supermemory-chunks-retrieved"], "2")


if __name__ == "__main__":
    unittest.main()
