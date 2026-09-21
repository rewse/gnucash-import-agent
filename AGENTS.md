# Project Guidelines

## Purpose

This repository provides a Kiro skill and source-specific Python scripts for importing online financial statements into a GnuCash PostgreSQL database.

## Technology

- Use Python 3 and the Python standard library for import scripts. Do not add third-party Python packages.
- Use `agent-browser` for browser automation.
- Use the 1Password CLI (`op`) to retrieve PostgreSQL credentials. Do not store credentials in the repository.

## Repository Layout

- `.kiro/skills/gnucash-import/`: import workflow and source-specific guidance
- `.kiro/skills/gnucash-import/references/accounts/`: source reference files
- `.kiro/skills/gnucash-import/references/templates/`: templates for new sources
- `scripts/`: reusable source-specific import scripts

## Conventions

- Keep one import script in `scripts/` and one account reference in `.kiro/skills/gnucash-import/references/accounts/` for each supported source.
- Name scripts with snake_case and references with kebab-case, for example `scripts/amazon_gc_import.py` and `references/accounts/amazon-gc.md`.
- Support `review` and `sql` commands in every import script.
- Create a unique workspace for each import run with `work_dir=$(mktemp -d "/tmp/gnucash-import.XXXXXX")`.
- Store all generated SQL, downloaded statements, temporary scripts, and intermediate data in the exact directory returned by `mktemp`.
- Keep import scripts runnable after copying them to the per-run workspace; resolve repository resources through the `GNUCASH_IMPORT_ROOT` and `PROJECT_ROOT` pattern used by the script template.
- Follow `.kiro/skills/gnucash-import/SKILL.md` for transaction review, duplicate detection, account mapping, and database operations.

## Documentation

- Structure account references with `Accounts`, `Access`, `Statement Data`, `Mapping`, and `Source-specific Rules` sections in that order.
- Keep shared workflows in `.kiro/skills/gnucash-import/SKILL.md`; account references should contain only source-specific behavior.
- Use format-preserving dummy values for statement examples. Do not include real names, transaction amounts, account identifiers, or other personal data in tracked files.

## Personal Settings

- Store personal names, locations, account mappings, and transaction rules only in `.kiro/skills/gnucash-import/references/personal.json`.
- Keep `personal.json` untracked with file mode `0600`, and document its schema with dummy values in `personal.example.json`.
- Do not print personal settings in logs, reports, tests, or review artifacts.

## Validation

- Run `python3 -m unittest discover -s tests -v` after changing import behavior.
- Run `python3 -m compileall -q scripts` after changing Python files.
- Run `basedpyright scripts` and require zero errors. Existing warnings need not be resolved unless they relate to the change.
- Run `git diff --check` before finishing.
