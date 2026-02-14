---
name: gnucash-import
description: Import online statement data into GnuCash PostgreSQL database. Use when inserting transactions from Mobile Suica, credit cards, or bank statements into GnuCash. Also use when adding a new financial source (bank, credit card, prepaid card, etc.) to the import system. Triggers on "add a new account", "set up import for X card", or "create a new source".
---

# GnuCash Statement Importer

Import online financial statements into GnuCash PostgreSQL database.

## Import Workflow

1. Retrieve statement data via browser automation
2. Parse transaction data
3. Map to GnuCash accounts
4. Present all transactions to user for review before inserting
5. Generate and execute INSERT statements
6. Add learnings from user interactions to this skill

Rules:
- Description must be in English (e.g., merchant name)
- If you cannot determine how to map a transaction (account, description, etc.), you MUST ask the user instead of guessing
- You MUST check for duplicates before inserting: if a transaction with the same date and amount already exists, you MUST compare the statement details (description, transaction type, etc.) to determine if it's a duplicate or a separate transaction with the same amount
- Temporary scripts should be saved in `tmp/` directory
- Add separator lines between different dates in review table for readability

## New Source Workflow

Add a new financial source (bank, credit card, prepaid card, etc.) to the import system.

1. Gather account information from user (see Information Checklist below)
2. Create reference file from template: [references/templates/reference-template.md](references/templates/reference-template.md)
3. Create import script from template: [references/templates/script-template.py](references/templates/script-template.py)
4. Register the new source under "Supported Sources" and "Project Structure" below

### Information Checklist

Gather from user before creating files. Ask incrementally, not all at once.

Essential:
- Source name (e.g., "Mobile Suica", "Revolut")
- GnuCash account path (infer from [account-uuid-cache.json](references/account-uuid-cache.json))
- Login URL and authentication method (CAPTCHA, passkey, 1Password)
- Browser data format (ask user to show a sample snapshot)
- Transaction types and their GnuCash account mappings
- Currency (JPY, USD, etc.)

Optional (fill in as discovered):
- Script input format (if different from browser format)
- Business expense detection rules
- Email lookup needs
- Station/merchant-specific mappings

### Output Files

| File | Path |
|------|------|
| Reference | `references/accounts/{source-slug}.md` |
| Script | `scripts/{source_slug}_import.py` |

Naming: source-slug uses kebab-case for reference files, snake_case for scripts (e.g., `amazon-gc.md`, `amazon_gc_import.py`).

### Guidelines

- Match the style and structure of existing reference files in `references/accounts/`
- Import scripts MUST support both `review` and `sql` subcommands
- All transaction descriptions MUST be in English
- If mapping is ambiguous, the reference file MUST instruct to ask the user
- Reference `email-lookup.md` when the source may need email-based transaction lookup
- Reference the shared gnucash-schema.md for SQL patterns; do not duplicate schema details
- Amounts in Browser Data Format examples in reference files MUST be replaced with dummy values to avoid exposing real financial data

## Supported Sources

- Amazon Gift Certificate - See [references/accounts/amazon-gc.md](references/accounts/amazon-gc.md)
- Amazon Point - See [references/accounts/amazon-point.md](references/accounts/amazon-point.md)
- ANA Mileage Club - See [references/accounts/ana-mileage-club.md](references/accounts/ana-mileage-club.md)
- ANA SKY Coin - See [references/accounts/ana-sky-coin.md](references/accounts/ana-sky-coin.md)
- Bic Point - See [references/accounts/bic-point.md](references/accounts/bic-point.md)
- d NEOBANK - See [references/accounts/d-neobank.md](references/accounts/d-neobank.md)
- Hapitas - See [references/accounts/hapitas.md](references/accounts/hapitas.md)
- IHG Rewards Club - See [references/accounts/ihg-rewards-club.md](references/accounts/ihg-rewards-club.md)
- Marriott Rewards - See [references/accounts/marriott-rewards.md](references/accounts/marriott-rewards.md)
- Ponta - See [references/accounts/ponta.md](references/accounts/ponta.md)
- JRE Bank - See [references/accounts/jre-bank.md](references/accounts/jre-bank.md)
- JRE Point - See [references/accounts/jre-point.md](references/accounts/jre-point.md)
- Mobile PASMO - See [references/accounts/pasmo.md](references/accounts/pasmo.md)
- Mobile Suica - See [references/accounts/suica.md](references/accounts/suica.md)
- Revolut - See [references/accounts/revolut.md](references/accounts/revolut.md)
- SBI Securities - See [references/accounts/sbi-securities.md](references/accounts/sbi-securities.md)
- SBI Shinsei Bank - See [references/accounts/sbi-shinsei-bank.md](references/accounts/sbi-shinsei-bank.md)
- Starbucks - See [references/accounts/starbucks.md](references/accounts/starbucks.md)

## GnuCash Schema

See [references/gnucash-schema.md](references/gnucash-schema.md) for:
- Table structures (transactions, splits, accounts)
- GUID generation
- Numeric value handling
- Common queries

## Account List

See [references/account-uuid-cache.json](references/account-uuid-cache.json) for account paths and GUIDs.

This file is in `.gitignore` and should be regenerated if:
- File does not exist
- `updated_at` is older than 1 month

To regenerate:

```bash
DB_HOST=$(op read "op://gnucash/gnucash-db/server")
DB_PORT=$(op read "op://gnucash/gnucash-db/port")
DB_NAME=$(op read "op://gnucash/gnucash-db/database")
DB_USER=$(op read "op://gnucash/gnucash-db/username")
PGPASSWORD=$(op read "op://gnucash/gnucash-db/password") psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -c "
WITH RECURSIVE path_list AS (
   SELECT guid, parent_guid, name, name::text AS path, hidden FROM accounts WHERE parent_guid IS NULL
   UNION ALL
   SELECT c.guid, c.parent_guid, c.name, path || ':' || c.name, c.hidden
   FROM accounts c JOIN path_list p ON p.guid = c.parent_guid
)
SELECT json_build_object(
  'updated_at', NOW(),
  'accounts', (SELECT json_object_agg(path, guid) FROM path_list WHERE path NOT LIKE 'Template Root%' AND hidden = 0)
);
" | python3 -m json.tool > .kiro/skills/gnucash-import/references/account-uuid-cache.json
```

## Check Last Imported Transaction

Replace `{account_name}` with the account name (e.g., 'Amazon Gift Certificate', 'Suica iPhone'):

```sql
SELECT t.post_date::date, t.description, s.value_num as amount
FROM transactions t
JOIN splits s ON t.guid = s.tx_guid
JOIN accounts a ON s.account_guid = a.guid
WHERE a.name = '{account_name}'
ORDER BY t.post_date DESC
LIMIT 50;
```

## Personal Settings

See [references/personal.json](references/personal.json) for personal settings.

This file is in `.gitignore`. If it does not exist, ask the user for the following and create it:
- `nearest_station`: Nearest station name (for business expense detection)
