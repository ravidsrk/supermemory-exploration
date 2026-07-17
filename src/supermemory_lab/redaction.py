"""Shared credential redaction for configuration, traces, and probe artifacts."""

from __future__ import annotations

import re
from threading import RLock
from typing import Any, Iterable, Mapping, Optional


_SECRET_KEY_PARTS = ("authorization", "api_key", "apikey", "password", "secret", "token")
_SAFE_TOKEN_COUNT_KEYS = {
    "prompttokens",
    "completiontokens",
    "totaltokens",
    "tokensprocessed",
    "estimatedcontexttokens",
    "meanestimatedcontexttokens",
}
_SECRET_VALUE = re.compile(
    r"(?:sk-or-v1|sm|ss_live|monid_live|ctxt_secret|vcp|ak)_[A-Za-z0-9_-]{8,}"
)
_registered_values: set[str] = set()
_lock = RLock()


def register_secret(value: Optional[str]) -> None:
    """Register one configured credential for exact value-level redaction."""

    if isinstance(value, str) and len(value) >= 8:
        with _lock:
            _registered_values.add(value)


def register_secrets(values: Iterable[Optional[str]]) -> None:
    for value in values:
        register_secret(value)


def redact_text(value: str, *, max_chars: int = 8_000) -> str:
    """Remove known credential shapes and exact configured values from free text."""

    result = _SECRET_VALUE.sub("[REDACTED]", value)
    with _lock:
        registered = sorted(_registered_values, key=len, reverse=True)
    for secret in registered:
        result = result.replace(secret, "[REDACTED]")
    return result[:max_chars]


def redact(value: Any, key: str = "", *, max_string_chars: int = 8_000) -> Any:
    """Recursively redact secret-shaped keys and credential values."""

    lowered = key.lower()
    normalized = re.sub(r"[^a-z]", "", lowered)
    safe_token_count = isinstance(value, (int, float)) and (
        normalized in _SAFE_TOKEN_COUNT_KEYS
        or normalized.endswith("tokens")
        or normalized.endswith("pricepertoken")
    )
    if not safe_token_count and (
        lowered == "key" or any(part in lowered for part in _SECRET_KEY_PARTS)
    ):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): redact(
                item_value, str(item_key), max_string_chars=max_string_chars
            )
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [redact(item, max_string_chars=max_string_chars) for item in value[:100]]
    if isinstance(value, tuple):
        return tuple(
            redact(item, max_string_chars=max_string_chars) for item in value[:100]
        )
    if isinstance(value, str):
        return redact_text(value, max_chars=max_string_chars)
    return value
