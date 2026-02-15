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
- Amazon MasterCard Gold
- Amazon Point
- ANA Mileage Club
- ANA SKY Coin
- ANA Super Flyers Gold Card
- Bic Point
- d NEOBANK
- GOLD POINT CARD +
- Hapitas
- IHG Rewards Club
- JRE Bank
- JRE Point
- Marriott Rewards
- Mobile PASMO
- Mobile Suica
- MUFG Bank
- Ponta
- Rakuten Super Point
- Revolut
- SBI Securities
- SBI Shinsei Bank
- Sompo Japan DC Securities
- Sony Bank
- Starbucks
- V Point
- World of Hyatt
- Yodobashi Gold Point

## Usage

- Run `kiro-cli --agent gnucash`
- Chat with the agent

## Project Structure

```
.
├── scripts/                        # Import scripts
│   ├── amazon_gc_import.py         # Amazon Gift Certificate
│   ├── amazon_mastercard_gold_import.py # Amazon MasterCard Gold
│   ├── amazon_point_import.py      # Amazon Point
│   ├── ana_mileage_club_import.py  # ANA Mileage Club
│   ├── ana_sky_coin_import.py      # ANA SKY Coin
│   ├── ana_super_flyers_gold_card_import.py # ANA Super Flyers Gold Card
│   ├── bic_point_import.py         # Bic Point
│   ├── d_neobank_import.py         # d NEOBANK
│   ├── gold_point_card_plus_import.py # GOLD POINT CARD +
│   ├── hapitas_import.py           # Hapitas
│   ├── ihg_rewards_club_import.py  # IHG Rewards Club
│   ├── jre_bank_import.py          # JRE Bank
│   ├── jre_point_import.py         # JRE Point
│   ├── marriott_rewards_import.py  # Marriott Rewards
│   ├── mufg_bank_import.py         # MUFG Bank
│   ├── ponta_import.py             # Ponta
│   ├── rakuten_super_point_import.py # Rakuten Super Point
│   ├── revolut_import.py           # Revolut
│   ├── sbi_securities_import.py     # SBI Securities
│   ├── sbi_shinsei_bank_import.py  # SBI Shinsei Bank
│   ├── sompo_japan_dc_import.py    # Sompo Japan DC Securities
│   ├── sony_bank_import.py         # Sony Bank
│   ├── starbucks_import.py         # Starbucks
│   ├── suica_import.py             # Mobile Suica
│   ├── v_point_import.py           # V Point
│   ├── world_of_hyatt_import.py   # World of Hyatt
│   └── yodobashi_gold_point_import.py # Yodobashi Gold Point
└── .kiro/
    ├── agents/                     # Custom agent configurations
    ├── skills/
    │   └── gnucash-import/         # Statement import skill
    │       ├── SKILL.md
    │       └── references/
    │           ├── accounts/       # Per-source reference files
    │           │   ├── amazon-gc.md
    │           │   ├── amazon-mastercard-gold.md
    │           │   ├── amazon-point.md
    │           │   ├── ana-mileage-club.md
    │           │   ├── ana-sky-coin.md
    │           │   ├── ana-super-flyers-gold-card.md
    │           │   ├── bic-point.md
    │           │   ├── d-neobank.md
│           │   ├── gold-point-card-plus.md
    │           │   ├── hapitas.md
    │           │   ├── ihg-rewards-club.md
    │           │   ├── jre-bank.md
    │           │   ├── jre-point.md
    │           │   ├── marriott_rewards.md
    │           │   ├── mufg-bank.md
    │           │   ├── pasmo.md
    │           │   ├── ponta.md
    │           │   ├── rakuten-super-point.md
    │           │   ├── revolut.md
    │           │   ├── sbi-securities.md
    │           │   ├── sbi-shinsei-bank.md
    │           │   ├── sompo-japan-dc.md
    │           │   ├── sony-bank.md
    │           │   ├── starbucks.md
    │           │   ├── suica.md
    │           │   ├── v-point.md
    │           │   ├── world-of-hyatt.md
    │           │   └── yodobashi-gold-point.md
    │           ├── templates/      # Templates for new sources
    │           │   ├── reference-template.md
    │           │   └── script-template.py
    │           ├── account-guid-cache.json
    │           ├── email-lookup.md
    │           ├── gnucash-schema.md
    │           └── personal.json
    └── steering/                   # Steering rules
```
