# JRE Bank Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Banks:JRE Bank`

## Credentials

Secret question is required. You MUST use `agent-browser --headed` and ask the user to log in manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://sfes.rakuten-bank.co.jp/MS/main/RbS?CID=M_START&CMD=LOGIN&BAAS_CODE=JRE`
4. Ask user to log in manually (合言葉認証 required)
5. Click "入出金明細" tab, then click "以前のお取引"
6. `agent-browser eval "document.querySelector('body').innerText"` to get transaction data
7. Extract the transaction section from the text (between the header row and the CSV download section)
8. Copy RAW_DATA into `tmp/jre_bank_import_YYYYMMDD.py`
9. Run `python3 tmp/jre_bank_import_YYYYMMDD.py review` to show review table
10. User reviews and specifies manual overrides by ID
11. Run `python3 tmp/jre_bank_import_YYYYMMDD.py sql > tmp/import_jre_bank.sql` to generate SQL
12. Execute SQL to insert transactions

## Script Template

- `scripts/jre_bank_import.py`

## Browser Data Format

Text extracted via `eval "document.querySelector('body').innerText"` from the 入出金明細 page.

Transactions are grouped by year-month headers, with each transaction spanning 4 lines: date, amount, balance, description.

Example:
```
2026年02月
02/04
-6,701
123,456
カ）ヒ゛ユ－カ－ト゛
2026年01月
01/26
-100,000
130,157
住信ＳＢＩネット銀行　ブドウ支店　普通預金　150...
01/23
200,000
230,157
給与　アマゾンウエブサ－ビスジヤパン（ド
09/30
483
30,157
預金利息
```

Notes:
- Year-month header format: `YYYY年MM月`
- Date format: `MM/DD`
- Amount has commas and may be negative (e.g., `-6,701`, `200,000`)
- Balance line follows amount (skip when parsing)
- Description is on the line after balance

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| カ）ヒ゛ユ－カ－ト゛ | Liabilities:Credit Card:LUMINE CARD | NULL |
| 給与 | Income:Salary | NULL |
| 住信ＳＢＩネット銀行 | Assets:JPY - Current Assets:Banks:d NEOBANK | NULL |
| 預金利息 | Income:Interest Income | NULL |

If a transaction does not match any pattern, ask the user.

## Script Input Format

Same as Browser Data Format. Paste the transaction section directly.

Parsing rules:
- Lines matching `YYYY年MM月` set the current year
- Lines matching `MM/DD` start a new transaction
- Next line is amount (remove commas)
- Next line is balance (skip)
- Next line is description

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Transaction description from statement
- Transfer: Target account
- Increase/Decrease: Amount

## Notes

- The 入出金明細 page shows all transactions without pagination
- CSV/PDF download is also available but browser text extraction is simpler
- All descriptions are set to NULL; the raw description is shown in the review table for reference
