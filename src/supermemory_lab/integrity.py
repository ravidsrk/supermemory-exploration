"""Canonical serialization, digests, signatures, and run identities."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import secrets
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_parts(*values: str) -> str:
    return hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest()


def sign_json(key: bytes, value: Any) -> str:
    return hmac.new(key, canonical_bytes(value), hashlib.sha256).hexdigest()


def verify_json_signature(key: bytes, value: Any, signature: str) -> bool:
    return hmac.compare_digest(signature, sign_json(key, value))


def new_run_identity() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{secrets.token_hex(3)}"
