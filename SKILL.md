---
name: remove-orphan-macos-services
description: Audit and safely remove verified orphaned macOS launchd services, agents, daemons, and privileged helpers left after an application is uninstalled. Use when Login Items shows removed apps, launchd repeatedly invokes missing executables, or uninstallers leave background-service files behind.
---

# Remove Orphan macOS Services

Use `scripts/remove_orphan_services.py` with a task-specific JSON manifest. Never infer deletion targets from a vendor-name search alone.

## Workflow

1. Inventory `~/Library/LaunchAgents`, `/Library/LaunchAgents`, `/Library/LaunchDaemons`, and `/Library/PrivilegedHelperTools`.
2. Inspect every candidate plist, resolve `Program` or `ProgramArguments[0]`, check launchd state, and confirm the owning `.app` is absent.
3. Exclude Apple-managed components and any item whose owner, purpose, executable, or replacement path remains uncertain.
4. Read [references/MANIFEST.md](references/MANIFEST.md), then create an exact manifest containing only independently verified targets.
5. Run the script without `--apply`. Require every item to report `VERIFIED`; treat `REFUSED` as a stop condition, not an invitation to bypass a guardrail.
6. Tell the user the exact services and files affected, that deletion follows a complete backup, and whether administrator privileges are required. Obtain explicit approval for destructive cleanup and privilege escalation.
7. Apply with `--apply --confirm DELETE-VERIFIED-ORPHANS --backup-dir <absolute-directory>`. Use `sudo` only when verified system-scoped items require it.
8. Verify target absence, launchd state, backup completeness, and unrelated service presence. Follow [references/RESTORE.md](references/RESTORE.md) if rollback is requested.

Read [references/FAQ.md](references/FAQ.md) when explaining orphan criteria, Login Items caching, authorization, backups, or failure behavior.

## Boundaries

- Remove only exact regular files declared in the manifest and accepted by the script.
- Do not remove directories, symlinks, Apple-managed services, application data, preferences, caches, logs, certificates, receipts, or Background Task Management databases.
- Do not use broad name matches, recursive deletion, `sfltool resetbtm`, or application-bundle absence as the only evidence.
- Do not treat a disabled or unloaded service as orphaned without verifying ownership and intended lifecycle.
- Preserve session transcripts and audit logs unless the user separately and explicitly requests their deletion.

## Validate

    python3 -m py_compile scripts/remove_orphan_services.py scripts/test_remove_orphan_services.py
    python3 scripts/test_remove_orphan_services.py -v
    python3 /path/to/skill-creator/scripts/quick_validate.py .
