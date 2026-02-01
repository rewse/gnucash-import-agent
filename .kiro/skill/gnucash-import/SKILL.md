---
name: gnucash-import
description: Import online statement data into GnuCash PostgreSQL database. Use when inserting transactions from Mobile Suica, credit cards, or bank statements into GnuCash. Handles browser automation for statement retrieval and SQL generation for transaction insertion.
---

# GnuCash Statement Importer

Import online financial statements into GnuCash PostgreSQL database.

## Workflow

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

## Supported Sources

- Mobile Suica - See [references/suica.md](references/suica.md)

## GnuCash Schema

See [references/gnucash-schema.md](references/gnucash-schema.md) for:
- Table structures (transactions, splits, accounts)
- GUID generation
- Numeric value handling
- Common queries

## Account List

See [references/accounts.json](references/accounts.json) for account paths and GUIDs.

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
" | python3 -m json.tool > .kiro/skill/gnucash-import/references/accounts.json
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
