#!/usr/bin/env python3
"""Audit and remove an exact manifest of verified orphan macOS launchd items."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import plistlib
import pwd
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

CONFIRMATION = "DELETE-VERIFIED-ORPHANS"
SYSTEM_ROOTS = (
    Path("/Library/LaunchAgents"),
    Path("/Library/LaunchDaemons"),
    Path("/Library/PrivilegedHelperTools"),
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def invoking_uid() -> int:
    return int(os.environ.get("SUDO_UID", os.getuid()))


def invoking_home() -> Path:
    return Path(pwd.getpwuid(invoking_uid()).pw_dir)


def launch_domain(scope: str) -> str:
    if scope == "system":
        return "system"
    if scope == "user":
        return f"gui/{invoking_uid()}"
    fail(f"unsupported scope: {scope}")
    return ""


def allowed_plist_root(scope: str) -> Path:
    if scope == "user":
        return invoking_home() / "Library/LaunchAgents"
    if scope == "system":
        return Path("/Library/LaunchDaemons")
    return Path("/__invalid_scope__")


def allowed_artifact_roots(scope: str) -> tuple[Path, ...]:
    if scope == "user":
        return (invoking_home() / "Library/LaunchAgents",)
    if scope == "system":
        return SYSTEM_ROOTS
    return ()


def owner_app_allowed(path: Path) -> bool:
    if path.suffix != ".app":
        return False
    roots = (Path("/Applications"), invoking_home() / "Applications")
    return path.parent in roots


def lexists(path: Path) -> bool:
    return os.path.lexists(path)


def regular_file_without_symlinks(path: Path) -> tuple[bool, str | None]:
    try:
        current = path
        while current != current.parent:
            if current.is_symlink():
                return False, f"symlink path component is not allowed: {current}"
            current = current.parent
        mode = path.lstat().st_mode
    except OSError as exc:
        return False, f"cannot inspect artifact: {exc}"
    if not stat.S_ISREG(mode):
        return False, f"artifact is not a regular file: {path}"
    return True, None


def plist_program(plist: dict[str, Any]) -> str | None:
    program = plist.get("Program")
    if isinstance(program, str):
        return program
    arguments = plist.get("ProgramArguments")
    if isinstance(arguments, list) and arguments and isinstance(arguments[0], str):
        return arguments[0]
    return None


def validate_item(item: dict[str, Any]) -> tuple[bool, list[str]]:
    required = {
        "name",
        "scope",
        "label",
        "plist",
        "expected_program",
        "owner_app_absent",
        "artifacts",
    }
    missing = sorted(required - item.keys())
    reasons: list[str] = []
    if missing:
        return False, [f"missing fields: {', '.join(missing)}"]
    if item["scope"] not in {"user", "system"}:
        return False, [f"unsupported scope: {item['scope']!r}"]
    if not isinstance(item["label"], str) or not item["label"].strip():
        reasons.append("label must be a non-empty string")

    try:
        plist_path = Path(item["plist"])
        owner_path = Path(item["owner_app_absent"])
        expected_program = Path(item["expected_program"])
        artifacts = [Path(value) for value in item["artifacts"]]
    except TypeError as exc:
        return False, [f"paths must be strings: {exc}"]

    all_paths = [plist_path, owner_path, expected_program, *artifacts]
    if any(not path.is_absolute() for path in all_paths):
        reasons.append("all manifest paths must be absolute")
    if any(".." in path.parts for path in all_paths):
        reasons.append("manifest paths must not contain '..' components")
    if plist_path.parent != allowed_plist_root(item["scope"]):
        reasons.append(f"plist is outside the allowed {item['scope']} launchd directory")
    if not artifacts:
        reasons.append("artifacts must be a non-empty list")
    if len(set(artifacts)) != len(artifacts):
        reasons.append("artifacts must not contain duplicates")
    if plist_path not in artifacts:
        reasons.append("plist must also appear in artifacts")
    roots = allowed_artifact_roots(item["scope"])
    if any(path.parent not in roots for path in artifacts):
        reasons.append(f"an artifact is outside the allowed {item['scope']} directories")
    if not owner_app_allowed(owner_path):
        reasons.append("owner_app_absent must be an .app under /Applications or ~/Applications")
    if lexists(owner_path):
        reasons.append(f"owner application still exists: {owner_path}")

    for artifact in artifacts:
        if not lexists(artifact):
            reasons.append(f"artifact is already absent: {artifact}")
            continue
        valid_file, file_reason = regular_file_without_symlinks(artifact)
        if not valid_file and file_reason:
            reasons.append(file_reason)

    if lexists(plist_path) and plist_path.is_file() and not plist_path.is_symlink():
        try:
            with plist_path.open("rb") as handle:
                plist = plistlib.load(handle)
            if plist.get("Label") != item["label"]:
                reasons.append(
                    f"label mismatch: expected {item['label']!r}, found {plist.get('Label')!r}"
                )
            actual_program = plist_program(plist)
            if actual_program != str(expected_program):
                reasons.append(
                    f"program mismatch: expected {str(expected_program)!r}, found {actual_program!r}"
                )
        except (OSError, plistlib.InvalidFileException) as exc:
            reasons.append(f"cannot parse plist: {exc}")
    return not reasons, reasons


def ensure_safe_backup_base(base: Path) -> Path:
    expanded = base.expanduser()
    if not expanded.is_absolute():
        fail("backup directory must be absolute")
    if ".." in expanded.parts:
        fail("backup directory must not contain '..' components")
    current = expanded
    existing: list[Path] = []
    while not lexists(current):
        if current == current.parent:
            break
        current = current.parent
    while True:
        existing.append(current)
        if current == current.parent:
            break
        current = current.parent
    for component in existing:
        if component.is_symlink():
            fail(f"backup path contains a symlink: {component}")
    expanded.mkdir(parents=True, exist_ok=True)
    if not expanded.is_dir():
        fail(f"backup path is not a directory: {expanded}")
    resolved = expanded.resolve(strict=True)
    if resolved != expanded:
        fail("backup directory must not resolve through a symlink")
    return resolved


def backup_path(root: Path, original: Path) -> Path:
    return root / "files" / original.as_posix().lstrip("/")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path: Path) -> dict[str, int]:
    metadata = path.lstat()
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "size": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
    }


def parse_manifest(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read manifest: {exc}")
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items:
        fail("manifest must contain a non-empty items list")
    if not all(isinstance(item, dict) for item in items):
        fail("every manifest item must be an object")
    return items


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit exact orphan launchd targets; apply only after a verified dry run."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--confirm", metavar="PHRASE")
    args = parser.parse_args()

    items = parse_manifest(args.manifest)
    results = []
    for item in items:
        valid, reasons = validate_item(item)
        results.append((item, valid, reasons))
        print(f"{'VERIFIED' if valid else 'REFUSED'}: {item.get('name', '<unnamed>')}")
        for reason in reasons:
            print(f"  - {reason}")
    if not all(valid for _, valid, _ in results):
        print("No changes made because one or more items failed validation.", file=sys.stderr)
        return 2
    if not args.apply:
        print("Dry run only; no changes made.")
        return 0
    if args.confirm != CONFIRMATION:
        fail(f"--confirm {CONFIRMATION} is required with --apply")
    if args.backup_dir is None:
        fail("--backup-dir is required with --apply")
    if any(item["scope"] == "system" for item in items) and os.geteuid() != 0:
        fail("system-scoped items require running the apply command with sudo")

    backup_base = ensure_safe_backup_base(args.backup_dir)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S%z")
    backup_root = backup_base / f"orphan-services-{stamp}"
    backup_root.mkdir(mode=0o700)

    report: dict[str, Any] = {"created_at": dt.datetime.now().astimezone().isoformat(), "files": []}
    for item, _, _ in results:
        for raw_path in item["artifacts"]:
            original = Path(raw_path)
            identity = file_identity(original)
            original_hash = sha256(original)
            destination = backup_path(backup_root, original)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, destination, follow_symlinks=False)
            backup_hash = sha256(destination)
            if backup_hash != original_hash:
                fail(f"backup hash mismatch for {original}")
            report["files"].append(
                {
                    "original": str(original),
                    "backup": str(destination.relative_to(backup_root)),
                    "sha256": backup_hash,
                    "identity": identity,
                }
            )
    (backup_root / "backup-manifest.json").write_text(json.dumps(report, indent=2) + "\n")

    for record in report["files"]:
        original = Path(record["original"])
        valid_file, reason = regular_file_without_symlinks(original)
        if not valid_file:
            fail(reason or f"artifact changed before deletion: {original}")
        if file_identity(original) != record["identity"] or sha256(original) != record["sha256"]:
            fail(f"artifact changed after backup; refusing deletion: {original}")

    for item, _, _ in results:
        service = f"{launch_domain(item['scope'])}/{item['label']}"
        completed = subprocess.run(
            ["launchctl", "bootout", service],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"BOOTOUT: {service} (exit {completed.returncode})")
    for item, _, _ in results:
        for raw_path in item["artifacts"]:
            original = Path(raw_path)
            original.unlink()
            print(f"REMOVED: {original}")

    print(f"BACKUP: {backup_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
