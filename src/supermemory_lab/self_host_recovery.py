"""Secret-safe directory snapshots and signed proof records for self-host recovery."""

from dataclasses import asdict, dataclass, replace
import hashlib
import hmac
import json
from pathlib import Path
import shutil
from typing import Any


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class DirectorySnapshot:
    file_count: int
    total_bytes: int
    tree_digest: str


@dataclass(frozen=True)
class SignedRecoveryProof:
    server_version: str
    source_snapshot: DirectorySnapshot
    backup_snapshot: DirectorySnapshot
    restore_snapshot: DirectorySnapshot
    restart_marker_visible: bool
    restore_marker_visible: bool
    restore_profile_visible: bool
    restored_delete_verified: bool
    source_delete_verified: bool
    orphan_process_count: int
    proof_hash: str
    signature: str


def snapshot_directory(root: Path) -> DirectorySnapshot:
    """Hash names and bytes without returning file contents or credentials."""

    root = Path(root)
    if not root.is_dir():
        raise ValueError("snapshot root must be an existing directory")
    digest = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    for path in sorted((item for item in root.rglob("*") if item.is_file())):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        size = path.stat().st_size
        digest.update(size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        file_count += 1
        total_bytes += size
    return DirectorySnapshot(file_count, total_bytes, digest.hexdigest())


def copy_verified_directory(source: Path, target: Path) -> DirectorySnapshot:
    source = Path(source)
    target = Path(target)
    if target.exists():
        raise FileExistsError("verified backup target must be a clean path")
    before = snapshot_directory(source)
    shutil.copytree(source, target, symlinks=True)
    after = snapshot_directory(target)
    if after != before:
        shutil.rmtree(target, ignore_errors=True)
        raise RuntimeError("copied self-host directory failed digest verification")
    return after


class RecoveryProofSigner:
    def __init__(self, signing_key: bytes) -> None:
        if len(signing_key) < 16:
            raise ValueError("signing_key must contain at least 16 bytes")
        self._key = signing_key

    def _sign(self, value: Any) -> str:
        return hmac.new(
            self._key, _canonical(value).encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def build(
        self,
        *,
        server_version: str,
        source_snapshot: DirectorySnapshot,
        backup_snapshot: DirectorySnapshot,
        restore_snapshot: DirectorySnapshot,
        restart_marker_visible: bool,
        restore_marker_visible: bool,
        restore_profile_visible: bool,
        restored_delete_verified: bool,
        source_delete_verified: bool,
        orphan_process_count: int,
    ) -> SignedRecoveryProof:
        if not server_version.strip() or orphan_process_count < 0:
            raise ValueError("server version and non-negative orphan count are required")
        unsigned = SignedRecoveryProof(
            server_version,
            source_snapshot,
            backup_snapshot,
            restore_snapshot,
            restart_marker_visible,
            restore_marker_visible,
            restore_profile_visible,
            restored_delete_verified,
            source_delete_verified,
            orphan_process_count,
            "",
            "",
        )
        proof_hash = hashlib.sha256(_canonical(asdict(unsigned)).encode()).hexdigest()
        with_hash = replace(unsigned, proof_hash=proof_hash)
        return replace(
            with_hash,
            signature=self._sign(asdict(replace(with_hash, signature=""))),
        )

    def verify(self, proof: SignedRecoveryProof) -> bool:
        unsigned = replace(proof, proof_hash="", signature="")
        expected_hash = hashlib.sha256(
            _canonical(asdict(unsigned)).encode()
        ).hexdigest()
        return (
            proof.source_snapshot == proof.backup_snapshot == proof.restore_snapshot
            and proof.orphan_process_count == 0
            and proof.proof_hash == expected_hash
            and hmac.compare_digest(
                proof.signature,
                self._sign(asdict(replace(proof, signature=""))),
            )
        )
