# ANA Super Flyers Gold Card Statement Import

## GnuCash Account

- Card: `Liabilities:Credit Card:ANA Super Flyers Gold Card`
- Payment debit: `Assets:JPY - Current Assets:Banks:d NEOBANK`
- Payment date: 10th (or next business day if 10th is a holiday)

## Credentials

Password field on Vpass login does not accept automated input. You MUST use `agent-browser --headed` and ask the user to enter the password manually.

## Import Workflow

This is a credit card. Transactions may appear on the statement with a delay, so you MUST follow the billing-statement-based verification workflow below to avoid missing transactions.

### Billing Statement Verification

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. `agent-browser --headed open https://www.smbc-card.com/mem/index.jsp`
3. Ask user to enter password manually and log in
4. Switch card to `ＡＮＡ　ＶＩＳＡゴールド` using the card selector dropdown
5. Click `ご利用明細` to open the WEB明細書 page
6. For each billing month (starting from the most recent confirmed statement, going backwards):
   a. Select the month from the `お支払い月` dropdown
   b. Note the `お支払い合計額` (total payment amount) and `お支払い日` (payment date)
   c. Check if this total already exists in GnuCash (see SKILL.md "Credit Card: Billing Total Check")
   d. If the total exists → all transactions in this statement are already imported; stop going further back
   e. If the total does NOT exist → extract all transactions from this statement and proceed to duplicate detection
7. For statements where the total is not in GnuCash, extract transaction data via `agent-browser eval "document.querySelector('body').innerText"`
8. Perform per-transaction duplicate detection (see SKILL.md "Credit Card: Duplicate Detection")
9. Prepare RAW_DATA with only new transactions
10. Copy RAW_DATA into `tmp/ana_super_flyers_gold_card_import_YYYYMMDD.py`
11. Run `python3 tmp/ana_super_flyers_gold_card_import_YYYYMMDD.py review` to show review table
12. User reviews and specifies manual overrides by ID
13. Run `python3 tmp/ana_super_flyers_gold_card_import_YYYYMMDD.py sql > tmp/import_ana_super_flyers_gold_card.sql` to generate SQL
14. Execute SQL to insert transactions

### Current Statement (Unconfirmed)

See SKILL.md "Credit Card: Current Statement (Unconfirmed)".

## Script Template

- `scripts/ana_super_flyers_gold_card_import.py`

## Browser Data Format

Text extracted via `eval "document.querySelector('body').innerText"` from the WEB明細書 page.

Tab-separated table with card-holder sections. Each section starts with a header line containing the card number and card type. Transaction lines may have `B#` or `#` markers before the date.

Example:
```
柴田　竜典　様　ご利用分　4980-00**-****-****　（ＡＮＡＶＩＳＡゴールド）
B#	25/12/28	レストラン　新宿店	2,500	１	１	2,500		◎
#	26/01/01	ソフトウェア会社	330	１	１	330		◎
#	26/01/05	ALIEXPRESS (SINGAPORE )	2,000	１	１	2,000	15.00	USD	133.333	01 05	◎
＜お支払金額総合計＞	 	 	5,160		 
```

Notes:
- Card section header: `柴田　竜典　様　ご利用分　4980-XX**-****-****　（ＡＮＡＶＩＳＡゴールド）`
- Transaction lines may start with `B#` or `#` marker (before tab+date)
- Date format: `YY/MM/DD`
- Columns (tab-separated): [marker], date, merchant, amount, payment_type, installment, payment_amount, then optionally remarks OR foreign currency fields
- Amount format: comma-separated integers (e.g., `2,500`)
- Full-width characters for merchant names
- Foreign transactions have extra fields: local_amount, currency_code, exchange_rate, exchange_date
- Remarks field (備考) may contain `◎` (point-eligible marker) or store details
- `お支払い月` dropdown allows selecting past 15 months
- Payment date is the 10th of each month

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| セブン－イレブン | Expenses:Foods:Dining | SEVEN-ELEVEN |
| ファミリーマート | Expenses:Foods:Dining | Family Mart |
| ローソン | Expenses:Foods:Dining | LAWSON |
| ALIEXPRESS | (email lookup) | AliExpress |

For any transaction not matching the above patterns, check past GnuCash transactions for the same description. If no match found, ask the user.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Same as Amazon MasterCard Gold. Supports both confirmed (WEB明細書) and unconfirmed (ご利用明細照会) formats. The parser auto-detects the format by checking if the column after the date is a number.

### Confirmed format (WEB明細書)

Tab-separated: `[marker], date, merchant, amount, pay_type, installment, pay_amount, [remarks | foreign_fields]`

Transaction lines may be prefixed with `B#` or `#` markers.

### Unconfirmed format (ご利用明細照会)

Tab-separated: `date, merchant, card_holder, pay_type, empty, pay_month, amount`

### Common parsing rules
- Lines matching `ご利用分` are card section headers (skip)
- Transaction lines contain a date pattern `YY/MM/DD`
- Strip `B#` or `#` markers before parsing columns
- Amount: remove commas, parse as integer; always negative (credit card spending)
- Foreign transactions: fields after payment_amount are local_amount, currency_code, exchange_rate, exchange_date
- Domestic transactions: field after payment_amount may be empty or contain `◎`
- Skip `＜お支払金額総合計＞` line and blank lines

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Merchant: Merchant name from statement (normalized to ASCII)
- Desc: Description for GnuCash
- Transfer: Target account
- Amount: Amount (JPY, always shown as positive for readability)

## Notes

- All descriptions MUST be in English
- Same Vpass portal as Amazon MasterCard Gold but different card selector
