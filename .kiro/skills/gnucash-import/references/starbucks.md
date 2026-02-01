# Starbucks Card Statement Import

## Statement URL

https://sbcard.starbucks.co.jp/card/history

## Credentials

- Username: `op://gnucash/Starbucks/useranem`
- Password: `op://gnucash/Starbucks/password`
- Login URL: https://login.starbucks.co.jp/login

## GnuCash Account

`Assets:JPY - Current Assets:Prepaid:Starbucks`

## Import Workflow

1. Check if `accounts.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser open https://login.starbucks.co.jp/login`
4. Login with 1Password credentials
5. `agent-browser open https://sbcard.starbucks.co.jp/card/history`
6. `agent-browser snapshot` to get transaction data
7. Prepare RAW_DATA
8. Copy RAW_DATA into `tmp/starbucks_import_YYYYMMDD.py`
9. Run `python3 tmp/starbucks_import_YYYYMMDD.py review` to show review table
10. User reviews and specifies manual overrides by ID
11. Run `python3 tmp/starbucks_import_YYYYMMDD.py sql > tmp/import_starbucks.sql` to generate SQL
12. Execute SQL to insert transactions

## Script Template

- `scripts/starbucks_import.py`

## Source Data Structure

Data from browser snapshot (list items):
- Description: Transaction type or store name
- Amount and Date: `¥N YYYY/MM/DD` or `- ¥N YYYY/MM/DD`

Example:
```
オートチャージ
¥2,000 2026/01/27

モバイルオーダー&ペイ
- ¥481 2026/01/27

晴海 トリトンスクエア店
- ¥496 2025/12/19
```

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Type: Charge/Payment
- Desc: Transaction description
- Transfer: Target account
- Increase/Decrease: Amount

## Data Parsing

RAW_DATA format (tab-separated):
```
{description}\t{amount}\t{date}
```

Example:
```
オートチャージ	¥2,000	2026/01/27
モバイルオーダー&ペイ	- ¥481	2026/01/27
晴海 トリトンスクエア店	- ¥496	2025/12/19
```

Parsing rules:
- Fields are tab-separated
- Amount: `¥N` (positive = charge), `- ¥N` (negative = payment)
- Date format: YYYY/MM/DD

## Transaction Types

| Pattern | Type | Transfer Account | Description |
|---------|------|------------------|-------------|
| オートチャージ | Charge | Liabilities:Credit Card:ANA Super Flyers Gold Card | null |
| 他社ポイント交換 | Charge | (lookup email) | null |
| モバイルオーダー&ペイ | Payment | Expenses:Foods:Dining | Starbucks |
| {店舗名}店 | Payment | Expenses:Foods:Dining | Starbucks |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Notes

- History shows approximately 4 months of transactions
- No pagination; all history loads on single page
- Amount sign: positive = charge (入金), negative with `- ` prefix = payment (支払い)
