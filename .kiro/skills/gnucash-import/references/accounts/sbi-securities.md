# SBI Securities Statement Import

## GnuCash Accounts

### NISA (Periodic Investment / つみたて投資枠)

- `Assets:JPY - Current Assets:Securities:SBI Securities:NISA (Periodic Investment):eMAXIS Slim All Countries`
- `Assets:JPY - Current Assets:Securities:SBI Securities:NISA (Periodic Investment):iFreeNEXT NASDAQ100 Index`

### NISA (Growth Investment / 成長投資枠)

- `Assets:JPY - Current Assets:Securities:SBI Securities:NISA (Growth Investment):Entertainment Account:eMAXIS Slim All Countries`
- `Assets:JPY - Current Assets:Securities:SBI Securities:NISA (Growth Investment):Entertainment Account:eMAXIS NASDAQ100 Index`

### Specific Account (特定/一般)

- `Assets:JPY - Current Assets:Securities:SBI Securities:Entertainment Account:eMAXIS Slim All Countries`
- `Assets:JPY - Current Assets:Securities:SBI Securities:Entertainment Account:eMAXIS NASDAQ100 Index`

### USD Accounts

- `Assets:USD - Current Assets:Securities:SBI Securities`
- `Assets:USD - Current Assets:Securities:SBI Securities:Entertainment Account:Invesco QQQ Trust Series 1`
- `Assets:USD - Current Assets:Securities:SBI Securities:Entertainment Account:Vanguard Information Technology Index Fund ETF`

### Transfer Accounts

JPY mutual funds: `Liabilities:A/Payable:SBI Securities`
- Buy: A/Payable:SBI Securities → Fund Account (on trade date)
- Sell: Fund Account → A/Payable:SBI Securities (on trade date)
- The bank side (SBI Hyper Deposit ↔ A/Payable:SBI Securities) is handled separately on settlement date.

USD stocks: `Assets:USD - Current Assets:Securities:SBI Securities` (cash account)
- Sell: Fund Account → Cash Account (with fees/tax splits)

USD cash: Source account is `Assets:USD - Current Assets:Securities:SBI Securities`
- Dividends: `Income:Dividend` → Cash Account
- Transfers/FX: Cash Account → `Assets:USD - Current Assets:Banks:d NEOBANK:Entertainment Account`

### Fee/Tax Accounts (USD stocks)

- `Expenses:Fees` - Commission/brokerage fees
- `Expenses:Tax:Income Tax` - Withholding tax

## Credentials

Passkey authentication required. You MUST use `agent-browser --headed` and ask the user to log in manually.

## Import Workflow

### JPY Mutual Funds (円貨建口座)

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://login.sbisec.co.jp/login/entry`
4. Ask user to log in manually (passkey authentication required)
5. Navigate to 口座管理 > 取引履歴
6. Set date range and click 照会
7. `agent-browser eval "document.querySelector('body').innerText"` to get transaction data
8. If multiple pages, click 次へ→ and repeat step 7
9. Extract the transaction rows from the text (between header row and footer)
10. Copy RAW_DATA_JPY into `tmp/sbi_securities_import_YYYYMMDD.py`
11. Run `python3 tmp/sbi_securities_import_YYYYMMDD.py review` to show review table
12. User reviews and specifies manual overrides by ID
13. Run `python3 tmp/sbi_securities_import_YYYYMMDD.py sql > tmp/import_sbi_securities.sql` to generate SQL
14. Execute SQL to insert transactions

### USD Stocks (外国株式)

1. Navigate to 外国株式 > 取引照会 > 注文履歴 (`https://member.c.sbisec.co.jp/foreign/refer/us/order-history`)
2. Set period to 2年間 and click 照会
3. For each order, click 詳細 and extract the 約定結果 section
4. Compile into tab-separated format (see USD Stock Input Format below)
5. Copy RAW_DATA_USD_STOCK into `tmp/sbi_securities_import_YYYYMMDD.py`
6. Run `python3 tmp/sbi_securities_import_YYYYMMDD.py review-usd-stock`
7. Run `python3 tmp/sbi_securities_import_YYYYMMDD.py sql-usd-stock > tmp/import_sbi_usd_stock.sql`
8. Execute SQL

### USD Cash (外貨入出金明細)

1. Navigate to 入出金 > 外貨入出金・振替 > 入出金明細
2. Set period and click 照会
3. `agent-browser eval "document.querySelector('body').innerText"` to get data
4. Extract the transaction section
5. Copy RAW_DATA_USD_CASH into `tmp/sbi_securities_import_YYYYMMDD.py`
6. Run `python3 tmp/sbi_securities_import_YYYYMMDD.py review-usd-cash`
7. Run `python3 tmp/sbi_securities_import_YYYYMMDD.py sql-usd-cash > tmp/import_sbi_usd_cash.sql`
8. Execute SQL

## Script Template

- `scripts/sbi_securities_import.py`

## Browser Data Format

### JPY Mutual Funds

Text extracted via `eval "document.querySelector('body').innerText"` from the 取引履歴 page (円貨建口座 tab).

Each transaction spans 6 lines in the extracted text:

```
24/02/02	ｅＭＡＸＩＳ　Ｓｌｉｍ　全世界株式（オール・カントリー）	投信金額買付
NISA(つ)/ --	12,345
21,000	--
--	
24/02/08
50,000	
```

Line breakdown:
- Line 0: `TRADE_DATE\tSECURITY_NAME\tTRANSACTION_TYPE`
- Line 1: `ACCOUNT_TYPE\tQUANTITY`
- Line 2: `UNIT_PRICE\tFEES`
- Line 3: `TAX\t`
- Line 4: `SETTLEMENT_DATE`
- Line 5: `SETTLEMENT_AMOUNT\t`

Notes:
- Trade date format: YY/MM/DD
- Security names use full-width characters
- Transaction types: 投信金額買付 (buy), 投信金額解約 (sell)
- Account types: NISA(つ)/ -- (tsumitate), NISA(成)/ -- (growth), 特定/一般/ -- (specific/general), 特定/ -- (specific)
- Amounts have commas (e.g., 50,000)
- Settlement date format: YY/MM/DD

### USD Stocks

Data compiled from individual order detail pages (注文照会 詳細). The 約定結果 section contains:

```
国内約定日	2026/01/05
国内受渡日	2026/01/07
約定数量	1
平均約定単価	500.0000 USD
約定金額 (外貨)	500.00 USD
手数料/諸経費 (外貨)	2.50 USD
現地取引税等 (外貨)	0.00 USD
課税額 (外貨)	0.25 USD
受渡金額 (外貨)	497.25 USD
```

Notes:
- Access via 外国株式 > 取引照会 > 注文履歴 > 詳細
- URL: `https://member.c.sbisec.co.jp/foreign/refer/us/order-history`
- Each order detail must be opened individually
- Types: 現物売却 (sell), 現物買付 (buy)
- All amounts in USD

### USD Cash

Text extracted from 外貨入出金明細 page. Fields separated by double newlines:

```
2026/01/05

入金

分配金

米ドル

QQQ 銘柄名:インベ QQQ ETF

-

100.00
```

Fields per transaction:
1. Date (YYYY/MM/DD)
2. Type (入金/出金)
3. Category (分配金 or -)
4. Currency (米ドル)
5. Description
6. Withdrawal amount (number or -)
7. Deposit amount (number or -)

## Conversion Rules

### Account Mapping

The GnuCash account is determined by security name + account type:

| Security (Browser) | Account Type | GnuCash Account |
|---------------------|-------------|-----------------|
| ｅＭＡＸＩＳ　Ｓｌｉｍ　全世界株式（オール・カントリー） | NISA(つ) | ...NISA (Periodic Investment):eMAXIS Slim All Countries |
| ｉＦｒｅｅＮＥＸＴ　ＮＡＳＤＡＱ１００インデックス | NISA(つ) | ...NISA (Periodic Investment):iFreeNEXT NASDAQ100 Index |
| ｅＭＡＸＩＳ　Ｓｌｉｍ　全世界株式（オール・カントリー） | NISA(成) | ...NISA (Growth Investment):Entertainment Account:eMAXIS Slim All Countries |
| ｅＭＡＸＩＳ　ＮＡＳＤＡＱ１００インデックス | NISA(成) | ...NISA (Growth Investment):Entertainment Account:eMAXIS NASDAQ100 Index |
| ｅＭＡＸＩＳ　Ｓｌｉｍ　全世界株式（オール・カントリー） | 特定 or 特定/一般 | ...Entertainment Account:eMAXIS Slim All Countries |
| ｅＭＡＸＩＳ　ＮＡＳＤＡＱ１００インデックス | 特定 or 特定/一般 | ...Entertainment Account:eMAXIS NASDAQ100 Index |

### USD Stock Account Mapping

| Ticker | GnuCash Account |
|--------|-----------------|
| QQQ | Assets:USD - Current Assets:Securities:SBI Securities:Entertainment Account:Invesco QQQ Trust Series 1 |
| VGT | Assets:USD - Current Assets:Securities:SBI Securities:Entertainment Account:Vanguard Information Technology Index Fund ETF |

Sell splits (4 splits):
- Fund account: -約定金額
- Cash account (`Assets:USD - Current Assets:Securities:SBI Securities`): +受渡金額
- `Expenses:Fees`: +手数料/諸経費
- `Expenses:Tax:Income Tax`: +課税額

Buy splits (4 splits):
- Fund account: +約定金額
- Cash account: -受渡金額
- `Expenses:Fees`: +手数料/諸経費
- `Expenses:Tax:Income Tax`: +課税額

### USD Cash Account Mapping

| Pattern | GnuCash Account |
|---------|-----------------|
| 分配金 (QQQ or VGT) | Income:Dividend |
| 住信SBIネット銀行へ外貨出金 | Assets:USD - Current Assets:Banks:d NEOBANK:Entertainment Account |
| 外貨預り金（外国為替取引） | Assets:USD - Current Assets:Banks:d NEOBANK:Entertainment Account |

If a transaction does not match any pattern, ask the user.

### Description

All descriptions are set to NULL.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

### JPY Mutual Funds

Same as Browser Data Format. Paste the transaction section directly (from the first trade date line to the last settlement amount line).

Parsing rules:
- Lines matching `YY/MM/DD\t` start a new transaction (line 0)
- Line 1: account type (before \t) and quantity (after \t)
- Line 2: unit price (before \t)
- Line 3: tax (skip)
- Line 4: settlement date
- Line 5: settlement amount (remove commas)

### USD Stocks

Agent compiles data from detail pages into tab-separated format:

```
DATE	TICKER	TYPE	QUANTITY	EXEC_AMOUNT	FEES	TAX	SETTLEMENT
2026/01/05	QQQ	売却	1	500.00	2.50	0.25	497.25
```

### USD Cash

Same as Browser Data Format. Paste the transaction section (fields separated by double newlines).

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Security: Fund name (shortened)
- Type: Buy/Sell
- Account Type: NISA(つ)/NISA(成)/特定
- Desc: Transaction description
- Fund Account: Target GnuCash account (shortened)
- Amount: Settlement amount

## Notes

- The 取引履歴 page shows up to 200 transactions per page with pagination
- Past 2 years of history available for JPY and USD stocks
- Past 5 years of history available for USD cash (外貨入出金明細)
- CSV download is also available but browser text extraction is used for consistency
- Subcommands: `review`/`sql` (JPY), `review-usd-stock`/`sql-usd-stock`, `review-usd-cash`/`sql-usd-cash`
