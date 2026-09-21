# GnuCash Import for Kiro

A Kiro skill and a collection of Python scripts for importing online financial statements into a GnuCash PostgreSQL database.

The skill guides Kiro through statement retrieval, transaction parsing, account mapping, duplicate detection, review, and SQL generation. Source-specific scripts cover bank accounts, credit cards, prepaid cards, securities, points, and loyalty programs.

## Requirements

- [Kiro CLI](https://kiro.dev/cli/)
- Python 3
- PostgreSQL with a GnuCash database
- [1Password CLI](https://developer.1password.com/docs/cli/) for database credentials
- [agent-browser](https://github.com/vercel-labs/agent-browser) for statement retrieval

Import scripts use only the Python standard library.

## Usage

Start Kiro CLI from the repository root:

```bash
kiro-cli chat
```

Ask Kiro to import a statement or add support for a financial source. The bundled `gnucash-import` skill provides the review and duplicate-detection workflow used before writing to the database.

Source scripts can also be run directly after supplying statement data in the format documented by the matching account reference:

```bash
python3 scripts/<source>_import.py review
python3 scripts/<source>_import.py sql
```

Some scripts provide additional source-specific commands. Run a script without arguments to see its accepted commands.

## Supported Sources

Each supported source has an import script in [`scripts/`](scripts/) and guidance in [`.kiro/skills/gnucash-import/references/accounts/`](.kiro/skills/gnucash-import/references/accounts/). Those directories are the authoritative source list.

## Repository Layout

```text
.
├── AGENTS.md                                  # Project rules for coding agents
├── scripts/                                   # Source-specific import scripts
└── .kiro/
    └── skills/gnucash-import/
        ├── SKILL.md                           # Import workflow
        └── references/
            ├── accounts/                      # Source-specific guidance
            └── templates/                     # New-source templates
```

## License

This project is licensed under the [MIT License](LICENSE).
