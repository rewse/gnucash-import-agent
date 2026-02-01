# Revolut Statement Import

## Statement URL

https://app.revolut.com/start

## Credentials

CAPTCHA is required. You MUST use `agent-browser --headed` and ask the user to login manually.

## GnuCash Account

`Assets:JPY - Current Assets:Prepaid:Revolut`

## Import Workflow

1. Check if `accounts.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://app.revolut.com/start`
4. Ask user to login manually (CAPTCHA required)
5. Click "すべて表示" to see full transaction history
6. Click month buttons to expand each month's transactions
7. `agent-browser snapshot -i` to get transaction data
8. Scroll and repeat snapshot to get all transactions
9. Prepare RAW_DATA
10. Copy RAW_DATA into `tmp/revolut_import_YYYYMMDD.py`
11. Run `python3 tmp/revolut_import_YYYYMMDD.py review` to show review table
12. User reviews and specifies manual overrides by ID
13. Run `python3 tmp/revolut_import_YYYYMMDD.py sql > tmp/import_revolut.sql` to generate SQL
14. Execute SQL to insert transactions

## Script Template

- `scripts/revolut_import.py`

## Source Data Structure

Columns from Revolut app:
- Month header: Month (YYYY年M月 or M月 format)
- Merchant: Merchant name or transaction type
- Time: Transaction time (HH:MM format)
- JPY Amount: Amount in JPY (+￥N for income, -￥N for expense)
- USD Amount: Amount in USD (optional, for foreign transactions)

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Merchant name
- Transfer: Target account
- Increase/Decrease: Amount (JPY)

## Data Parsing

Expected RAW_DATA format (from initial home screen, not "すべて表示"):
```
AliExpress 1月3日 15:21 -￥2,060.00 -$12.96
Apple Pay経由でチャージされました 2025年12月26日 14:40 +￥30,000.00
Www.lumesca.com 2025年12月26日 13:40 -￥6,256.00 -$39.99
```

Parsing rules:
- Date format: `YYYY年M月D日` or `M月D日` (year inferred from current date)
- Amount: `-￥N` (expense), `+￥N` (income)
- Skip transactions with `￥0.00` amount
- Skip transactions with `失敗しました` or `取り消されました` status

## Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| Apple Pay経由でチャージされました | Liabilities:Credit Card:Luxury Card Mastercard Titanium | NULL |
| ・・経由でお金が追加されました | Liabilities:Credit Card:Luxury Card Mastercard Titanium (default) | NULL |
| カード配送料 | Expenses:Fees | Revolut |
| AliExpress | Expenses:Groceries (default) | AliExpress |
| PayPal | (lookup email) | PayPal |
| Other merchants | (infer or lookup email) | Merchant name |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Notes

- Multi-currency: Transactions show both JPY and USD amounts; use JPY for GnuCash
- Date is shown only in month header; individual transactions show time only
- Always show review table before inserting to database
- User can specify manual overrides by ID for account and/or description
