# Project Guidelines

This repository provides an agent skill and source-specific Python scripts for importing online financial statements into a GnuCash PostgreSQL database. Load the `gnucash-import` skill and follow it for imports, transaction review, duplicate detection, account mapping, database operations, and adding a source.

## Technology

- Use Python 3 and the Python standard library for import scripts. Do not add third-party Python packages.
- Use `agent-browser` for browser automation.
- Use the 1Password CLI (`op`) to retrieve PostgreSQL credentials. Do not store credentials in the repository.

## Conventions

- Edit the skill only under `.agents/skills/gnucash-import/`. `.claude/skills/gnucash-import` and `.kiro/skills/gnucash-import` are symlinks to it; do not replace them with copies.
- Keep one import script in `scripts/` and one account reference in `.agents/skills/gnucash-import/references/accounts/` for each supported source. Name scripts with snake_case and references with kebab-case, for example `scripts/amazon_gc_import.py` and `references/accounts/amazon-gc.md`.
- Support `review` and `sql` commands in every import script.
- Keep import scripts runnable after copying them to the run's temporary directory; resolve repository resources through the `GNUCASH_IMPORT_ROOT` and `PROJECT_ROOT` pattern used by the script template.

## Documentation

- Structure account references with `Accounts`, `Access`, `Statement Data`, `Mapping`, and `Source-specific Rules` sections in that order.
- Keep shared workflows in `SKILL.md`; account references should contain only source-specific behavior.
- Use format-preserving dummy values for statement examples. Do not include real names, transaction amounts, account identifiers, or other personal data in tracked files.

## Personal Settings

- Store personal names, locations, account mappings, transaction rules, and user-confirmed source-stream import cutoffs only in `.agents/skills/gnucash-import/references/personal.json`.
- Keep `personal.json` untracked with file mode `0600`, and document its schema with dummy values in `personal.example.json`.
- Do not hardcode personal cutoff dates in scripts or account references, and do not infer them from transaction history or the current year.
- Do not print personal settings in logs, reports, tests, or review artifacts.

## Validation

- Before pushing, run `uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files` and `python3 -m unittest discover -s tests`, and commit any files the hooks reformat. Stage new files first, because `--all-files` skips untracked files. CI runs the same hooks and tests, and `core.hooksPath` points at git-defender, so `pre-commit install` cannot run them at commit time.
- Run `python3 -m unittest discover -s tests -v` after changing import behavior.
- Run `python3 -m compileall -q scripts .agents/skills/gnucash-import/scripts` after changing Python files.
- Run `basedpyright scripts .agents/skills/gnucash-import/scripts` and require zero errors. Existing warnings need not be resolved unless they relate to the change.
- Run `git diff --check` before finishing.
