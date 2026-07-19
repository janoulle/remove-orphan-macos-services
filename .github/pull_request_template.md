## What

Describe the user-visible behavior or maintenance outcome that changes.

## Why

Explain the evidence or risk that motivated the change and why it matters.

## How

Describe the approach, safety boundaries, recovery behavior, and meaningful tradeoffs.

## How I validated it

List the scenarios exercised and their observed results. State untested paths and remaining risk directly.

## Safety checklist

- [ ] The change preserves dry-run-first behavior and explicit confirmation.
- [ ] The change does not broaden filesystem roots silently or follow symlinks.
- [ ] Every deletion candidate is backed up before deletion begins.
- [ ] Tests cover new validation, privilege, deletion, or recovery behavior.
- [ ] The public mirror contains no machine-specific manifests, paths, credentials, logs, or cleanup evidence.
- [ ] The canonical source and public distributable files have been reconciled.
