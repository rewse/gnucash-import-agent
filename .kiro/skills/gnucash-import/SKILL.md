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
6. For credit cards: register the payment (debit) transaction from the payment account to the credit card account for each billing statement imported
7. For credit cards: also import unconfirmed transactions from the current billing cycle

Rules:
- Description must be in English (e.g., merchant name)
- If you cannot determine how to map a transaction (account, description, etc.), you MUST ask the user instead of guessing
- You MUST check for duplicates before inserting: if a transaction with the same date and amount already exists, you MUST compare the statement details (description, transaction type, etc.) to determine if it's a duplicate or a separate transaction with the same amount
- Temporary scripts should be saved in `tmp/` directory
- Add separator lines between different dates in review table for readability

### Credit Card: Billing Total Check

For credit cards, check if a billing statement has already been fully imported by looking for the payment transaction:

```sql
SELECT t.post_date::date, t.description, s.value_num
FROM transactions t
JOIN splits s ON t.guid = s.tx_guid
JOIN accounts a ON s.account_guid = a.guid
WHERE a.name = '{account_name}'
AND s.value_num > 0
AND to_char(t.post_date, 'YYYY-MM') = '{YYYY-MM}'
AND s.value_num = {total_amount};
```

Replace `{account_name}` with the credit card account name, `{YYYY-MM}` with the payment month. If this returns a row, the billing statement is already fully imported.

### Credit Card: Duplicate Detection

For statements where the billing total is NOT in GnuCash, you MUST check each transaction individually:

1. Query existing transactions for the statement's date range:
```sql
SELECT t.post_date::date, s.value_num, COUNT(*) as cnt
FROM transactions t
JOIN splits s ON t.guid = s.tx_guid
JOIN accounts a ON s.account_guid = a.guid
WHERE a.name = '{account_name}'
AND s.value_num < 0
AND t.post_date::date BETWEEN '{start_date}' AND '{end_date}'
GROUP BY t.post_date::date, s.value_num
ORDER BY t.post_date::date;
```

2. For each (date, amount) pair in the statement, count how many times it appears
3. Compare with the count from GnuCash
4. If the statement has more occurrences than GnuCash → the difference is new transactions to import
5. If counts match → already imported, skip

### Credit Card: Current Statement (Unconfirmed)

The current month's statement may show unconfirmed transactions. These transactions are still accumulating and may change. You SHOULD still import them but be aware that re-checking will be needed in the next import cycle.

## New Source Workflow

Add a new financial source (bank, credit card, prepaid card, etc.) to the import system.

1. Gather account information from user (see Information Checklist below)
2. Create reference file from template: [references/templates/reference-template.md](references/templates/reference-template.md)
3. Ask user to review the reference file before proceeding
4. Create import script from template: [references/templates/script-template.py](references/templates/script-template.py)
5. Register the new source under "Supported Sources" and "Project Structure" below

### Information Checklist

Gather from user before creating files. Ask incrementally, not all at once.

Essential:
- Source name (e.g., "Mobile Suica", "Revolut")
- GnuCash account path (infer from [account-guid-cache.json](references/account-guid-cache.json))
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
- Credit card numbers in reference files: the first 6 digits (BIN) MAY be shown, but the last 4 digits MUST be masked (e.g., `4980-01**-****-****`)

## Supported Sources

- Amazon MasterCard Gold - See [references/accounts/amazon-mastercard-gold.md](references/accounts/amazon-mastercard-gold.md)
- Amazon Gift Certificate - See [references/accounts/amazon-gc.md](references/accounts/amazon-gc.md)
- Amazon Point - See [references/accounts/amazon-point.md](references/accounts/amazon-point.md)
- ANA Mileage Club - See [references/accounts/ana-mileage-club.md](references/accounts/ana-mileage-club.md)
- ANA SKY Coin - See [references/accounts/ana-sky-coin.md](references/accounts/ana-sky-coin.md)
- ANA Super Flyers Gold Card - See [references/accounts/ana-super-flyers-gold-card.md](references/accounts/ana-super-flyers-gold-card.md)
- Bic Point - See [references/accounts/bic-point.md](references/accounts/bic-point.md)
- d NEOBANK - See [references/accounts/d-neobank.md](references/accounts/d-neobank.md)
- GOLD POINT CARD + - See [references/accounts/gold-point-card-plus.md](references/accounts/gold-point-card-plus.md)
- Hapitas - See [references/accounts/hapitas.md](references/accounts/hapitas.md)
- IHG Rewards Club - See [references/accounts/ihg-rewards-club.md](references/accounts/ihg-rewards-club.md)
- Marriott Rewards - See [references/accounts/marriott-rewards.md](references/accounts/marriott-rewards.md)
- Ponta - See [references/accounts/ponta.md](references/accounts/ponta.md)
- JRE Bank - See [references/accounts/jre-bank.md](references/accounts/jre-bank.md)
- LUMINE CARD - See [references/accounts/lumine-card.md](references/accounts/lumine-card.md)
- JRE Point - See [references/accounts/jre-point.md](references/accounts/jre-point.md)
- Mobile PASMO - See [references/accounts/pasmo.md](references/accounts/pasmo.md)
- Mobile Suica - See [references/accounts/suica.md](references/accounts/suica.md)
- PayPay Card JCB - See [references/accounts/paypay-card-jcb.md](references/accounts/paypay-card-jcb.md)
- Revolut - See [references/accounts/revolut.md](references/accounts/revolut.md)
- SBI Securities - See [references/accounts/sbi-securities.md](references/accounts/sbi-securities.md)
- SBI Shinsei Bank - See [references/accounts/sbi-shinsei-bank.md](references/accounts/sbi-shinsei-bank.md)
- Rakuten Super Point - See [references/accounts/rakuten-super-point.md](references/accounts/rakuten-super-point.md)
- Starbucks - See [references/accounts/starbucks.md](references/accounts/starbucks.md)
- V Point - See [references/accounts/v-point.md](references/accounts/v-point.md)
- World of Hyatt - See [references/accounts/world-of-hyatt.md](references/accounts/world-of-hyatt.md)
- Yodobashi Gold Point - See [references/accounts/yodobashi-gold-point.md](references/accounts/yodobashi-gold-point.md)

## GnuCash Schema

See [references/gnucash-schema.md](references/gnucash-schema.md) for:
- Table structures (transactions, splits, accounts)
- GUID generation
- Numeric value handling
- Common queries

## Account List

See [references/account-guid-cache.json](references/account-guid-cache.json) for account paths and GUIDs.

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
" | python3 -c "import json,sys; d=json.load(sys.stdin); d['accounts']=dict(sorted(d['accounts'].items())); json.dump(d,sys.stdout,indent=4)" > .kiro/skills/gnucash-import/references/account-guid-cache.json
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

## Notes

- 住信SBIネット銀行, ドコモSMTBネット銀行, and "d NEOBANK" refer to the same bank
