# Project Structure

```
.
├── scripts/                        # Import scripts
├── tmp/                            # Temporary scripts and data
└── .kiro/
    ├── agents/                     # Custom agent configurations
    ├── skills/
    │   └── gnucash-import/         # Statement import skill
    │       ├── SKILL.md
    │       └── references/
    │           ├── accounts/       # Per-source reference files
    │           ├── templates/      # Templates for new sources
    │           │   ├── reference-template.md
    │           │   └── script-template.py
    │           ├── account-guid-cache.json
    │           ├── email-lookup.md
    │           ├── gnucash-schema.md
    │           └── personal.json
    └── steering/                   # Steering rules

```

## Conventions

- Temporary scripts, generated SQL, and downloaded data go in `tmp/`
- Every file in `tmp/` is named `{source_slug}_{purpose}_YYYYMMDD.{ext}` (e.g. `sony_bank_import_20260814.py`, `sony_bank_import_20260814.sql`, `sony_bank_statement_20260814_jpy.csv`) so that imports for different sources can run concurrently without overwriting each other
- Each source has a corresponding import script in `scripts/` (e.g., `suica_import.py`) and a reference file in `references/accounts/` (e.g., `suica.md`)
