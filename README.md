# Remove Orphan macOS Services

A safety-focused Codex skill for auditing and removing launchd agents, daemons, and privileged helpers left behind after a macOS application is uninstalled.

This repository is the curated public mirror of a version-controlled private skill source. Public releases contain only the distributable skill, tests, and community documentation; machine-specific manifests, cleanup evidence, and personal configuration are never mirrored. See [MIRRORING.md](MIRRORING.md).

> [!CAUTION]
> This project can delete privileged system files. A missing application does not, by itself, prove that a background service is orphaned. Always audit first, review the exact manifest, preserve the generated backup, and understand the restore procedure.

## Why this exists

Deleting an application bundle does not necessarily remove helpers installed in `/Library` or launch agents stored in a user's Library. macOS can continue listing those registrations under Login Items, and launchd may continue trying to invoke missing executables.

This skill turns cleanup into an evidence-based workflow. It validates exact plist labels and programs, limits eligible paths, rejects symlinks and directories, performs a mandatory dry run, backs up every target before deletion, and records file hashes for recovery.

## Requirements

- macOS
- Python 3.10 or later
- Codex for skill-driven use; the audit script can also be run directly
- Administrator authorization only when applying system-scoped cleanup

No third-party Python packages are required.

## Install as a Codex skill

Clone this repository into the Codex skills directory:

```bash
git clone https://github.com/janoulle/remove-orphan-macos-services.git \
  ~/.codex/skills/remove-orphan-macos-services
```

Then invoke `$remove-orphan-macos-services` in Codex.

## Safety model

The script refuses an item unless all declared evidence matches. Important guardrails include:

- exact `Label` and executable matching against the plist;
- absent owner application constrained to `/Applications` or `~/Applications`;
- allowlisted launchd and privileged-helper directories;
- rejection of symlinks, directories, missing files, duplicate artifacts, and mixed scopes;
- complete backup of every artifact before the first deletion;
- SHA-256 inventory in `backup-manifest.json`;
- a literal confirmation phrase for apply mode;
- root enforcement for system-scoped cleanup.

It deliberately does not delete caches, preferences, logs, certificates, receipts, application data, directories, or macOS Background Task Management databases.

## Direct script usage

Read [the manifest reference](references/MANIFEST.md), create a machine-specific manifest outside the repository, and run a dry audit:

```bash
python3 scripts/remove_orphan_services.py /absolute/path/to/manifest.json
```

Only when every item reports `VERIFIED`, apply with an absolute backup directory:

```bash
sudo python3 scripts/remove_orphan_services.py /absolute/path/to/manifest.json \
  --apply \
  --confirm DELETE-VERIFIED-ORPHANS \
  --backup-dir /absolute/path/to/backups
```

Omit `sudo` when the manifest contains only user-scoped items. Review [the restore procedure](references/RESTORE.md) before deleting the backup.

## Validation

```bash
python3 scripts/test_remove_orphan_services.py -v
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/remove_orphan_services.py scripts/sync_from_canonical.py
```

GitHub Actions runs the test suite on macOS with supported Python versions.

## Frequently asked questions

See [FAQ.md](FAQ.md) for orphan-detection criteria, Login Items caching, administrator authorization, backups, and failure behavior.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes. Report vulnerabilities according to [SECURITY.md](SECURITY.md), not through a public issue.

Accepted public changes are reconciled into the canonical source before the mirror is refreshed. The mirror-sync check must pass before release.

## License

Licensed under the [Apache License 2.0](LICENSE).
