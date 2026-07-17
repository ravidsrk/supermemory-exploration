from pathlib import Path
import sqlite3
import tempfile
import unittest

from supermemory_lab.authorization import (
    SqliteAuthorizationLedger,
    TestingAuthorizationLedger,
    authorization_resource,
)


class AuthorizationLedgerTests(unittest.TestCase):
    def test_testing_ledger_requires_explicit_grant_and_denies_replay(self) -> None:
        ledger = TestingAuthorizationLedger()
        resource = authorization_resource("plan", "one")
        with self.assertRaises(PermissionError):
            ledger.consume(scope="test.apply", actor="owner", resource_hash=resource)
        ledger.grant(scope="test.apply", actor="owner", resource_hash=resource)
        ledger.consume(scope="test.apply", actor="owner", resource_hash=resource)
        with self.assertRaises(RuntimeError):
            ledger.consume(scope="test.apply", actor="owner", resource_hash=resource)

    def test_sqlite_ledger_denies_replay_across_fresh_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authorization.sqlite3"
            key = b"0123456789abcdef0123456789abcdef"
            resource = authorization_resource("plan", "durable")
            first = SqliteAuthorizationLedger(path, integrity_key=key)
            first.grant(scope="test.apply", actor="owner", resource_hash=resource)
            first.consume(scope="test.apply", actor="owner", resource_hash=resource)
            fresh = SqliteAuthorizationLedger(path, integrity_key=key)
            with self.assertRaises(RuntimeError):
                fresh.consume(scope="test.apply", actor="owner", resource_hash=resource)

    def test_sqlite_ledger_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authorization.sqlite3"
            key = b"0123456789abcdef0123456789abcdef"
            resource = authorization_resource("plan", "tamper")
            ledger = SqliteAuthorizationLedger(path, integrity_key=key)
            ledger.grant(scope="test.apply", actor="owner", resource_hash=resource)
            with sqlite3.connect(str(path)) as connection:
                connection.execute("UPDATE authorization_grants SET signature='forged'")
            with self.assertRaises(PermissionError):
                ledger.consume(scope="test.apply", actor="owner", resource_hash=resource)


if __name__ == "__main__":
    unittest.main()
