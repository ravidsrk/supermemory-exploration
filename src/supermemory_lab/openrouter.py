"""Tiny OpenRouter adapter used by end-to-end agent demos."""

from typing import Any, Mapping, Optional, Protocol

from .http import JsonTransport


class LanguageModel(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


class OpenRouterClient:
    def __init__(
        self,
        transport: JsonTransport,
        *,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 700,
    ) -> None:
        self._transport = transport
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._transport.request(
            "POST",
            "/chat/completions",
            {
                "model": self._model,
                "temperature": self._temperature,
                "max_tokens": self._max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenRouter response did not contain choices")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise RuntimeError("OpenRouter choice had an unexpected shape")
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise RuntimeError("OpenRouter choice did not contain a message")
        content: Optional[Any] = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenRouter message did not contain text")
        return content.strip()
