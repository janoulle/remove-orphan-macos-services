import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MIRROR = Path(__file__).parents[1]
SYNC = MIRROR / "scripts" / "sync_from_canonical.py"
MAPPINGS = {
    "SKILL.md": "SKILL.md",
    "agents/openai.yaml": "agents/openai.yaml",
    "references/FAQ.md": "FAQ.md",
    "references/MANIFEST.md": "references/MANIFEST.md",
    "references/RESTORE.md": "references/RESTORE.md",
    "scripts/remove_orphan_services.py": "scripts/remove_orphan_services.py",
    "scripts/test_remove_orphan_services.py": "scripts/test_remove_orphan_services.py",
}


class MirrorSyncTests(unittest.TestCase):
    def run_sync(self, checkout: Path, source: Path, mode: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(checkout / "scripts" / "sync_from_canonical.py"), "--source", str(source), mode],
            text=True,
            capture_output=True,
            check=False,
        )

    def make_fixture(self, root: Path) -> tuple[Path, Path]:
        source = root / "canonical"
        checkout = root / "mirror"
        for source_relative, mirror_relative in MAPPINGS.items():
            source_file = source / source_relative
            mirror_file = checkout / mirror_relative
            source_file.parent.mkdir(parents=True, exist_ok=True)
            mirror_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_text(f"content for {source_relative}\n")
            mirror_file.write_text(f"content for {source_relative}\n")
        script_target = checkout / "scripts" / "sync_from_canonical.py"
        script_target.write_bytes(SYNC.read_bytes())
        return source, checkout

    def test_check_passes_for_matching_files(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            source, checkout = self.make_fixture(Path(directory))
            result = self.run_sync(checkout, source, "--check")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_fails_and_apply_repairs_difference(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            source, checkout = self.make_fixture(Path(directory))
            (checkout / "SKILL.md").write_text("stale\n")
            failed = self.run_sync(checkout, source, "--check")
            self.assertEqual(failed.returncode, 1)
            self.assertIn("OUT-OF-SYNC: SKILL.md", failed.stderr)
            applied = self.run_sync(checkout, source, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            verified = self.run_sync(checkout, source, "--check")
            self.assertEqual(verified.returncode, 0, verified.stderr)


if __name__ == "__main__":
    unittest.main()
