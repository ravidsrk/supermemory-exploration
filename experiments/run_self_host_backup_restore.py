"""Stopped-state backup, restart, clean-directory restore, and cleanup drill."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import time
from typing import Any, Dict, List, Optional

from supermemory_lab.client import SupermemoryClient
from supermemory_lab.http import ApiError, UrlLibTransport
from supermemory_lab.self_host_recovery import (
    RecoveryProofSigner,
    copy_verified_directory,
    snapshot_directory,
)
from supermemory_lab.trace import RunTrace


from supermemory_lab.integrity import new_run_identity


_identity = new_run_identity


def _load_env(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _matching_worker_pids(data_dir: Path) -> List[int]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        capture_output=True,
        text=True,
        check=True,
    )
    tokens = {str(data_dir), str(data_dir.absolute()), str(data_dir.resolve())}
    values = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped or " " not in stripped:
            continue
        pid_text, command = stripped.split(None, 1)
        if any(token in command for token in tokens) and "rivet-engine" in command:
            values.append(int(pid_text))
    return values


def _quarantine_worker_paths(
    data_dirs: List[Path], *, seconds: float
) -> Dict[str, int]:
    """Reap detached workers across macOS /tmp and /private/tmp path aliases."""

    detected = set()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        for data_dir in data_dirs:
            for pid in _matching_worker_pids(data_dir):
                detected.add(pid)
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        time.sleep(0.5)
    remaining = {
        pid
        for data_dir in data_dirs
        for pid in _matching_worker_pids(data_dir)
    }
    return {"detected": len(detected), "remaining": len(remaining)}


class LocalServer:
    def __init__(
        self,
        binary: Path,
        data_dir: Path,
        provider_env: Path,
        port: int,
        log_path: Path,
    ) -> None:
        self.binary = binary
        self.data_dir = data_dir
        self.provider_env = provider_env
        self.port = port
        self.log_path = log_path
        self.process: Optional[subprocess.Popen[bytes]] = None
        self._log: Any = None

    def start(self) -> SupermemoryClient:
        if self.process is not None:
            raise RuntimeError("local server is already running")
        environment = dict(os.environ)
        environment.update(_load_env(self.provider_env))
        environment.update(
            {
                "SUPERMEMORY_DATA_DIR": str(self.data_dir),
                "SUPERMEMORY_PORT": str(self.port),
                "PORT": str(self.port),
                "SUPERMEMORY_DISABLE_TELEMETRY": "1",
            }
        )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.log_path.open("wb")
        self.process = subprocess.Popen(
            [str(self.binary)],
            cwd=str(self.binary.parent.parent),
            env=environment,
            stdout=self._log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.monotonic() + 60
        last_error = "not-ready"
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("local server exited before readiness")
            key_path = self.data_dir / "api-key"
            if key_path.is_file():
                key = key_path.read_text(encoding="utf-8").strip()
                if key:
                    client = SupermemoryClient(
                        UrlLibTransport(
                            f"http://127.0.0.1:{self.port}",
                            key,
                            timeout_seconds=5,
                        )
                    )
                    try:
                        client.list_documents(
                            container_tags=["lab:readiness"], limit=1, page=1
                        )
                        return client
                    except ApiError as error:
                        last_error = f"api-{error.status or 'network'}"
            time.sleep(1)
        raise TimeoutError(f"local server readiness timed out ({last_error})")

    def stop(self) -> Dict[str, Any]:
        if self.process is None:
            return {"running": False, "orphanPids": _matching_worker_pids(self.data_dir)}
        process = self.process
        process.send_signal(signal.SIGTERM)
        forced = False
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            forced = True
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if self._log is not None:
            self._log.close()
        self.process = None
        self._log = None
        detected_orphans = set()
        # Reap immediate children here. The experiment adds longer explicit
        # quiescence barriers before backup and final teardown.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            current = _matching_worker_pids(self.data_dir)
            if current:
                detected_orphans.update(current)
                for pid in current:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            time.sleep(0.5)
        remaining = _matching_worker_pids(self.data_dir)
        return {
            "running": False,
            "mainExitCode": process.returncode,
            "forcedMainStop": forced,
            "orphanPidsAfterMain": len(detected_orphans),
            "orphanPidsAfterCleanup": len(remaining),
        }


def _visible(client: SupermemoryClient, container: str, marker: str) -> bool:
    response = client.search_memories(
        marker,
        container_tag=container,
        search_mode="hybrid",
        threshold=0.0,
        limit=10,
        rerank=False,
        rewrite_query=False,
    )
    return marker in json.dumps(response, ensure_ascii=False, default=str)


def _profile_visible(client: SupermemoryClient, container: str, marker: str) -> bool:
    response = client.profile(
        container,
        query=marker,
        threshold=0.0,
        include=["static", "dynamic", "buckets"],
    )
    return marker in json.dumps(response, ensure_ascii=False, default=str)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-binary", type=Path, required=True)
    parser.add_argument("--source-data-dir", type=Path, required=True)
    parser.add_argument("--provider-env", type=Path, required=True)
    parser.add_argument("--source-port", type=int, default=6779)
    parser.add_argument("--restore-port", type=int, default=6780)
    parser.add_argument("--published-latest-version", default="")
    args = parser.parse_args()
    if not args.server_binary.is_file() or not args.source_data_dir.is_dir():
        raise SystemExit("server binary and source data directory must exist")

    identity = _identity()
    suffix = identity[-6:].upper()
    workspace = f"lab:self-host-recovery:{identity}"
    marker = f"SELF_HOST_RECOVERY_{suffix}"
    backup_dir = Path("/tmp") / f"supermemory-backup-{identity}"
    restore_dir = Path("/tmp") / f"supermemory-restore-{identity}"
    trace = RunTrace(
        f"self-host-recovery-{identity}",
        experiment="self-host-stopped-backup-restart-clean-restore",
    )
    source = LocalServer(
        args.server_binary,
        args.source_data_dir,
        args.provider_env,
        args.source_port,
        Path(".runs") / f"self-host-source-{identity}.log",
    )
    restored = LocalServer(
        args.server_binary,
        restore_dir,
        args.provider_env,
        args.restore_port,
        Path(".runs") / f"self-host-restore-{identity}.log",
    )
    evaluation: Dict[str, Any] = {}
    cleanup: Dict[str, Any] = {}
    stop_reports: List[Mapping[str, Any]] = []
    try:
        source_client = source.start()
        source_client.create_memories(
            workspace,
            [
                {
                    "content": (
                        f"Synthetic stopped-backup recovery canary {marker}. "
                        f"The immutable recovery code is {marker}."
                    ),
                    "isStatic": True,
                    "metadata": {
                        "synthetic": True,
                        "kind": "backup-restore-canary",
                    },
                }
            ],
        )
        source_client.wait_for_memory(
            marker,
            container_tag=workspace,
            search_mode="hybrid",
            threshold=0.0,
            required_text=marker,
            timeout_seconds=120,
            poll_seconds=2,
        )
        profile_deadline = time.monotonic() + 120
        while time.monotonic() < profile_deadline:
            if _profile_visible(source_client, workspace, marker):
                break
            time.sleep(2)
        pre_backup_profile = _profile_visible(source_client, workspace, marker)
        stop_reports.append(source.stop())
        pre_backup_quarantine = _quarantine_worker_paths(
            [args.source_data_dir], seconds=15
        )

        source_snapshot = snapshot_directory(args.source_data_dir)
        backup_snapshot = copy_verified_directory(
            args.source_data_dir, backup_dir
        )
        restarted_client = source.start()
        restart_marker_visible = _visible(restarted_client, workspace, marker)
        restart_profile_visible = _profile_visible(
            restarted_client, workspace, marker
        )
        stop_reports.append(source.stop())

        restore_snapshot = copy_verified_directory(backup_dir, restore_dir)
        restored_client = restored.start()
        restore_marker_visible = _visible(restored_client, workspace, marker)
        restore_profile_visible = _profile_visible(
            restored_client, workspace, marker
        )
        restored_client.delete_container(workspace)
        restored_delete_verified = not _visible(
            restored_client, workspace, marker
        )
        stop_reports.append(restored.stop())

        cleanup_client = source.start()
        cleanup_client.delete_container(workspace)
        source_delete_verified = not _visible(cleanup_client, workspace, marker)
        stop_reports.append(source.stop())
        post_run_quarantine = _quarantine_worker_paths(
            [args.source_data_dir, restore_dir], seconds=15
        )
        orphan_count = sum(
            int(item.get("orphanPidsAfterCleanup") or 0)
            for item in stop_reports
        ) + pre_backup_quarantine["remaining"] + post_run_quarantine["remaining"]
        orphan_occurrences = sum(
            int(item.get("orphanPidsAfterMain") or 0)
            for item in stop_reports
        ) + pre_backup_quarantine["detected"] + post_run_quarantine["detected"]
        signer = RecoveryProofSigner(secrets.token_bytes(32))
        proof = signer.build(
            server_version=subprocess.run(
                [str(args.server_binary), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            ).stdout.strip(),
            source_snapshot=source_snapshot,
            backup_snapshot=backup_snapshot,
            restore_snapshot=restore_snapshot,
            restart_marker_visible=restart_marker_visible,
            restore_marker_visible=restore_marker_visible,
            restore_profile_visible=restore_profile_visible,
            restored_delete_verified=restored_delete_verified,
            source_delete_verified=source_delete_verified,
            orphan_process_count=orphan_count,
        )
        recovery_passed = all(
            (
                signer.verify(proof),
                source_snapshot == backup_snapshot,
                backup_snapshot == restore_snapshot,
                pre_backup_profile,
                restart_marker_visible,
                restart_profile_visible,
                restore_marker_visible,
                restore_profile_visible,
                restored_delete_verified,
                source_delete_verified,
                orphan_count == 0,
            )
        )
        clean_shutdowns = all(
            item.get("mainExitCode") in {0, -signal.SIGTERM}
            and item.get("forcedMainStop") is False
            for item in stop_reports
        )
        newer_release_available = bool(args.published_latest_version) and (
            args.published_latest_version != proof.server_version
        )
        evaluation = {
            "proofValid": signer.verify(proof),
            "serverVersion": proof.server_version,
            "sourceFiles": source_snapshot.file_count,
            "sourceBytes": source_snapshot.total_bytes,
            "sourceBackupDigestEqual": source_snapshot == backup_snapshot,
            "backupRestoreDigestEqual": backup_snapshot == restore_snapshot,
            "preBackupProfileVisible": pre_backup_profile,
            "restartMarkerVisible": restart_marker_visible,
            "restartProfileVisible": restart_profile_visible,
            "restoreMarkerVisible": restore_marker_visible,
            "restoreProfileVisible": restore_profile_visible,
            "restoredDeleteVerified": restored_delete_verified,
            "sourceDeleteVerified": source_delete_verified,
            "stopReports": stop_reports,
            "orphanProcessCount": orphan_count,
            "workerProcessesReaped": orphan_occurrences,
            "preBackupQuarantineSeconds": 15,
            "postRunQuarantineSeconds": 15,
            "preBackupQuarantine": pre_backup_quarantine,
            "postRunQuarantine": post_run_quarantine,
            "providerConfigurationIncludedInDataBackup": False,
            "providerConfigurationRestoredSeparately": True,
            "cleanShutdowns": clean_shutdowns,
            "publishedLatestVersion": args.published_latest_version or "not-supplied",
            "newerReleaseAvailable": newer_release_available,
            "upgradeRehearsalPerformed": False,
            "upgradeRehearsalBlockedByNoNewerRelease": (
                bool(args.published_latest_version) and not newer_release_available
            ),
            "recoveryPassed": recovery_passed,
        }
        evaluation["productionGatePassed"] = (
            recovery_passed
            and clean_shutdowns
            and newer_release_available
            and evaluation["upgradeRehearsalPerformed"]
        )
        evaluation["passed"] = recovery_passed
        trace.metric("proof", asdict(proof))
        trace.metric("evaluation", evaluation)
    finally:
        if source.process is not None:
            stop_reports.append(source.stop())
        if restored.process is not None:
            stop_reports.append(restored.stop())
        cleanup["backupRemoved"] = False
        cleanup["restoreRemoved"] = False
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        cleanup["backupRemoved"] = not backup_dir.exists()
        if restore_dir.exists():
            shutil.rmtree(restore_dir)
        cleanup["restoreRemoved"] = not restore_dir.exists()
        cleanup["remainingSourceWorkers"] = len(
            _matching_worker_pids(args.source_data_dir)
        )
        cleanup["remainingRestoreWorkers"] = len(
            _matching_worker_pids(restore_dir)
        )
        trace.metric("cleanup", cleanup)
        path = trace.write()
        print(json.dumps({
            "trace": str(path),
            "evaluation": evaluation,
            "cleanup": cleanup,
        }, indent=2))


if __name__ == "__main__":
    main()
