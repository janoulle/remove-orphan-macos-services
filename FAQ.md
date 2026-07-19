# Frequently asked questions

## What counts as an orphan service?

An item is a candidate when its owning application is absent and repository evidence ties its exact launchd plist, label, executable, and artifacts to that application. Absence alone is insufficient: shared updaters, enterprise tools, command-line packages, and independently installed helpers may remain intentionally.

## Why does an uninstalled app still appear under Login Items?

macOS discovers background-item registrations and helper files outside `/Applications`. Removing the `.app` bundle does not automatically remove those files. System Settings may also cache display metadata until it is reopened, the user logs out, or the Mac restarts.

## Does a disabled toggle mean the service is safe to delete?

No. Disabled, unloaded, and orphaned describe different conditions. Audit ownership and lifecycle before deletion.

## Why is administrator authorization sometimes required?

Files under `/Library/LaunchDaemons` and `/Library/PrivilegedHelperTools` are normally owned by `root`. User-scoped agents under `~/Library/LaunchAgents` generally do not require administrator privileges.

## Can Touch ID authorize `sudo`?

On supported macOS versions, Apple documents `/etc/pam.d/sudo_local` as the update-persistent configuration surface. This project does not enable or modify that authentication policy.

## Why require a manifest and confirmation phrase?

The manifest makes the deletion boundary reviewable and reproducible. The confirmation phrase prevents an accidental transition from dry-run mode to destructive mode.

## What is backed up?

Every declared artifact is copied before any artifact is deleted. The timestamped backup also contains `backup-manifest.json` with original paths and SHA-256 hashes.

## What if one item fails validation?

The script refuses the entire manifest and makes no changes. Fix the evidence or remove an uncertain item from the proposed cleanup; never weaken a guardrail to force acceptance.

## What if backup creation fails?

Deletion does not begin until every artifact has been copied and its hash recorded. A backup failure stops the process.

## Does this remove caches or application data?

No. It intentionally excludes directories, preferences, caches, logs, certificates, receipts, application data, and Background Task Management databases.

## How do I restore a removed service?

Follow [references/RESTORE.md](references/RESTORE.md). Prefer reinstalling or repairing the owning application through its official installer when available.

## Is this an Apple product?

No. This is an independent open-source project and is not affiliated with or endorsed by Apple Inc.
