import importlib.util
import json
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "remove_orphan_services.py"
SPEC = importlib.util.spec_from_file_location("remove_orphan_services", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.root = Path(self.temp.name)
        self.launch_root = self.root / "LaunchDaemons"
        self.helper_root = self.root / "PrivilegedHelperTools"
        self.launch_root.mkdir()
        self.helper_root.mkdir()
        self.plist = self.launch_root / "com.example.helper.plist"
        self.helper = self.helper_root / "com.example.helper"
        self.owner = self.root / "Applications" / "Example.app"
        self.program = str(self.helper)
        self.write_plist()
        self.helper.write_bytes(b"helper")
        self.item = {
            "name": "Example",
            "scope": "system",
            "label": "com.example.helper",
            "plist": str(self.plist),
            "expected_program": self.program,
            "owner_app_absent": str(self.owner),
            "artifacts": [str(self.plist), str(self.helper)],
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_plist(self, *, label="com.example.helper", program=None):
        payload = {"Label": label, "Program": program or str(self.helper)}
        with self.plist.open("wb") as handle:
            plistlib.dump(payload, handle)

    def policy(self):
        return mock.patch.multiple(
            MODULE,
            allowed_plist_root=mock.DEFAULT,
            allowed_artifact_roots=mock.DEFAULT,
            owner_app_allowed=mock.DEFAULT,
        )

    def configure_policy(self, patched):
        patched["allowed_plist_root"].return_value = self.launch_root
        patched["allowed_artifact_roots"].return_value = (
            self.launch_root,
            self.helper_root,
        )
        patched["owner_app_allowed"].return_value = True

    def test_valid_exact_item_is_verified(self):
        with self.policy() as patched:
            self.configure_policy(patched)
            valid, reasons = MODULE.validate_item(self.item)
        self.assertTrue(valid)
        self.assertEqual(reasons, [])

    def test_program_mismatch_is_refused(self):
        self.item["expected_program"] = str(self.helper_root / "unexpected")
        with self.policy() as patched:
            self.configure_policy(patched)
            valid, reasons = MODULE.validate_item(self.item)
        self.assertFalse(valid)
        self.assertTrue(any("program mismatch" in reason for reason in reasons))

    def test_existing_owner_application_is_refused(self):
        self.owner.mkdir(parents=True)
        with self.policy() as patched:
            self.configure_policy(patched)
            valid, reasons = MODULE.validate_item(self.item)
        self.assertFalse(valid)
        self.assertTrue(any("owner application still exists" in reason for reason in reasons))

    def test_symlink_artifact_is_refused(self):
        target = self.helper_root / "real-helper"
        target.write_bytes(b"real")
        self.helper.unlink()
        self.helper.symlink_to(target)
        with self.policy() as patched:
            self.configure_policy(patched)
            valid, reasons = MODULE.validate_item(self.item)
        self.assertFalse(valid)
        self.assertTrue(any("symlink" in reason for reason in reasons))

    def test_parent_traversal_component_is_refused(self):
        self.item["artifacts"][1] = str(self.helper_root / ".." / "PrivilegedHelperTools" / self.helper.name)
        with self.policy() as patched:
            self.configure_policy(patched)
            valid, reasons = MODULE.validate_item(self.item)
        self.assertFalse(valid)
        self.assertTrue(any("'..' components" in reason for reason in reasons))

    def test_nested_artifact_is_refused(self):
        nested = self.helper_root / "nested" / "helper"
        nested.parent.mkdir()
        nested.write_bytes(b"nested")
        self.item["artifacts"][1] = str(nested)
        with self.policy() as patched:
            self.configure_policy(patched)
            valid, reasons = MODULE.validate_item(self.item)
        self.assertFalse(valid)
        self.assertTrue(any("outside the allowed" in reason for reason in reasons))

    def test_apply_requires_literal_confirmation(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"items": [self.item]}))
        argv = [str(SCRIPT), str(manifest), "--apply", "--backup-dir", str(self.root / "backups")]
        with self.policy() as patched, mock.patch.object(sys, "argv", argv):
            self.configure_policy(patched)
            with self.assertRaises(SystemExit) as raised:
                MODULE.main()
        self.assertEqual(raised.exception.code, 2)
        self.assertTrue(self.plist.exists())
        self.assertTrue(self.helper.exists())

    def test_backup_failure_happens_before_any_deletion(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"items": [self.item]}))
        argv = [
            str(SCRIPT),
            str(manifest),
            "--apply",
            "--confirm",
            MODULE.CONFIRMATION,
            "--backup-dir",
            str(self.root / "backups"),
        ]
        original_copy = MODULE.shutil.copy2
        calls = 0

        def fail_second_copy(source, destination, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated backup failure")
            return original_copy(source, destination, **kwargs)

        with (
            self.policy() as patched,
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(MODULE.os, "geteuid", return_value=0),
            mock.patch.object(MODULE.shutil, "copy2", side_effect=fail_second_copy),
        ):
            self.configure_policy(patched)
            with self.assertRaises(OSError):
                MODULE.main()
        self.assertTrue(self.plist.exists())
        self.assertTrue(self.helper.exists())

    def test_successful_apply_backs_up_hashes_then_deletes(self):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"items": [self.item]}))
        backup_base = self.root / "backups"
        argv = [
            str(SCRIPT),
            str(manifest),
            "--apply",
            "--confirm",
            MODULE.CONFIRMATION,
            "--backup-dir",
            str(backup_base),
        ]
        completed = mock.Mock(returncode=0)
        with (
            self.policy() as patched,
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(MODULE.os, "geteuid", return_value=0),
            mock.patch.object(MODULE.subprocess, "run", return_value=completed),
        ):
            self.configure_policy(patched)
            self.assertEqual(MODULE.main(), 0)
        self.assertFalse(self.plist.exists())
        self.assertFalse(self.helper.exists())
        backup_roots = list(backup_base.glob("orphan-services-*"))
        self.assertEqual(len(backup_roots), 1)
        report = json.loads((backup_roots[0] / "backup-manifest.json").read_text())
        self.assertEqual(len(report["files"]), 2)
        self.assertTrue(all(len(record["sha256"]) == 64 for record in report["files"]))


if __name__ == "__main__":
    unittest.main()
