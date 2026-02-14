# d NEOBANK Statement Import

## GnuCash Account

- JPY: `Assets:JPY - Current Assets:Banks:d NEOBANK`
- USD: `Assets:USD - Current Assets:Banks:d NEOBANK`

Sub-accounts (purpose accounts):
- `Assets:JPY - Current Assets:Banks:d NEOBANK:Reserved Account`
- `Assets:JPY - Current Assets:Banks:d NEOBANK:Longterm Account`
- `Assets:JPY - Current Assets:Banks:d NEOBANK:Retirement Account`
- `Assets:USD - Current Assets:Banks:d NEOBANK:Entertainment Account`
- `Assets:USD - Current Assets:Banks:d NEOBANK:Longterm Account`

## Credentials

Manual login required. You MUST use `agent-browser --headed` and ask the user to log in manually.

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for existing transactions (see Duplicate Detection below)
3. `agent-browser --headed open https://www.netbk.co.jp/contents/pages/wpl010101E/i010101CT/DI01010240`
4. Ask user to log in manually
5. After login, click "入出金明細" link in the navigation bar

### JPY 代表口座 (Primary)

6. Ensure "代表口座" and "円" are selected (default after navigating to 入出金明細)
7. Click the target month in the left sidebar to switch months
8. `agent-browser snapshot -c -s "main"` to get transaction data
9. Repeat steps 7-8 for each month needed

### USD 代表口座

10. Click the "円" currency button, then select "米ドル"
11. Click the target month in the left sidebar
12. `agent-browser snapshot -c -s "main"` to get transaction data
13. Repeat steps 11-12 for each month needed

### Currency Transfer Matching

For currency transfers (JPY side: `普通 米ドル 代表口座`, USD side: `普通 円 代表口座`), match entries by date to obtain both JPY and USD amounts. The script needs both to create multi-currency splits.

### Purpose Accounts

Purpose account transfers (`普通 円 予備費`, `普通 円 長期貯蓄`, `普通 円 老後資金`) appear in the JPY 代表口座 view. Do NOT import from purpose account views separately — they are mirror transactions.

### Generate and Execute

14. Prepare RAW_DATA and copy into `tmp/d_neobank_import_YYYYMMDD.py`
15. Run `python3 tmp/d_neobank_import_YYYYMMDD.py review` to show review table
16. User reviews and specifies manual overrides by ID
17. Run `python3 tmp/d_neobank_import_YYYYMMDD.py sql > tmp/import_d_neobank.sql` to generate SQL
18. Execute SQL to insert transactions

## Script Template

- `scripts/d_neobank_import.py`

## Browser Data Format

Monthly transaction list under heading "YYYY年M月". Columns: 日付, 取引内容, 出金金額, 入金金額, 残高, メモ.

The first transaction of each date uses `time` for the date and `text` for the description. Subsequent transactions on the same date omit the `time` element and use `term` for the description.

JPY example (from snapshot):
```
  heading "2026年2月" [level=2]
    time: 14日
    text: 振込＊○○ ○○
      - listitem: 10,000円
      - listitem: 1,200,000円
  term: 口座振替 ＤＦ ○○カード
      - listitem: 5,000円
      - listitem: 1,195,000円
    time: 10日
    text: 振込＊○○（○○）
      - listitem: 20,000円
      - listitem: 1,215,000円
```

USD example (from snapshot):
```
  heading "2025年12月" [level=2]
    time: 21日
    text: 国税
      - listitem: 0.02USD
      - listitem: 0.14USD
  term: 利息
      - listitem: 0.16USD
      - listitem: 0.16USD
    time: 19日
    text: 普通 円 代表口座
      - listitem: 1,789.10USD
      - listitem: 0.00USD
```

Notes:
- Date is day-only (e.g., `14日`); combine with the heading year/month to get full date
- Whether it's a deposit or withdrawal must be inferred from balance changes
- JPY amounts: comma-separated with `円` suffix (e.g., `10,000円`)
- USD amounts: decimal with `USD` suffix (e.g., `1,789.10USD`)

## Conversion Rules

### Transfers (振込)

| Pattern | Direction | GnuCash Account | Description | Notes |
|---------|-----------|-----------------|-------------|-------|
| 振込＊シバタ ア* | Deposit 32,400 | `Income:Reserved Money from Family` | Wife | |
| 振込＊シバタ ア* | Deposit (other) | Ask user or search email | Wife | Search email with amount to determine account |
| 振込＊シバタ ア* | Withdrawal | `Expenses:Reserved Money to Family` | Wife | |
| 振込＊シバタ ノ* | Withdrawal 100,000 | Split: `Assets:JPY - Current Assets:Reimbursement:Family` (60,000) + `Expenses:Living Cost to Family` (40,000) | Parents | |
| 振込＊シズ* | Any | `Assets:JPY - Current Assets:Reimbursement:Friend` | NULL | Matches any name starting with シズ |
| 振込＊シバタ タツノリ | Deposit | `Assets:JPY - Current Assets:Banks:SBI Shinsei Bank` | NULL | Self-transfer; may already exist from SBI Shinsei import |
| 振込＊ジドウテアテ（クニ） | Deposit | `Income:National Allowance` | Japan | |
| 振込＊アマゾンウエブサービスジヤパン* | Deposit | `Assets:JPY - Current Assets:Reimbursement:AWS Japan` | AWS Japan | |
| 振込＊０１８サポートキユウフキン | Deposit | `Income:National Allowance` | Tokyo | |

### Direct Debits (口座振替)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 口座振替 ＤＦ トウキユウカード | `Liabilities:Credit Card:TOKYU CARD ClubQ JMB` | NULL |
| 口座振替 ミツイスミトモカード | `Liabilities:Credit Card:Amazon MasterCard Gold` or `Liabilities:Credit Card:ANA Super Flyers Gold Card` | NULL |
| 口座振替 ＰａｙＰａｙカード | `Liabilities:Credit Card:PayPay Card JCB` | NULL |
| 口座振替 ＡＰアプラス | `Liabilities:Credit Card:Luxury Card Mastercard Titanium` | NULL |
| 口座振替 ＤＦ ＧＰマーケテインク | `Liabilities:Credit Card:GOLD POINT CARD +` | NULL |

For ミツイスミトモカード, you MUST ask the user which card it is (Amazon MasterCard Gold or ANA Super Flyers Gold Card).

### Skipped Patterns

These patterns MUST NOT be imported:
- `約定返済 円 住宅` (mortgage payment)

### Purpose Account Transfers (目的別口座)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 普通 円 予備費 | `Assets:JPY - Current Assets:Banks:d NEOBANK:Reserved Account` | NULL |
| 普通 円 長期貯蓄 | `Assets:JPY - Current Assets:Banks:d NEOBANK:Longterm Account` | NULL |
| 普通 円 老後資金 | `Assets:JPY - Current Assets:Banks:d NEOBANK:Retirement Account` | NULL |

### Currency Transfers

| JPY Pattern | USD Pattern | GnuCash Account | Description |
|-------------|-------------|-----------------|-------------|
| 普通 米ドル 代表口座 | 普通 円 代表口座 | `Assets:USD - Current Assets:Banks:d NEOBANK` | NULL |

Multi-currency: use JPY amount for value_num/value_denom on the JPY split, USD amount for quantity_num/quantity_denom on the USD split.

### Tax and Interest (JPY)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 地方税 | `Expenses:Tax:Income Tax` | Tokyo |
| 国税 | `Expenses:Tax:Income Tax` | Japan |
| 利息 | `Income:Interest Income` | NULL |
| モバイルレジ（コウキン）* | `Expenses:Tax:Fixed Assets Tax` | Tokyo |
| ヨツヤゼイムシヨ* | `Expenses:Tax:Income Tax` | Japan |

For `取消` (cancellation) entries, the amount sign is reversed.

### Tax and Interest (USD)

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 国税 | `Expenses:Tax:Income Tax` | Japan |
| 利息 | `Income:Interest Income` | NULL |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Duplicate Detection

Transfers between d NEOBANK and other imported accounts (e.g., SBI Shinsei Bank) may already exist in GnuCash if the other account was imported first. You MUST NOT simply check the last imported date. Instead:

1. Query existing transactions for the d NEOBANK account within the last 2 months
2. For each transaction in the statement, check if a matching transaction already exists (same date and amount)
3. If a match is found, compare descriptions to confirm it is the same transaction
4. Report duplicates and missing transactions separately to the user

Max lookback: 2 months.

## Script Input Format

Tab-separated lines: `CURRENCY\tDATE\tDESCRIPTION\tWITHDRAWAL\tDEPOSIT`

- CURRENCY: `JPY` or `USD`
- DATE: `YYYY/MM/DD`
- DESCRIPTION: 取引内容 text
- WITHDRAWAL: amount (empty if none)
- DEPOSIT: amount (empty if none)
- Amounts are raw numbers without commas or currency suffix

Example:
```
JPY	2026/02/14	振込＊○○ ○○	10000	
JPY	2026/02/12	口座振替 ＤＦ ○○カード	5000	
JPY	2026/02/10	振込＊○○（○○）		20000
JPY	2026/02/05	普通 円 予備費	150000	
JPY	2025/12/19	普通 米ドル 代表口座	250000	
USD	2025/12/19	普通 円 代表口座	1789.10	
USD	2025/12/21	国税	0.02	
USD	2025/12/21	利息		0.16
```

Parsing rules:
- Split by tab
- Field 0: currency (`JPY` or `USD`)
- Field 1: date (`YYYY/MM/DD`)
- Field 2: description (取引内容)
- Field 3: withdrawal amount (empty = 0)
- Field 4: deposit amount (empty = 0)
- Amount = deposit - withdrawal

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Ccy: Currency (JPY/USD)
- Desc: Transaction description from statement
- Transfer: Target GnuCash account
- Increase/Decrease: Amount (¥ for JPY, $ for USD)

## Notes

- The page displays one month at a time; navigate months via the left sidebar
- Account selector: 代表口座, 予備費, 長期貯蓄, 老後資金, 生活費, 娯楽費
- Currency selector: 円, 米ドル, ユーロ, 英ポンド, 豪ドル, NZドル, カナダドル, スイスフラン, 香港ドル, 南アランド
- Transaction history goes back several years
