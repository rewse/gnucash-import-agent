# Project Structure

```
.
├── scripts/                        # Import scripts
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

- For each import run, create `work_dir=$(mktemp -d "/tmp/gnucash-import.XXXXXX")` and store all temporary scripts, generated SQL, downloads, and intermediate data in the exact directory returned by `mktemp`; filenames inside it may be simple
- Each source has a corresponding import script in `scripts/` (e.g., `suica_import.py`) and a reference file in `references/accounts/` (e.g., `suica.md`)
