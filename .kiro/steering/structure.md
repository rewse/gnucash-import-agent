# Project Structure

```
.
├── scripts/                        # Import scripts
├── tmp/                            # Temporary scripts
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

- Temporary scripts go in `tmp/`
- Each source has a corresponding import script in `scripts/` (e.g., `suica_import.py`) and a reference file in `references/accounts/` (e.g., `suica.md`)
