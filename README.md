# GnuCash Import Agent

An agent skill and a collection of Python scripts for importing online financial statements into a GnuCash PostgreSQL database.

The `gnucash-import` skill guides a coding agent through statement retrieval, transaction parsing, account mapping, duplicate detection, review, and SQL generation. Source-specific scripts cover bank accounts, credit cards, prepaid cards, securities, points, and loyalty programs.

## Requirements

- [1Password CLI](https://developer.1password.com/docs/cli/) for database credentials
- [agent-browser](https://github.com/vercel-labs/agent-browser) for statement retrieval
- The [Amazon RDS global CA bundle](https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem) at `~/.postgresql/rds-global-bundle.pem`, or at the path in `GNUCASH_DB_SSLROOTCERT`, for verified TLS to Aurora PostgreSQL (see the `Database connection` section of the skill)
- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview), [Codex CLI](https://developers.openai.com/codex/cli), or [Kiro CLI](https://kiro.dev/cli/)
- PostgreSQL with a GnuCash database
- Python 3

Import scripts use only the Python standard library.

## Usage

Start the agent from the repository root:

```bash
claude          # Claude Code
codex           # Codex CLI
kiro-cli chat   # Kiro CLI
```

Ask the agent to import a statement or add support for a financial source. The skill lives in `.agents/skills/gnucash-import/`, where Codex reads it directly; `.claude/skills/` and `.kiro/skills/` link to it for Claude Code and Kiro.

Source scripts can also be run directly. Write the statement data to `raw.txt` next to the script, or point `GNUCASH_RAW_DATA` at the file, in the format documented by the matching account reference:

```bash
GNUCASH_RAW_DATA=/path/to/raw.txt python3 scripts/<source>_import.py review
GNUCASH_RAW_DATA=/path/to/raw.txt python3 scripts/<source>_import.py sql
```

Some scripts provide additional source-specific commands. Run a script without arguments to see its accepted commands.

## Supported Sources

Each supported source has an import script in [`scripts/`](scripts/) and guidance in [`.agents/skills/gnucash-import/references/accounts/`](.agents/skills/gnucash-import/references/accounts/). Those directories are the authoritative source list.

## License

This project is licensed under the [MIT License](LICENSE).
