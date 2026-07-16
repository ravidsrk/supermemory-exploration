"""OpenAI-compatible Memory Router adapter with bounded diagnostics."""

import json
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .http import ApiError, JsonObject


_ROUTER_HEADERS = (
    "x-supermemory-conversation-id",
    "x-supermemory-context-modified",
    "x-supermemory-tokens-processed",
    "x-supermemory-chunks-created",
    "x-supermemory-chunks-retrieved",
    "x-supermemory-error",
)


class MemoryRouterClient:
    """Send chat completions through Supermemory's transparent proxy.

    The provider key remains in the normal Authorization header; the
    Supermemory key is sent separately as required by the Router API.
    """

    def __init__(
        self,
        *,
        supermemory_api_key: str,
        provider_api_key: str,
        provider_base_url: str,
        model: str,
        timeout_seconds: float = 90.0,
        opener: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._supermemory_api_key = supermemory_api_key
        self._provider_api_key = provider_api_key
        self._provider_base_url = provider_base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._opener = opener or urlopen

    def complete(
        self,
        *,
        user_id: str,
        conversation_id: Optional[str],
        messages: Sequence[Mapping[str, str]],
        max_tokens: int = 200,
    ) -> JsonObject:
        provider_url = f"{self._provider_base_url}/chat/completions"
        router_url = f"https://api.supermemory.ai/v3/{provider_url}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._provider_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "supermemory-field-lab/0.1",
            "x-supermemory-api-key": self._supermemory_api_key,
            "x-sm-user-id": user_id,
        }
        if conversation_id is not None:
            headers["x-sm-conversation-id"] = conversation_id
        request = Request(
            router_url,
            data=json.dumps(
                {
                    "model": self._model,
                    "temperature": 0,
                    "max_tokens": max_tokens,
                    "messages": [dict(message) for message in messages],
                }
            ).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                diagnostics = {
                    name: response.headers.get(name)
                    for name in _ROUTER_HEADERS
                    if response.headers.get(name) is not None
                }
        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            raise ApiError(
                "POST", "/v3/{provider}/chat/completions", error.code, _detail(raw)
            ) from None
        except URLError as error:
            raise ApiError(
                "POST", "/v3/{provider}/chat/completions", None, str(error.reason)
            ) from None

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            raise ApiError(
                "POST",
                "/v3/{provider}/chat/completions",
                None,
                "response was not valid JSON",
            ) from None
        text = _assistant_text(payload)
        usage = payload.get("usage") if isinstance(payload, Mapping) else None
        model = payload.get("model") if isinstance(payload, Mapping) else None
        choices = payload.get("choices") if isinstance(payload, Mapping) else None
        first = choices[0] if isinstance(choices, list) and choices else None
        finish_reason = first.get("finish_reason") if isinstance(first, Mapping) else None
        return {
            "text": text,
            "diagnostics": diagnostics,
            "usage": dict(usage) if isinstance(usage, Mapping) else None,
            "model": model if isinstance(model, str) else None,
            "finishReason": finish_reason if isinstance(finish_reason, str) else None,
        }


def _assistant_text(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        raise RuntimeError("Memory Router returned an unexpected response")
    choices = payload.get("choices")
    if not isinstance(choices, List) or not choices:
        raise RuntimeError("Memory Router response did not contain choices")
    first = choices[0]
    message = first.get("message") if isinstance(first, Mapping) else None
    content = message.get("content") if isinstance(message, Mapping) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Memory Router response did not contain assistant text")
    return content.strip()


def _detail(raw: str) -> str:
    try:
        payload = json.loads(raw)
        if isinstance(payload, Mapping):
            for key in ("message", "error", "detail"):
                value = payload.get(key)
                if isinstance(value, str):
                    return value[:500]
                if isinstance(value, Mapping) and isinstance(value.get("message"), str):
                    return str(value["message"])[:500]
    except json.JSONDecodeError:
        pass
    return raw.strip()[:500] or "empty error response"
