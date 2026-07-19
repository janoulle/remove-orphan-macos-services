# Contributing

Contributions are welcome when they preserve the project's fail-closed safety model.

## Before opening a pull request

1. Open an issue for behavior changes, new deletion surfaces, or expanded path allowlists.
2. Keep manifests machine-specific and out of the repository.
3. Add tests for every validation or deletion-path change.
4. Reconcile distributable changes with the canonical source and run the mirror-sync check described in [MIRRORING.md](MIRRORING.md).
5. Run:

   ```bash
   python3 scripts/test_remove_orphan_services.py -v
   python3 -m unittest discover -s tests -v
   python3 -m py_compile scripts/remove_orphan_services.py scripts/sync_from_canonical.py
   ```

6. Explain the threat model, failure behavior, recovery path, and macOS versions tested.

## Safety invariants

Pull requests must not:

- infer deletion targets from names alone;
- introduce recursive deletion;
- follow symlinks;
- bypass backup-before-delete behavior;
- silently expand eligible filesystem roots;
- delete user data, logs, certificates, receipts, or Background Task Management databases;
- weaken dry-run or explicit-confirmation requirements.

## Pull request descriptions

Use **What**, **Why**, **How**, and **How I validated it** sections. Disclose untested paths and compatibility risks directly.

By contributing, you agree that your contribution is licensed under Apache License 2.0.
