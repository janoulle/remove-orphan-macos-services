# Restore procedure

Treat restoration as a privileged change. Inspect `backup-manifest.json` in the timestamped backup directory before copying anything.

1. Verify each backup file's SHA-256 digest against `backup-manifest.json`.
2. Confirm the original owning application has not been reinstalled; prefer its official installer if it has.
3. Copy only the required files to the recorded `original` paths with their preserved metadata. Use administrator privileges only for `/Library` targets.
4. Bootstrap the restored plist into its recorded domain with `launchctl bootstrap` only after inspecting it again.
5. Confirm the service state and application behavior.

Do not restore a helper merely to make a stale Login Items entry reappear. If the application has been reinstalled, use its vendor-supported repair or installer path instead.
