"""External authorization and durable replay control for governed mutations.

Controllers consume pre-issued grants through the narrow ``AuthorizationLedger``
interface. Production callers should use ``SqliteAuthorizationLedger`` (or an
equivalent transactional service). ``TestingAuthorizationLedger`` is deliberately
limited to unit tests and synthetic harnesses.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Iterator, Protocol, Sequence, Tuple


def authorization_resource(*parts: Any) -> str:
    """Return a stable digest for the exact mutation being authorized."""

    encoded = json.dumps(
        parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AuthorizationLedger(Protocol):
    def consume(self, *, scope: str, actor: str, resource_hash: str) -> None:
        """Atomically consume one pre-issued grant or raise PermissionError."""


@dataclass(frozen=True)
class AuthorizationGrant:
    scope: str
    actor: str
    resource_hash: str


class TestingAuthorizationLedger:
    """Explicitly non-production ledger for isolated tests and synthetic harnesses.

    ``trust_first_use`` preserves focus in domain unit tests while still providing
    shared-ledger replay protection. Security tests should call ``grant`` explicitly.
    """

    def __init__(self, *, trust_first_use: bool = False) -> None:
        self._trust_first_use = trust_first_use
        self._pending: set[Tuple[str, str, str]] = set()
        self._consumed: set[Tuple[str, str, str]] = set()
        self._lock = RLock()

    def grant(self, *, scope: str, actor: str, resource_hash: str) -> None:
        key = _validated_key(scope, actor, resource_hash)
        with self._lock:
            if key in self._consumed:
                raise RuntimeError("authorization grant was already consumed")
            self._pending.add(key)

    def consume(self, *, scope: str, actor: str, resource_hash: str) -> None:
        key = _validated_key(scope, actor, resource_hash)
        with self._lock:
            if key in self._consumed:
                raise RuntimeError("authorization replay denied")
            if key not in self._pending and not self._trust_first_use:
                raise PermissionError("no matching external authorization grant")
            self._pending.discard(key)
            self._consumed.add(key)


class SqliteAuthorizationLedger:
    """Transactional, HMAC-protected authorization and replay ledger."""

    def __init__(self, path: Path, *, integrity_key: bytes) -> None:
        if len(integrity_key) < 16:
            raise ValueError("authorization integrity key must contain at least 16 bytes")
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._key = bytes(integrity_key)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self._path), timeout=30, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS authorization_grants (
                    scope TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    resource_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    PRIMARY KEY (scope, actor, resource_hash)
                )
                """
            )

    def _signature(self, key: Sequence[str], state: str) -> str:
        payload = json.dumps(
            [*key, state], separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def grant(self, *, scope: str, actor: str, resource_hash: str) -> None:
        key = _validated_key(scope, actor, resource_hash)
        signature = self._signature(key, "pending")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT state FROM authorization_grants WHERE scope=? AND actor=? AND resource_hash=?",
                key,
            ).fetchone()
            if row is not None:
                raise RuntimeError("authorization grant already exists")
            connection.execute(
                "INSERT INTO authorization_grants VALUES (?, ?, ?, 'pending', ?)",
                (*key, signature),
            )

    def consume(self, *, scope: str, actor: str, resource_hash: str) -> None:
        key = _validated_key(scope, actor, resource_hash)
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT state, signature FROM authorization_grants WHERE scope=? AND actor=? AND resource_hash=?",
                key,
            ).fetchone()
            if row is None:
                raise PermissionError("no matching external authorization grant")
            state, signature = str(row[0]), str(row[1])
            if not hmac.compare_digest(signature, self._signature(key, state)):
                raise PermissionError("authorization ledger integrity check failed")
            if state != "pending":
                raise RuntimeError("authorization replay denied")
            consumed_signature = self._signature(key, "consumed")
            connection.execute(
                """
                UPDATE authorization_grants
                SET state='consumed', signature=?
                WHERE scope=? AND actor=? AND resource_hash=? AND state='pending'
                """,
                (consumed_signature, *key),
            )
            if connection.total_changes != 1:
                raise RuntimeError("authorization was concurrently consumed")


def consume_authorization(
    ledger: AuthorizationLedger,
    *,
    scope: str,
    actor: str,
    resource_hash: str,
) -> None:
    """Validate fields and atomically consume a matching external grant."""

    ledger.consume(scope=scope, actor=actor, resource_hash=resource_hash)


def _validated_key(scope: str, actor: str, resource_hash: str) -> Tuple[str, str, str]:
    values = (str(scope).strip(), str(actor).strip(), str(resource_hash).strip())
    if not all(values):
        raise ValueError("authorization scope, actor, and resource hash are required")
    return values
