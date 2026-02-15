# Amazon MasterCard Gold Statement Import

## GnuCash Account

- Card: `Liabilities:Credit Card:Amazon MasterCard Gold`
- Payment debit: `Assets:JPY - Current Assets:Banks:d NEOBANK`
- Payment date: 26th (or next business day if 26th is a holiday)

## Credentials

Password field on Vpass login does not accept automated input. You MUST use `agent-browser --headed` and ask the user to enter the password manually.

## Import Workflow

This is a credit card. Transactions may appear on the statement with a delay, so you MUST follow the billing-statement-based verification workflow below to avoid missing transactions.

### Billing Statement Verification

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. `agent-browser --headed open https://www.smbc-card.com/mem/index.jsp`
3. Ask user to enter password manually and log in
4. Switch card to `Ａｍａｚｏｎ旧ゴールド` using the card selector dropdown (`#vp-view-VC0205-001_RS0051_cardIdentifyKey`)
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
10. Copy RAW_DATA into `tmp/amazon_mastercard_gold_import_YYYYMMDD.py`
11. Run `python3 tmp/amazon_mastercard_gold_import_YYYYMMDD.py review` to show review table
12. User reviews and specifies manual overrides by ID
13. Run `python3 tmp/amazon_mastercard_gold_import_YYYYMMDD.py sql > tmp/import_amazon_mastercard_gold.sql` to generate SQL
14. Execute SQL to insert transactions

### Current Statement (Unconfirmed)

See SKILL.md "Credit Card: Current Statement (Unconfirmed)".

## Script Template

- `scripts/amazon_mastercard_gold_import.py`

## Browser Data Format

Text extracted via `eval "document.querySelector('body').innerText"` from the WEB明細書 page.

Tab-separated table with card-holder sections. Each section starts with a header line containing the card number and card type.

Example:
```
柴田　竜典　様　ご利用分　5302-32**-****-****　（Ａｍａｚｏｎマスター）
	26/01/03	ＡＭＡＺＯＮ．ＣＯ．ＪＰ	5,000	１	１	5,000		
	26/01/04	ＡＭＡＺＯＮ．ＣＯ．ＪＰ	1,200	１	１	1,200		
	26/01/14	ＡｍａｚｏｎＰａｙ提携サイト	800	１	１	800	ＡＭＺ＊アマゾン社員食堂	
	26/01/03	ALIEXPRESS (SINGAPORE )	2,000	１	１	2,000	15.00	USD	133.333	01 03	
柴田　竜典　様　ご利用分　5302-39**-****-****　（ＡｐｐｌｅＰａｙ）
	26/01/04	セブン－イレブン	500	１	１	500		
	26/01/05	ファミリーマート	300	１	１	300	ファミリーマート　新宿三丁目	
＜お支払金額総合計＞	 	 	24,641		 
```

Notes:
- Card section header: `柴田　竜典　様　ご利用分　5302-XX**-****-****　（カード名）`
- Two card sections: Amazonマスター (main card) and ApplePay
- Date format: `YY/MM/DD`
- Columns (tab-separated): date, merchant, amount, payment_type, installment, payment_amount, then optionally remarks OR foreign currency fields
- Amount format: comma-separated integers (e.g., `1,200`)
- Full-width characters for merchant names (e.g., `ＡＭＡＺＯＮ．ＣＯ．ＪＰ`)
- Foreign transactions have extra fields: local_amount, currency_code, exchange_rate, exchange_date
- Remarks field (備考) may contain store details (e.g., `ＡＭＺ＊アマゾン社員食堂`, `ファミリーマート　新宿三丁目`)
- `お支払い月` dropdown allows selecting past 15 months
- Payment date is the 26th of each month

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| ＡＭＡＺＯＮ．ＣＯ．ＪＰ | (email lookup) | Amazon |
| ＡｍａｚｏｎＰａｙ提携サイト + ＡＭＺ＊アマゾン社員食堂 | Expenses:Foods:Dining | AMZ Employee Cafe |
| ＡｍａｚｏｎＰａｙ提携サイト (other) | (email lookup) | (from email) |
| セブン－イレブン | Expenses:Foods:Dining | SEVEN-ELEVEN |
| ファミリーマート | Expenses:Foods:Dining | Family Mart |
| ローソン | Expenses:Foods:Dining | LAWSON |
| ALIEXPRESS | (email lookup) | AliExpress |

For any transaction not matching the above patterns, check past GnuCash transactions for the same description. If no match found, ask the user.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Supports both confirmed (WEB明細書) and unconfirmed (ご利用明細照会) formats. The parser auto-detects the format by checking if the third column is a number.

### Confirmed format (WEB明細書)

Tab-separated: `date, merchant, amount, pay_type, installment, pay_amount, [remarks | foreign_fields]`

### Unconfirmed format (ご利用明細照会)

Tab-separated: `date, merchant, card_holder, pay_type, empty, pay_month, amount`

### Common parsing rules
- Lines matching `ご利用分` are card section headers (skip, but note the card type)
- Lines starting with `\tYY/MM/DD\t` are transaction lines (tab-separated)
- Split by tab: [empty, date, merchant, amount, payment_type, installment, payment_amount, ...]
- Amount: remove commas, parse as integer; always negative (credit card spending)
- Foreign transactions: fields after payment_amount are local_amount, currency_code, exchange_rate, exchange_date
- Domestic transactions: field after payment_amount is remarks (may be empty)
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
- Amazon purchases map to many different accounts; email lookup is essential
- Both card sections (Amazonマスター and ApplePay) belong to the same GnuCash account
