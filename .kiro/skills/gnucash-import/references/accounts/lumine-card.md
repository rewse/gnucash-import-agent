# LUMINE CARD Statement Import

## GnuCash Account

- Card: `Liabilities:Credit Card:LUMINE CARD`
- Payment debit: `Assets:JPY - Current Assets:Banks:JRE Bank`
- Payment date: 4th (or next business day if 4th is a holiday)

## Credentials

- Username: `op://gnucash/VIEWs NET/username`
- Password: `op://gnucash/VIEWs NET/password`

## Import Workflow

This is a credit card. Transactions may appear on the statement with a delay, so you MUST follow the billing-statement-based verification workflow below to avoid missing transactions.

### Billing Statement Verification

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. `agent-browser --headed --args "--disable-blink-features=AutomationControlled" open https://www.viewsnet.jp/default.htm`
3. Fill service ID and password fields, click ログイン
4. After login, close the rtoaster popup:
   `agent-browser eval "document.getElementById('rtoaster_popup').style.display='none'; document.getElementById('rt.popup-overlay_rtoaster_popup').style.display='none'"`
5. Click `ご利用明細照会` to open the statement page
6. If multiple cards exist, select `ルミネカード` from the card dropdown
7. For each billing month (starting from the most recent confirmed statement, going backwards):
   a. Click the month link (e.g., `2026年02月`)
   b. Note the `カードのご利用額合計` (total) and `お支払日` (payment date)
   c. Check if this total already exists in GnuCash (see SKILL.md "Credit Card: Billing Total Check")
   d. If the total exists → all transactions in this statement are already imported; stop going further back
   e. If the total does NOT exist → download CSV via `明細CSVダウンロード` button
8. Convert CSV from Shift-JIS to UTF-8: `iconv -f SHIFT_JIS -t UTF-8 <file>`
9. Perform per-transaction duplicate detection (see SKILL.md "Credit Card: Duplicate Detection")
10. Prepare RAW_DATA with only new transactions (use CSV confirmed format)
11. Copy RAW_DATA into `tmp/lumine_card_import_YYYYMMDD.py`
12. Run `python3 tmp/lumine_card_import_YYYYMMDD.py review` to show review table
13. User reviews and specifies manual overrides by ID
14. Run `python3 tmp/lumine_card_import_YYYYMMDD.py sql > tmp/import_lumine_card.sql` to generate SQL
15. Execute SQL to insert transactions

### Current Statement (Unconfirmed)

See SKILL.md "Credit Card: Current Statement (Unconfirmed)".

Click `請求予定の明細` to view unconfirmed transactions. This page does NOT have CSV download; extract data via:
`agent-browser eval "document.querySelector('table[summary*=\"ご利用年月日\"]').innerText"`

Use the unconfirmed format for RAW_DATA.

## Script Template

- `scripts/lumine_card_import.py`

## Browser Data Format

### Confirmed format (CSV, Shift-JIS)

Downloaded via `明細CSVダウンロード` button. Convert to UTF-8 before use.

Example:
```
会員番号,****-****-****-****
対象カード,ルミネカード
お支払日,2026年02月04日
今回お支払金額,"1,234"

ご利用年月日,ご利用箇所,ご利用額,払戻額,ご請求額（うち手数料・利息）,支払区分（回数）,今回回数,今回ご請求額・弁済金（うち手数料・利息）,現地通貨額,通貨略称,換算レート
****-****-****-**** 柴田　竜典
2025/12/10,イイトルミネ新宿店　ランディーズドーナツ,800,,760,１回払,,760,,   ,
2025/12/17,東京都交通局　春日駅　オートチャージ（モバイル）,"5,000",,"5,000",１回払,,"5,000",,   ,
```

Notes:
- Header rows: 会員番号, 対象カード, お支払日, 今回お支払金額, then blank line, then column headers, then card holder line
- Date format: `YYYY/MM/DD`
- Columns: date, merchant, usage_amount, refund, billed_amount, pay_type, installment, current_billed, foreign_amount, currency, exchange_rate
- LUMINE stores have 5% discount: ご利用額 (original) ≠ ご請求額 (billed after discount). MUST use ご請求額 (column index 4, 0-based) for GnuCash amount
- Amount format: comma-separated integers, quoted when containing commas (e.g., `"5,000"`)
- Full-width numbers for pay_type (１回払)

### Unconfirmed format (HTML table via eval)

Text extracted via `eval "document.querySelector('table[summary*=\"ご利用年月日\"]').innerText"`.

Example:
```
2026\n01/12\t****-****-****-****\t東京都交通局　曙橋駅　オートチャージ（モバイル）\t5,000\n(5,000)\t \t\t \tショッピング１回払い\t
2026\n01/27\tイイトルミネ新宿店　ババンコク屋台カオサン\t1,100\n(1,045)\t \t\t \tショッピング１回払い\t
```

Notes:
- Tab-separated fields
- Date: `YYYY\nMM/DD` (year and month/day separated by newline)
- Amount field: `original_amount\n(discounted_amount)` — use the discounted amount in parentheses
- Columns: date, card_number, merchant, amount(discounted), overseas_flag, (empty), (space), pay_type, (empty)
- Card number column may be absent in some rows

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| オートチャージ（モバイル） | `Assets:JPY - Current Assets:Prepaid:Suica iPhone` | Auto-charge (Mobile Suica) |

For any transaction not matching the above patterns, check past GnuCash transactions for the same description. If no match found, ask the user.

### LUMINE Store Discount

LUMINE CARD provides 5% off at LUMINE/NEWoMan stores. The statement shows both the original amount (ご利用額) and the billed amount (ご請求額). Always use the billed amount (ご請求額) for GnuCash transactions.

## Script Input Format

Supports both confirmed (CSV) and unconfirmed (HTML table) formats. The parser auto-detects the format by checking if the first data line contains a date in `YYYY/MM/DD` format (confirmed) or `YYYY\nMM/DD` format (unconfirmed).

### Confirmed format (CSV)

Comma-separated: `date, merchant, usage_amount, refund, billed_amount, pay_type, installment, current_billed, foreign_amount, currency, exchange_rate`

### Unconfirmed format (HTML table)

Tab-separated with newlines within fields: `date, card_number, merchant, amount(discounted), overseas, empty, space, pay_type, empty`

### Common parsing rules
- Skip header rows (会員番号, 対象カード, etc.) and column header row
- Skip card holder lines (matching `****-****-****-****`)
- Confirmed: lines starting with `YYYY/MM/DD` are transaction lines; use billed_amount (index 4)
- Unconfirmed: extract discounted amount from parentheses in amount field
- Amount: remove commas, parse as integer; always negative (credit card spending)

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Merchant: Merchant name from statement
- Desc: Description for GnuCash (in English)
- Transfer: Target account
- Amount: Amount (JPY, always shown as positive for readability)

## Notes

- All descriptions MUST be in English
- LUMINE CARD is issued by VIEW Card (ビューカード) and uses VIEW's NET portal
- The `--disable-blink-features=AutomationControlled` flag is required to avoid bot detection
- The rtoaster popup MUST be closed via JavaScript after login before interacting with the page
- CSV files are encoded in Shift-JIS and must be converted to UTF-8
