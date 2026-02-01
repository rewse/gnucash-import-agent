# GnuCash Import Agent

An agent for importing online financial statements into GnuCash PostgreSQL database.

## Overview

Automates the import of transaction data from various online sources (banks, credit cards, prepaid cards, etc.) into GnuCash accounting software. Features include browser automation for statement retrieval, intelligent account mapping, business expense detection, and direct database insertion via SQL.

## Features

- **Browser Automation**: Retrieve statements from online banking portals
- **Transaction Parsing**: Parse and normalize transaction data
- **Account Mapping**: Map transactions to GnuCash accounts with configurable rules
- **Business Expense Detection**: Automatically detect business expenses based on commute patterns
- **Duplicate Detection**: Check for existing transactions before insertion
- **SQL Generation**: Generate INSERT statements for direct database insertion

## Prerequisites

- Python 3
- PostgreSQL (GnuCash backend)
- 1Password CLI (`op`) for credential management
- [agent-browser](https://github.com/vercel-labs/agent-browser) for web automation

## Supported Sources

- Amazon Gift Certificate
- Mobile Suica

## Usage

- Run `kiro-cli --agent gnucash`
- Chat with the agent

## Project Structure

```
.
├── scripts/                    # Import scripts
│   ├── amazon_gc_import.py     # Amazon Gift Certificate statement importer
│   └── suica_import.py         # Mobile Suica statement importer
└── .kiro/
    ├── agents/                 # Custom agent configurations
    ├── skill/                  # Skill definitions
    └── steering/               # Steering rules
```
