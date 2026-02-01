---
name: gnucash-statement-importer
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

See [references/accounts.md](references/accounts.md) for account paths and GUIDs.

This file is in `.gitignore` and should be regenerated if:
- File does not exist
- File is older than 1 month

To regenerate:

```bash
cat > .kiro/skill/gnucash-statement-importer/references/accounts.md << 'EOF'
# GnuCash Account List

Last updated: $(date +%Y-%m-%d)

Hidden accounts are excluded.

Format: `Account Path | GUID`

## All Accounts

EOF
PGPASSWORD=$(op read "op://gnucash/gnucash-db/password") psql -h $(op read "op://gnucash/gnucash-db/server") -p $(op read "op://gnucash/gnucash-db/port") -U $(op read "op://gnucash/gnucash-db/username") -d $(op read "op://gnucash/gnucash-db/database") -t -A -c "
WITH RECURSIVE path_list AS (
   SELECT guid, parent_guid, name, name::text AS path, hidden FROM accounts WHERE parent_guid IS NULL
   UNION ALL
   SELECT c.guid, c.parent_guid, c.name, path || ':' || c.name, c.hidden
   FROM accounts c JOIN path_list p ON p.guid = c.parent_guid
)
SELECT '- ' || path || ' | ' || guid FROM path_list WHERE path NOT LIKE 'Template Root%' AND hidden = 0 ORDER BY path;
" >> .kiro/skill/gnucash-statement-importer/references/accounts.md
```

## Personal Settings

See [references/personal.md](references/personal.md) for personal settings (nearest station, etc.).

This file is in `.gitignore`. If it does not exist, ask the user for the following and create it:
- Nearest station (for business expense detection)
