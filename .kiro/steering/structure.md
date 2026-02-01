# Project Structure

```
.
├── scripts/                    # Import scripts
│   └── *_import.py            # Statement importer
├── tmp/                        # Temporary files
└── .kiro/
    ├── agents/                 # Custom agent configurations
    │   └── gnucash.json        # GnuCash import agent
    ├── skills/                  # Skill definitions
    │   └── gnucash-import/
    │       ├── SKILL.md        # Main skill documentation
    │       └── references/     # Reference docs (accounts, schema, etc.)
    └── steering/               # Steering rules
```

## Conventions

- Temporary scripts go in `tmp/`
