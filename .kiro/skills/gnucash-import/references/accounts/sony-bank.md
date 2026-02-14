# Sony Bank Statement Import

## GnuCash Account

- JPY: `Assets:JPY - Current Assets:Banks:Sony Bank`
- USD: `Assets:USD - Current Assets:Banks:Sony Bank`

## Credentials

Manual login required. You MUST use `agent-browser --headed` and ask the user to log in manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://sonybank.jp/pages/da/daya010a/?lang=ja`
4. Ask user to log in manually
5. Click "通帳" button on the dashboard
6. Click "普通預金取引履歴" link
7. Select currency from the "通貨" dropdown (円 / 米ドル / ユーロ / 豪ドル)
8. Set date range using the 表示期間 fields (year/month/day inputs)
9. Click "表示" button
10. Click "CSVのダウンロード" to download CSV file
11. Convert CSV from Shift-JIS to UTF-8: `iconv -f SHIFT_JIS -t UTF-8 FutsuRireki.csv`
12. Copy converted CSV content into `tmp/sony_bank_import_YYYYMMDD.py` RAW_DATA
13. Run `python3 tmp/sony_bank_import_YYYYMMDD.py review` to show review table
14. User reviews and specifies manual overrides by ID
15. Run `python3 tmp/sony_bank_import_YYYYMMDD.py sql > tmp/import_sony_bank.sql` to generate SQL
16. Execute SQL to insert transactions
17. Repeat steps 7-16 for each currency as needed

## Script Template

- `scripts/sony_bank_import.py`

## Browser Data Format

CSV file downloaded from the 普通預金取引履歴 page. Encoding is Shift-JIS; convert to UTF-8 before use.

JPY CSV (7 columns):
```
"取引日","摘要","参考情報","通貨","預入額","引出額","差引残高"
"2025年2月17日","決算お利息","","JPY","2.000000","","354.000000"
"2025年7月19日","振込 シバタ　タツノリ","","JPY","100000.000000","","100354.000000"
"2025年7月19日","カード再発行手数料（税込）","","JPY","","1650.000000","98704.000000"
```

USD CSV (8 columns, with exchange rate):
```
"取引日","摘要","参考情報","通貨","預入額","引出額","差引残高","為替レート"
"2025年7月23日","円普通預金より振替","","USD","204.060000","","204.060000","147.010000"
"2025年8月19日","Visaデビット 01　313056　ＵＳＣＵＳＴＯＭＳ　ＴＲＵＳＴＥＤＴＲＡＶＥＬＥＲ","","USD","","120.000000","286.860000",""
```

Notes:
- Date format: `YYYY年M月DD日`
- Amount format: decimal with 6 decimal places (e.g., `100000.000000` for JPY, `204.060000` for USD)
- Empty string means no amount
- 預入額 filled = deposit (positive); 引出額 filled = withdrawal (negative)
- USD CSV has an extra 為替レート column (exchange rate at time of transaction; empty for debit purchases)
- Downloaded filename is always `FutsuRireki.csv`

## Conversion Rules

### Transaction Types (JPY)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 決算お利息 / 決算利息 | Income:Interest Income | NULL |
| 振込 + シバタ | Assets:JPY - Current Assets:Banks:MUFG Bank | NULL |
| 外貨普通預金（米ドル）への振替 / へ振替 / へ振替（積立購入） | Assets:USD - Current Assets:Banks:Sony Bank | NULL |
| 外貨普通預金（米ドル）より振替 | Assets:USD - Current Assets:Banks:Sony Bank | NULL |
| デビツトカイガイリヨウキヤツシユバツク | Income:Cash Back | NULL |
| カイガイジムテスウリヨウキヤツシユバツク | Income:Cash Back | NULL |

### Transaction Types (USD)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 決算利息 | Income:Interest Income | NULL |
| 円普通預金より振替 / より振替（デビット01） / より振替（積立購入） | Assets:JPY - Current Assets:Banks:Sony Bank | NULL |
| 円普通預金へ振替 | Assets:JPY - Current Assets:Banks:Sony Bank | NULL |

If a transaction does not match any pattern, ask the user.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

UTF-8 converted CSV content (without header row). Paste the data rows directly.

Parsing rules:
- Split by comma, respecting quoted fields
- Field 0: date (`YYYY年M月DD日`) — parse year, month, day
- Field 1: description (摘要)
- Field 3: currency code (`JPY` or `USD`)
- Field 4: deposit amount (預入額); empty = 0
- Field 5: withdrawal amount (引出額); empty = 0
- Amount = deposit - withdrawal (parse as float, then convert: JPY → int, USD → float with 2 decimals)
- Skip the header row if present

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Transaction description from statement
- Transfer: Target account
- Increase/Decrease: Amount (¥ for JPY, $ for USD)

## Notes

- Currency dropdown options: 円, 米ドル, ユーロ, 豪ドル
- Run the script once per currency (JPY and USD separately)
- All descriptions are set to NULL; the raw description is shown in the review table for reference
- Visa Debit transactions show merchant name in full-width characters
