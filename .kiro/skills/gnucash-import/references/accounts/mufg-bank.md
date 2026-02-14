# MUFG Bank Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Banks:MUFG Bank`

## Credentials

Manual login required. You MUST use `agent-browser --headed` and ask the user to log in manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://directg.s.bk.mufg.jp/APL/LGP_P_01/PU/LG_0001/LG_0001_PC01`
4. Ask user to log in manually
5. Click "入出金明細" link on the top page
6. Change period filter to cover the desired date range (default is 最近30日間; use 期間指定 for custom range)
7. `agent-browser eval "document.querySelector('body').innerText"` to get transaction data
8. Extract the transaction section from the text (between the header row and the footer)
9. Copy RAW_DATA into `tmp/mufg_bank_import_YYYYMMDD.py`
10. Run `python3 tmp/mufg_bank_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/mufg_bank_import_YYYYMMDD.py sql > tmp/import_mufg_bank.sql` to generate SQL
13. Execute SQL to insert transactions

## Script Template

- `scripts/mufg_bank_import.py`

## Browser Data Format

Text extracted via `eval "document.querySelector('body').innerText"` from the 入出金明細 page.

Tab-separated table with year headers. Each transaction is one tab-separated line followed by a `メモ内容` line.

Example:
```
2025年
2/17		1,000 円	利息　ス－パ－フツウ	50,000 円	
メモ内容

3/9		100,000 円	振込１　シバタ　タツノリ	150,000 円	
メモ内容

4/28	80,000 円		口座振替４　メイジヤスダセイメイ	70,000 円	
メモ内容

7/13		50,000 円	ことら送金　シバタ　タツノリ	120,000 円	
メモ内容

7/13	60,000 円		ＰＥ／ＩＮ　ラクテンソンガイホケン	60,000 円	
メモ内容

8/18		500 円	利息　ス－パ－フツウ	60,500 円	
メモ内容
```

Notes:
- Year header format: `YYYY年`
- Date format: `M/DD`
- Columns (tab-separated): date, お支払い (withdrawal), お預かり (deposit), 取引内容, 残高, メモ編集
- Amount format: `N 円` with commas (e.g., `100,000 円`); empty field means no amount
- Withdrawal column filled = money out (negative); Deposit column filled = money in (positive)
- `メモ内容` line follows each transaction (skip when parsing)
- Period filter defaults to 最近30日間; use 期間指定 with JS to set date inputs (`tx-start-date`, `tx-end-date`)

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 利息 | Income:Interest Income | NULL |
| メイジヤスダセイメイ | Expenses:Insurances:Property Insurances | NULL |
| ラクテンソンガイホケン | Expenses:Insurances:Property Insurances | NULL |
| 振込 + シバタ | Assets:JPY - Current Assets:Banks:d NEOBANK | NULL |
| ことら送金 + シバタ | Assets:JPY - Current Assets:Banks:d NEOBANK | NULL |

If a transaction does not match any pattern, ask the user.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Same as Browser Data Format. Paste the transaction section directly.

Parsing rules:
- Lines matching `YYYY年` set the current year
- Lines matching `M/DD\t...` are transaction lines (tab-separated)
- Split by tab: [date, withdrawal, deposit, description, balance, ...]
- Amount: remove commas, spaces, and `円` suffix; parse as integer
- If withdrawal is non-empty, amount is negative; if deposit is non-empty, amount is positive
- Skip `メモ内容` lines and blank lines

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Transaction description from statement
- Transfer: Target account
- Increase/Decrease: Amount

## Notes

- The 入出金明細 page shows up to 100 transactions per page
- Period filter options: 本日, 最近10日間, 最近30日間, 今月, 前月, 期間指定
- All descriptions are set to NULL; the raw description is shown in the review table for reference
