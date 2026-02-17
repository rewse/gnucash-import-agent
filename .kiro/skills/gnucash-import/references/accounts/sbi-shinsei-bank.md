# SBI Shinsei Bank Statement Import

## GnuCash Account

- JPY Savings: `Assets:JPY - Current Assets:Banks:SBI Shinsei Bank`
- USD Savings: `Assets:USD - Current Assets:Banks:SBI Shinsei Bank`
- SBI Hyper Deposit: `Assets:JPY - Current Assets:Banks:SBI Shinsei Bank:SBI Hyper Deposit`

## Credentials

Manual login required. You MUST use `agent-browser --headed` and ask the user to log in manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://bk.web.sbishinseibank.co.jp/SFC/apps/services/www/SFC/desktopbrowser/default/login?mode=1`
4. Ask user to log in manually
5. Navigate to transaction history for each account type:
   - **JPY Savings**: From top page, click "入出金明細" link under "円普通預金" section
   - **SBI Hyper Deposit**: From top page, click "入出金明細" link under "SBIハイパー預金" section
   - **USD Savings**: Navigate to 外貨預金 → 外貨普通預金 → click "入出金明細" link in the 米ドル row
6. On each transaction history page, click "明細をCSVでダウンロードする" to download CSV
7. Copy CSV content into `tmp/sbi_shinsei_bank_import_YYYYMMDD.py` RAW_DATA
8. Run `python3 tmp/sbi_shinsei_bank_import_YYYYMMDD.py review` to show review table
9. User reviews and specifies manual overrides by ID
10. Run `python3 tmp/sbi_shinsei_bank_import_YYYYMMDD.py sql > tmp/import_sbi_shinsei_bank.sql` to generate SQL
11. Execute SQL to insert transactions
12. Repeat steps 5-11 for each account type as needed

## Script Template

- `scripts/sbi_shinsei_bank_import.py`

## Browser Data Format

Table on the transaction history page with columns: 取引日, 摘要, 出金, 入金, 残高, メモ.

CSV download is available via "明細をCSVでダウンロードする" button. CSV format may differ from the old PowerDirect system.

JPY Savings example (from snapshot):
```
row "2026/02/11 ATM 現金出金（提携取引） 10,000 円 100,000 円":
  - cell "2026/02/11"
  - cell "ATM 現金出金（提携取引）"
  - cell "10,000 円"
  - cell
  - cell "100,000 円"

row "2026/02/01 税引前利息 500 円 110,000 円":
  - cell "2026/02/01"
  - cell "税引前利息"
  - cell
  - cell "500 円"
  - cell "110,000 円"
```

SBI Hyper Deposit example (from snapshot):
```
row "2026/02/02 SBI証券精算 200 円 5,000,000 円":
  - cell "2026/02/02"
  - cell "SBI証券精算"
  - cell
  - cell "200 円"
  - cell "5,000,000 円"

row "2026/01/18 円普通預金 1,000,000 円 4,000,000 円":
  - cell "2026/01/18"
  - cell "円普通預金"
  - cell "1,000,000 円"
  - cell
  - cell "4,000,000 円"
```

USD Savings example (from snapshot):
```
row "2026/01/01 税引前利息 2.00 USD 2.00 USD":
  - cell "2026/01/01"
  - cell "税引前利息"
  - cell "2.00 USD"
  - cell "2.00 USD"

row "2025/11/04 被仕向事務手数料 15.00 USD 500.00 USD":
  - cell "2025/11/04"
  - cell "被仕向事務手数料"
  - cell "15.00 USD"
  - cell "500.00 USD"
```

Notes:
- Date format: `YYYY/MM/DD`
- JPY amounts: comma-separated with ` 円` suffix (e.g., `10,000 円`)
- USD amounts: decimal with ` USD` suffix (e.g., `15.00 USD`)
- 出金 (withdrawal) column filled = money out; 入金 (deposit) column filled = money in
- Empty cell means no amount for that column
- URL cannot be accessed directly; must navigate from the logged-in top page

## Conversion Rules

### Transaction Types (JPY Savings)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| ATM 現金出金（提携取引） | Assets:JPY - Current Assets:Cash | NULL |
| 地方税 | Expenses:Tax:Income Tax | Tokyo |
| 国税 | Expenses:Tax:Income Tax | Japan |
| 税引前利息 | Income:Interest Income | SBI Shinsei Bank |

### Transaction Types (SBI Hyper Deposit)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| SBI証券精算 | Assets:JPY - Current Assets:Securities:SBI Securities | NULL |
| 円普通預金 | Assets:JPY - Current Assets:Banks:SBI Shinsei Bank | NULL |
| 地方税 | Expenses:Tax:Income Tax | Tokyo |
| 国税 | Expenses:Tax:Income Tax | Japan |
| 税引前利息 | Income:Interest Income | SBI Shinsei Bank |

### Transaction Types (USD Savings)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 円普通預金 | Assets:JPY - Current Assets:Banks:SBI Shinsei Bank | NULL |
| 地方税 | Expenses:Tax:Income Tax | Tokyo |
| 国税 | Expenses:Tax:Income Tax | Japan |
| 税引前利息 | Income:Interest Income | SBI Shinsei Bank |
| 被仕向事務手数料 | Expenses:Fees | SBI Shinsei Bank |

If a transaction does not match any pattern, ask the user.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated lines with format: `ACCOUNT_TYPE\tDATE\tDESCRIPTION\tWITHDRAWAL\tDEPOSIT`

- ACCOUNT_TYPE: `JPY`, `HYPER`, or `USD`
- DATE: `YYYY/MM/DD`
- DESCRIPTION: 摘要 text
- WITHDRAWAL: amount (empty if none)
- DEPOSIT: amount (empty if none)
- Amounts are raw numbers without commas or currency suffix

Example:
```
JPY	2026/02/11	ATM 現金出金（提携取引）	10000	
JPY	2026/02/01	税引前利息		500
HYPER	2026/02/02	SBI証券精算		200
USD	2026/01/01	税引前利息		2.00
USD	2025/11/04	被仕向事務手数料	15.00	
```

Parsing rules:
- Split by tab
- Field 0: account type (`JPY`, `HYPER`, `USD`)
- Field 1: date (`YYYY/MM/DD`)
- Field 2: description (摘要)
- Field 3: withdrawal amount (empty = 0)
- Field 4: deposit amount (empty = 0)
- Amount = deposit - withdrawal

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Type: Account type (JPY/HYPER/USD)
- Desc: Transaction description from statement
- Transfer: Target account
- Increase/Decrease: Amount (¥ for JPY/HYPER, $ for USD)

## Notes

- Three separate account types share the same login session
- SBI Hyper Deposit is used for automatic settlement with SBI Securities
- The "明細をCSVでダウンロードする" button is available on each transaction history page
- Transaction history is available from the current day back to the same month two years prior
