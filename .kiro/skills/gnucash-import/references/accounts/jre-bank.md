# JRE Bank Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Banks:JRE Bank`

## Credentials

Secret question is required. You MUST use `agent-browser --auto-connect` and ask the user to log in manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --auto-connect open https://sfes.rakuten-bank.co.jp/MS/main/RbS?CID=M_START&CMD=LOGIN&BAAS_CODE=JRE`
4. Ask user to log in manually (合言葉認証 required)
5. Click "入出金明細" tab, then click "以前のお取引"
6. `agent-browser --auto-connect eval "document.querySelector('body').innerText"` to get transaction data
7. Extract the transaction section from the text (between the header row and the CSV download section)
8. Copy RAW_DATA into `tmp/jre_bank_import_YYYYMMDD.py`
9. Run `python3 tmp/jre_bank_import_YYYYMMDD.py review` to show review table
10. User reviews and specifies manual overrides by ID
11. Run `python3 tmp/jre_bank_import_YYYYMMDD.py sql > tmp/jre_bank_import_YYYYMMDD.sql` to generate SQL
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
| 給与 | (multi-split, see below) | AWS Japan |
| 住信ＳＢＩネット銀行 | Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank | NULL |
| 預金利息 | Income:Interest Income | NULL |

If a transaction does not match any pattern, ask the user.

### 給与 (Payroll)

The statement shows only the net pay, so ask the user for the payslip PDF and read it with `pdftotext -layout`. Never carry the previous month's figures forward: doing so leaves a transaction that balances internally but disagrees with the statement.

| Payslip item | GnuCash Account | Side |
|--------------|-----------------|------|
| 基本給/BaseComp | Income:Salary | credit |
| 非課税通勤/NTravel | Income:Salary:Allowance | credit |
| AWSome Awards (支給) | Income:Salary:Bonus | credit |
| 健康保険/Health | Expenses:Social Security:Health Insurance | debit |
| 介護保険/NursCare | Expenses:Social Security:Nursing Care Insurance | debit |
| 厚生年金/Welfare | Expenses:Social Security:Welfare | debit |
| 雇用保険/EmployIns | Expenses:Social Security:Employment Insurance | debit |
| 所得税/IncomeTax | Expenses:Tax:Income Tax | debit |
| 住民税/Inhab.Tax | Expenses:Tax:Inhabitant Tax | debit |
| 所得補償/LTD | Expenses:Insurances:Property Insurances | debit |
| AWSome Awards (控除) | Assets:JPY - Current Assets:Reward Programs:AWSome Awards | debit |
| 差引支給額/NetPay | Assets:JPY - Current Assets:Banks:JRE Bank | debit |

Notes:
- 内)本給/BasePay and 内)職務/JobAllow are a breakdown of 基本給/BaseComp, and 通勤手当 計/Travel restates 非課税通勤/NTravel. Using them as separate splits double-counts the gross
- Only the bank split carries a reconciliation state; the payroll splits stay `n`

#### AWSome Awards

The award arrives as points and is taxed on receipt, so the payments line is the grossed-up taxable amount and the deductions line is the point value. `Reward Programs:AWSome Awards` is a `Reward` namespace commodity account, so its split needs the JPY amount in `value` and the point count in `quantity`.

One point is worth about USD 1, and the deductions line is that value converted to JPY at roughly the month's USD rate, so the point count is the deductions line divided by the USD rate rather than by the redemption rate. Grant emails arrive per award and can be added together to cross-check the count.

Redemption runs at 8 points per JPY 1,000 Amazon gift card, below the taxable valuation. Redeeming the full balance therefore realizes less than the recorded value, and the shortfall is booked when the points are exchanged.

The points portal exposes no grant history, so when the point count cannot be established, record the JPY value from the payslip and leave the count to be corrected at redemption, where the exchange reveals the rate.

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
