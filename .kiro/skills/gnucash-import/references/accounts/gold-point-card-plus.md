# GOLD POINT CARD + Statement Import

## GnuCash Account

- Card: `Liabilities:Credit Card:GOLD POINT CARD +`
- Payment debit: `Assets:JPY - Current Assets:Banks:d NEOBANK`
- Payment date: 27th (or next business day if 27th is a holiday)

## Credentials

- Username: `op://gnucash/Yodobashi Camera/username`
- Password: `op://gnucash/Yodobashi Camera/password`

## Import Workflow

This is a credit card. Transactions may appear on the statement with a delay, so you MUST follow the billing-statement-based verification workflow below to avoid missing transactions.

### Billing Statement Verification

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. `agent-browser --headed --args "--disable-blink-features=AutomationControlled" open https://secure.goldpoint.co.jp/gpm/authentication/index.html`
3. Fill password field and click Submit (email is pre-filled from browser profile)
4. Click `ご利用明細の照会` to open the Webご利用明細 page
5. For each billing month (starting from the most recent confirmed statement, going backwards):
   a. Select the month from the `お支払い月` dropdown and click `照会`
   b. Note the `お支払い合計額` (total payment amount) and `お支払い日` (payment date)
   c. Check if this total already exists in GnuCash (see SKILL.md "Credit Card: Billing Total Check")
   d. If the total exists → all transactions in this statement are already imported; stop going further back
   e. If the total does NOT exist → extract all transactions from this statement and proceed to duplicate detection
6. For statements where the total is not in GnuCash, extract transaction data via `agent-browser eval "document.querySelector('body').innerText"`
7. Perform per-transaction duplicate detection (see SKILL.md "Credit Card: Duplicate Detection")
8. Prepare RAW_DATA with only new transactions
9. Copy RAW_DATA into `tmp/gold_point_card_plus_import_YYYYMMDD.py`
10. Run `python3 tmp/gold_point_card_plus_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/gold_point_card_plus_import_YYYYMMDD.py sql > tmp/import_gold_point_card_plus.sql` to generate SQL
13. Execute SQL to insert transactions

### Current Statement (Unconfirmed)

See SKILL.md "Credit Card: Current Statement (Unconfirmed)".

When selecting a future month (e.g., "2026年4月以降") or the next payment month, the page shows unconfirmed transactions in a different format. See "Unconfirmed format" below.

## Script Template

- `scripts/gold_point_card_plus_import.py`

## Browser Data Format

Text extracted via `eval "document.querySelector('body').innerText"` from the Webご利用明細 page.

### Confirmed format (Webご利用明細)

Tab-separated table with a card-holder header line.

Example:
```
柴田　竜典　様　ご利用分　4980-01**-****-****　（ゴールドポイントカードプラス）
	26/01/15	ヨドバシドットコム	1,500	１	１	1,500		
	26/01/16	ヨドバシドットコム	300	１	１	300		
	26/01/19	ヨドバシカメラ	2,000	１	１	2,000		
＜お支払金額総合計＞	 	 	3,800		 
```

Notes:
- Card section header: `柴田　竜典　様　ご利用分　4980-01**-****-****　（ゴールドポイントカードプラス）`
- Date format: `YY/MM/DD`
- Columns (tab-separated): empty, date, merchant, amount, payment_type, installment, payment_amount, then optionally foreign currency fields
- Amount format: comma-separated integers (e.g., `1,500`)
- Full-width numbers for payment_type (１=1回払い) and installment (１)
- Foreign transactions have extra fields: local_amount, currency_code, exchange_rate, exchange_date
- `お支払い月` dropdown allows selecting past 15 months plus future unconfirmed
- Payment date is the 27th of each month

### Unconfirmed format (カードご利用明細照会)

Tab-separated table shown when selecting a future payment month.

Example:
```
26/02/08	ヨドバシドットコム	ご本人	1回払い		26/03	1,500	
```

Notes:
- Columns (tab-separated): date, merchant, card_holder, pay_type, installment_count, pay_month, amount, then optionally foreign currency fields
- No leading tab (unlike confirmed format)
- pay_type is text (e.g., `1回払い`) instead of full-width number
- card_holder: `ご本人` for primary card holder

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| ヨドバシドットコム | (email lookup) | Yodobashi.com |
| ヨドバシカメラ | (ask user) | Yodobashi Camera |

For any transaction not matching the above patterns, check past GnuCash transactions for the same description. If no match found, ask the user.

### Email Lookup for Missing Information

Search order confirmation emails from ヨドバシ・ドット・コム to determine what was purchased and map to the correct expense account. Match by date and amount. See [email-lookup.md](../email-lookup.md).

## Script Input Format

Supports both confirmed (Webご利用明細) and unconfirmed (カードご利用明細照会) formats. The parser auto-detects the format by checking if the first field after split is a date or empty.

### Confirmed format

Tab-separated: `empty, date, merchant, amount, pay_type, installment, pay_amount, [foreign_fields]`

### Unconfirmed format

Tab-separated: `date, merchant, card_holder, pay_type, installment_count, pay_month, amount, [foreign_fields]`

### Common parsing rules
- Lines matching `ご利用分` are card section headers (skip)
- Confirmed: lines starting with `\tYY/MM/DD` are transaction lines
- Unconfirmed: lines starting with `YY/MM/DD` are transaction lines
- Amount: remove commas, parse as integer; always negative (credit card spending)
- Skip `＜お支払金額総合計＞` line and blank lines

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
- Purchases are primarily from Yodobashi (online and in-store); email lookup is essential to determine the correct expense account
- In-store purchases show as ヨドバシカメラ, online purchases show as ヨドバシドットコム
