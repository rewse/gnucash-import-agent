---
name: gnucash-account-creator
description: Create new account reference files and import scripts for the gnucash-import skill. Use when adding a new financial source (bank, credit card, prepaid card, etc.) to the GnuCash import system. Triggers on requests like "add a new account", "set up import for X card", or "create a new source for gnucash-import".
---

# GnuCash Account Creator

Create new account reference files and Python import scripts for the gnucash-import skill.

## Workflow

1. Gather account information from user (see Information Checklist below)
2. Create reference file from template: [references/reference-template.md](references/reference-template.md)
3. Create import script from template: [references/script-template.py](references/script-template.py)
4. Register the new source in `.kiro/skills/gnucash-import/SKILL.md` under "Supported Sources"

## Information Checklist

Gather from user before creating files. Ask incrementally, not all at once.

Essential:
- Source name (e.g., "Mobile Suica", "Revolut")
- GnuCash account path (e.g., `Assets:JPY - Current Assets:Prepaid:Suica iPhone`)
- Login URL and authentication method (CAPTCHA, passkey, 1Password)
- Browser data format (ask user to show a sample snapshot)
- Transaction types and their GnuCash account mappings
- Currency (JPY, USD, etc.)

Optional (fill in as discovered):
- Script input format (if different from browser format)
- Business expense detection rules
- Email lookup needs
- Station/merchant-specific mappings

## Output Files

| File | Path |
|------|------|
| Reference | `.kiro/skills/gnucash-import/references/{source-slug}.md` |
| Script | `scripts/{source_slug}_import.py` |

Naming: source-slug uses kebab-case for reference files, snake_case for scripts (e.g., `amazon-gc.md`, `amazon_gc_import.py`).

## Guidelines

- Match the style and structure of existing reference files in `.kiro/skills/gnucash-import/references/`
- Import scripts MUST support both `review` and `sql` subcommands
- All transaction descriptions MUST be in English
- If mapping is ambiguous, the reference file MUST instruct to ask the user
- Reference `email-lookup.md` when the source may need email-based transaction lookup
- Reference the shared gnucash-schema.md for SQL patterns; do not duplicate schema details
