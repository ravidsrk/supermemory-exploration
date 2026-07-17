from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from supermemory_lab.self_host_recovery import (
    RecoveryProofSigner,
    copy_verified_directory,
    snapshot_directory,
)


class SelfHostRecoveryTests(unittest.TestCase):
    def test_copy_is_byte_verified_and_snapshot_exposes_no_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "api-key").write_text("credential-must-not-escape")
            nested = source / "nested"
            nested.mkdir()
            (nested / "data").write_bytes(b"encrypted-state")

            before = snapshot_directory(source)
            copied = copy_verified_directory(source, root / "backup")

            self.assertEqual(before, copied)
            self.assertEqual(before.file_count, 2)
            self.assertNotIn("credential-must-not-escape", str(before))

    def test_signed_proof_binds_equal_snapshots_and_recovery_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "state").write_text("value")
            snapshot = snapshot_directory(root)
            signer = RecoveryProofSigner(
                b"0123456789abcdef0123456789abcdef"
            )
            proof = signer.build(
                server_version="0.0.5",
                source_snapshot=snapshot,
                backup_snapshot=snapshot,
                restore_snapshot=snapshot,
                restart_marker_visible=True,
                restore_marker_visible=True,
                restore_profile_visible=True,
                restored_delete_verified=True,
                source_delete_verified=True,
                orphan_process_count=0,
            )

            self.assertTrue(signer.verify(proof))
            self.assertFalse(signer.verify(replace(proof, restore_marker_visible=False)))


if __name__ == "__main__":
    unittest.main()
