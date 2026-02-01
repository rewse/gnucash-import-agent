# Project Structure

```
.
├── scripts/                    # Import scripts
│   └── suica_import.py         # Mobile Suica statement importer
├── tmp/                        # Temporary files (gitignored)
└── .kiro/
    ├── agents/                 # Custom agent configurations
    │   └── gnucash.json        # GnuCash import agent
    ├── skill/                  # Skill definitions
    │   └── gnucash-statement-importer/
    │       ├── SKILL.md        # Main skill documentation
    │       └── references/     # Reference docs (accounts, schema, etc.)
    └── steering/               # Steering rules
        └── postgresql.md       # Database connection info
```

## Key Files

- `scripts/suica_import.py` - Main import script with hardcoded account GUIDs and transaction parsing logic
- `.kiro/skill/gnucash-statement-importer/SKILL.md` - Workflow documentation and supported sources
- `.kiro/skill/gnucash-statement-importer/references/` - Account lists and schema docs (some gitignored)

## Conventions

- Temporary scripts go in `tmp/`
