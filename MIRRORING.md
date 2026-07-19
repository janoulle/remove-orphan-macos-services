# Public mirror policy

This repository is a curated public distribution of one reusable skill. The canonical source is maintained in a private, version-controlled agent-configuration repository so multiple LLM harnesses can share the same local skill.

## Publication boundary

The public mirror includes:

- `SKILL.md` and `agents/openai.yaml`;
- generic references and safety documentation;
- the cleanup script and automated tests;
- public CI, issue templates, contribution guidance, security policy, and licensing.

The mirror must never include:

- machine-specific manifests or absolute home-directory paths;
- service inventories, cleanup results, backups, logs, or certificates;
- credentials, tokens, email addresses, browser sessions, or private configuration;
- unrelated skills or repository history from the canonical source.

## Refresh workflow

1. Update and validate the canonical skill first.
2. Run `scripts/sync_from_canonical.py --source /path/to/canonical-skill --check` from this repository.
3. If differences are expected, run the same command with `--apply` and review every changed file.
4. Run the skill validator, unit tests, compile checks, whitespace checks, and privacy scan.
5. Commit and publish only the curated mirror diff.

Public contributions are welcome. Before a public change is released, reconcile it into the canonical source and refresh this mirror so neither copy silently becomes an independent implementation.
