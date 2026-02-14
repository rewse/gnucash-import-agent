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
- Amazon Point
- ANA Mileage Club
- ANA SKY Coin
- Bic Point
- d NEOBANK
- Hapitas
- IHG Rewards Club
- JRE Bank
- JRE Point
- Marriott Rewards
- Mobile PASMO
- Mobile Suica
- MUFG Bank
- Revolut
- SBI Securities
- SBI Shinsei Bank
- Sompo Japan DC Securities
- Sony Bank
- Starbucks

## Usage

- Run `kiro-cli --agent gnucash`
- Chat with the agent

## Project Structure

```
.
├── scripts/                        # Import scripts
│   ├── amazon_gc_import.py         # Amazon Gift Certificate
│   ├── amazon_point_import.py      # Amazon Point
│   ├── ana_mileage_club_import.py  # ANA Mileage Club
│   ├── ana_sky_coin_import.py      # ANA SKY Coin
│   ├── bic_point_import.py         # Bic Point
│   ├── d_neobank_import.py         # d NEOBANK
│   ├── hapitas_import.py           # Hapitas
│   ├── ihg_rewards_club_import.py  # IHG Rewards Club
│   ├── jre_bank_import.py          # JRE Bank
│   ├── jre_point_import.py         # JRE Point
│   ├── marriott_rewards_import.py  # Marriott Rewards
│   ├── mufg_bank_import.py         # MUFG Bank
│   ├── revolut_import.py           # Revolut
│   ├── sbi_securities_import.py     # SBI Securities
│   ├── sbi_shinsei_bank_import.py  # SBI Shinsei Bank
│   ├── sompo_japan_dc_import.py    # Sompo Japan DC Securities
│   ├── sony_bank_import.py         # Sony Bank
│   ├── starbucks_import.py         # Starbucks
│   └── suica_import.py             # Mobile Suica
└── .kiro/
    ├── agents/                     # Custom agent configurations
    ├── skills/
    │   └── gnucash-import/         # Statement import skill
    │       ├── SKILL.md
    │       └── references/
    │           ├── accounts/       # Per-source reference files
    │           │   ├── amazon-gc.md
    │           │   ├── amazon-point.md
    │           │   ├── ana-mileage-club.md
    │           │   ├── ana-sky-coin.md
    │           │   ├── bic-point.md
    │           │   ├── d-neobank.md
    │           │   ├── hapitas.md
    │           │   ├── ihg-rewards-club.md
    │           │   ├── jre-bank.md
    │           │   ├── jre-point.md
    │           │   ├── marriott_rewards.md
    │           │   ├── mufg-bank.md
    │           │   ├── pasmo.md
    │           │   ├── revolut.md
    │           │   ├── sbi-securities.md
    │           │   ├── sbi-shinsei-bank.md
    │           │   ├── sompo-japan-dc.md
    │           │   ├── sony-bank.md
    │           │   ├── starbucks.md
    │           │   └── suica.md
    │           ├── templates/      # Templates for new sources
    │           │   ├── reference-template.md
    │           │   └── script-template.py
    │           ├── account-uuid-cache.json
    │           ├── email-lookup.md
    │           ├── gnucash-schema.md
    │           └── personal.json
    └── steering/                   # Steering rules
```
