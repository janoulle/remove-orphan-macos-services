#!/usr/bin/env python3
"""Check or refresh public skill files from a canonical skill directory."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path


FILES = {
    "SKILL.md": "SKILL.md",
    "agents/openai.yaml": "agents/openai.yaml",
    "references/FAQ.md": "FAQ.md",
    "references/MANIFEST.md": "references/MANIFEST.md",
    "references/RESTORE.md": "references/RESTORE.md",
    "scripts/remove_orphan_services.py": "scripts/remove_orphan_services.py",
    "scripts/test_remove_orphan_services.py": "scripts/test_remove_orphan_services.py",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def validate_source(source: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"canonical skill directory does not exist: {source}")
    missing = [relative for relative in FILES if not (source / relative).is_file()]
    if missing:
        raise SystemExit("canonical skill is incomplete: " + ", ".join(missing))
    return source


def main() -> int:
    args = arguments()
    source = validate_source(args.source)
    mirror = Path(__file__).resolve().parent.parent
    differences: list[str] = []

    for source_relative, mirror_relative in FILES.items():
        source_file = source / source_relative
        mirror_file = mirror / mirror_relative
        same = mirror_file.is_file() and filecmp.cmp(source_file, mirror_file, shallow=False)
        if same:
            continue
        differences.append(mirror_relative)
        if args.apply:
            mirror_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, mirror_file)
            print(f"UPDATED: {mirror_relative}")

    if args.check and differences:
        for path in differences:
            print(f"OUT-OF-SYNC: {path}", file=sys.stderr)
        return 1
    if args.check:
        print("Mirror matches canonical distributable files.")
    elif not differences:
        print("Mirror already matches canonical distributable files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
