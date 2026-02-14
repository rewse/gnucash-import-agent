# Sompo Japan DC Securities Statement Import

## GnuCash Accounts

### Fund Accounts

- `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities:DIAM Japan Stock Index Fund <DC Pension>`
- `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities:Index Fund Global Stock NoHedge (DC)`

### Transfer Account

- `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities`

Buy (掛金): Transfer Account → Fund Account (on settlement date)

## Credentials

- Username: `op://gnucash/Sompo Japan DC Securities/username`
- Password: `op://gnucash/Sompo Japan DC Securities/password`

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.rk.sjdc.co.jp/RKWEB/RkDCMember/Common/JP_D_BFKLogin.aspx`
4. Login with 1Password credentials
5. If password change prompt appears, click 「今はパスワードを変更しない」
6. Click 「取引履歴等の確認」 in the sidebar
7. Click 「取引履歴」
8. Select period (当月を含む12ヶ月) and click 「実行」
9. `agent-browser eval "document.querySelector('body').innerText"` to get transaction data
10. If multiple pages, click 「次へ >>」 and repeat step 9
11. Extract transaction rows from the text
12. Copy RAW_DATA into `tmp/sompo_japan_dc_import_YYYYMMDD.py`
13. Run `python3 tmp/sompo_japan_dc_import_YYYYMMDD.py review` to show review table
14. User reviews and specifies manual overrides by ID
15. Run `python3 tmp/sompo_japan_dc_import_YYYYMMDD.py sql > tmp/import_sompo_japan_dc.sql` to generate SQL
16. Execute SQL to insert transactions

## Script Template

- `scripts/sompo_japan_dc_import.py`

## Browser Data Format

Text extracted via `eval "document.querySelector('body').innerText"` from the 取引履歴 page.

Transaction rows are tab-separated:

```
2026/01/28	2026/01/29	ＤＩＡＭ国内株式インデックス	598	6.4375	10,000	買 掛金
2026/01/28	2026/01/30	インデックス海外株式ヘッジなし	4,599	11.1212	40,000	買 掛金
```

Columns: 約定日, 受渡日, 運用商品名, 数量(口), 約定単価(円/口), 受渡金額(円), 取引区分

Notes:
- Date format: YYYY/MM/DD
- Fund names use full-width characters (shortened on the page)
- Amounts have commas (e.g., 40,000)
- Pagination: 10 rows per page, navigate with 「次へ >>」
- Past 1 year of history available

## Conversion Rules

### Fund Name Mapping

| Browser Name | GnuCash Account |
|-------------|-----------------|
| ＤＩＡＭ国内株式インデックス | ...Sompo Japan DC Securities:DIAM Japan Stock Index Fund <DC Pension> |
| インデックス海外株式ヘッジなし | ...Sompo Japan DC Securities:Index Fund Global Stock NoHedge (DC) |

### Transaction Types

| Pattern | Description |
|---------|-------------|
| 買 掛金 | null |

### Description

All descriptions are set to NULL.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Same as Browser Data Format. Paste the transaction rows directly (tab-separated lines).

Parsing rules:
- Lines matching `YYYY/MM/DD\t` start a new transaction
- Split by tab: trade_date, settlement_date, fund_name, quantity, unit_price, amount, tx_type
- Remove commas from numeric fields

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.) — uses settlement date
- Fund: Fund name (shortened)
- Quantity: Number of units purchased
- Unit Price: Price per unit
- Desc: Transaction description
- Amount: Settlement amount
- Fund Account: Target GnuCash account (shortened)

## Notes

- Transaction history available for past 1 year only
- No CSV download available; use browser text extraction
