# PayPay Card JCB Statement Import

## GnuCash Account

- Card: `Liabilities:Credit Card:PayPay Card JCB`
- Payment debit: `Assets:JPY - Current Assets:Banks:d NEOBANK`
- Payment date: 27th of each month

## Credentials

Login via Yahoo! JAPAN ID with passkey. You MUST use `agent-browser --headed` and ask the user to complete passkey authentication manually.

## Import Workflow

This is a credit card. Follow the billing-statement-based verification workflow.

### Billing Statement Verification

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. `agent-browser --headed open https://www.paypay-card.co.jp/member-login?promptParam=3`
3. Ask user to complete Yahoo! JAPAN ID passkey login
4. Dismiss any popups or tutorials that appear after login:
   - Tutorial appears with `次へ` (Next) buttons/links
   - Click through all `次へ` buttons until `閉じる` (Close) or `完了` (Complete) appears
   - Click the final button to dismiss the tutorial
   - May require multiple `snapshot -i` and click cycles
5. Click `請求明細` in the top navigation to open the statement page
6. Navigate directly to monthly statement page: `agent-browser open https://www.paypay-card.co.jp/member/statement/monthly?dispmode=latest`
7. Wait for page load and check for popups:
   - After first access to monthly statement page, a popup may appear
   - Check snapshot for `閉じる` (Close) link/button
   - If found, click it to dismiss the popup
8. For each billing month (starting from the most recent confirmed statement, going backwards):
   a. Note the total amount and status (仮確定/未確定)
   b. Check if this total already exists in GnuCash (see SKILL.md "Credit Card: Billing Total Check")
   c. If the total exists → all transactions in this statement are already imported; stop going further back
   d. If the total does NOT exist → extract all transactions and proceed to duplicate detection
9. Extract transaction data via `agent-browser snapshot` (transactions appear as menuitem elements)
10. Perform per-transaction duplicate detection (see SKILL.md "Credit Card: Duplicate Detection")
11. Prepare RAW_DATA with only new transactions
12. Copy RAW_DATA into `tmp/paypay_card_jcb_import_YYYYMMDD.py`
13. Run `python3 tmp/paypay_card_jcb_import_YYYYMMDD.py review` to show review table
14. User reviews and specifies manual overrides by ID
15. Run `python3 tmp/paypay_card_jcb_import_YYYYMMDD.py sql > tmp/import_paypay_card_jcb.sql` to generate SQL
16. Execute SQL to insert transactions

### Current Statement (Unconfirmed)

See SKILL.md "Credit Card: Current Statement (Unconfirmed)".

## Script Template

- `scripts/paypay_card_jcb_import.py`

## Browser Data Format

Transaction data extracted via `agent-browser snapshot` from the statement page (`/member/statement/monthly`).

Each transaction appears as a menuitem element with text in the format: `{merchant} {date} {amount}円`

Example (from snapshot):
```
menuitem "チャージ 2026年1月20日 1,000円"
menuitem "RESTAURANT ABC 2026年1月18日 2,500円"
menuitem "キッチンオリジン、オリジン 2026年1月6日 3,000円"
menuitem "請求書払い 2026年1月4日 50,000円"
menuitem "ヤフージャパン 2025年12月31日 800円"
```

Notes:
- Date format: `YYYY年M月D日` (Japanese date)
- Amount: comma-separated integers with `円` suffix
- Merchant names may contain Japanese characters, commas, and spaces
- Month navigation via `前月`/`翌月` buttons
- Statement status: `仮確定` (semi-confirmed) or `未確定` (unconfirmed)
- `明細出力` button and `CSVダウンロード` link available on confirmed statements
- The page URL pattern: `/member/statement/monthly?dispmode=latest`

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| チャージ | Assets:JPY - Current Assets:Prepaid:PayPay | null |
| Dining/restaurant names | Expenses:Foods:Dining | (merchant name in English) |
| ヤフージャパン | (ask user for split amounts) | Yahoo! |
| 請求書払い | (ask user) | (ask user) |

- `ヤフージャパン` typically requires a split transaction; ask the user for the breakdown each time
- `請求書払い` can be various types of payments; always ask the user
- For any transaction not matching the above patterns, check past GnuCash transactions for the same description. If no match found, ask the user

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

One transaction per line, extracted from snapshot menuitem text:

```
チャージ	2026年1月20日	1,000
RESTAURANT ABC	2026年1月18日	2,500
キッチンオリジン、オリジン	2026年1月6日	3,000
請求書払い	2026年1月4日	50,000
ヤフージャパン	2025年12月31日	800
```

Tab-separated: `merchant\tdate\tamount`

Parsing rules:
- Split each line by tab
- Date: parse `YYYY年M月D日` format
- Amount: remove commas, parse as integer; always negative (credit card spending)
- Skip blank lines

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Merchant: Merchant name from statement
- Desc: Description for GnuCash (English)
- Transfer: Target account
- Amount: Amount (JPY, always shown as positive for readability)

## Notes

- All descriptions MUST be in English
