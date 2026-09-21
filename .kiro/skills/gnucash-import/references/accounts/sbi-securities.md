# SBI Securities Statement Import

Script: [`scripts/sbi_securities_import.py`](../../../../../scripts/sbi_securities_import.py)

## Accounts

### JPY mutual funds

- Transfer: `Liabilities:A/Payable:SBI Securities`
- `Assets:JPY - Current Assets:Securities:SBI Securities:Entertainment Account:eMAXIS NASDAQ100 Index`
- `Assets:JPY - Current Assets:Securities:SBI Securities:Entertainment Account:eMAXIS Slim All Countries`
- `Assets:JPY - Current Assets:Securities:SBI Securities:NISA (Growth Investment):Entertainment Account:eMAXIS NASDAQ100 Index`
- `Assets:JPY - Current Assets:Securities:SBI Securities:NISA (Growth Investment):Entertainment Account:eMAXIS Slim All Countries`
- `Assets:JPY - Current Assets:Securities:SBI Securities:NISA (Periodic Investment):eMAXIS Slim All Countries`
- `Assets:JPY - Current Assets:Securities:SBI Securities:NISA (Periodic Investment):iFreeNEXT NASDAQ100 Index`

A buy moves value from the payable account to the fund on the trade date; a sell reverses those sides. The SBI Hyper Deposit settlement against the payable account is imported separately on the settlement date.

### USD stocks and cash

- Cash: `Assets:USD - Current Assets:Securities:SBI Securities`
- `Assets:USD - Current Assets:Securities:SBI Securities:Entertainment Account:Invesco QQQ Trust Series 1`
- `Assets:USD - Current Assets:Securities:SBI Securities:Entertainment Account:Vanguard Information Technology Index Fund ETF`
- Fees: `Expenses:Fees`
- Tax: `Expenses:Tax:Income Tax`

## Access

Open `https://login.sbisec.co.jp/login/entry` with `agent-browser --auto-connect`, then ask the user to complete passkey authentication.

For JPY mutual funds, open `口座管理 > 取引履歴`, set the date range, click `照会`, and extract `document.querySelector('body').innerText`. Capture every page with `次へ→`.

For USD stocks, open `外国株式 > 取引照会 > 注文履歴` at `https://member.c.sbisec.co.jp/foreign/refer/us/order-history`, select `2年間`, and open each order's `詳細` page. Import only completed orders whose detail page contains `約定結果`; exclude `注文中` rows and any order without executed quantity and settlement results.

For USD cash, open `入出金 > 外貨入出金・振替 > 入出金明細`, select `5年`, set the page size to `200件`, and extract `document.querySelector('body').innerText`. The result can include rows whose currency is `-` or another non-USD value; retain only rows whose currency column is exactly `米ドル`.

## Statement Data

### JPY mutual funds

Each transaction from the `円貨建口座` tab occupies six lines:

```text
24/02/02	ｅＭＡＸＩＳ　Ｓｌｉｍ　全世界株式（オール・カントリー）	投信金額買付
NISA(つ)/ --	12,345
21,000	--
--	
24/02/08
50,000	
```

The lines are: `TRADE_DATE\tSECURITY_NAME\tTRANSACTION_TYPE`; `ACCOUNT_TYPE\tQUANTITY`; `UNIT_PRICE\tFEES`; `TAX\t`; settlement date; `SETTLEMENT_AMOUNT\t`. Dates use `YY/MM/DD`; amounts may contain commas. Transaction types are `投信金額買付` and `投信金額解約`. Account types include `NISA(つ)/ --`, `NISA(成)/ --`, `特定/一般/ --`, and `特定/ --`.

Paste all six lines per row into `RAW_DATA_JPY`. The parser uses the trade date for posting, derives buy/sell signs from the transaction type, reads quantity from line 2 and settlement amount from line 6, and normalizes non-NISA account types to `特定`.

### USD stocks

Each detail page includes domestic trade and settlement dates, quantity, execution price and amount, fees, local transaction tax, taxable amount, and settlement amount:

```text
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

Compile the required fields into `RAW_DATA_USD_STOCK` as tab-separated rows. `DATE` is the domestic trade date:

```text
DATE	TICKER	TYPE	QUANTITY	EXEC_AMOUNT	FEES	TAX	SETTLEMENT
2026/01/05	QQQ	売却	1	500.00	2.50	0.25	497.25
```

Types may be `現物売却` or `現物買付`; the parser detects a sell when the type contains `売`. All monetary fields are USD.

### USD cash

The extracted fields are separated by blank lines and occur in groups of seven: date, type, category, currency, description, withdrawal, deposit.

```text
2026/01/05

入金

分配金

米ドル

QQQ 銘柄名:インベ QQQ ETF

-

100.00
```

Paste this shape into `RAW_DATA_USD_CASH`. Dates use `YYYY/MM/DD`; type is `入金` or `出金`; category is `分配金` or `-`; an absent amount is `-`. The parser accepts only groups whose currency field is exactly `米ドル` and ignores all other currency values.

## Mapping

### JPY funds

| Security text | Account type | Account suffix |
|---|---|---|
| `ｅＭＡＸＩＳ　ＮＡＳＤＡＱ１００インデックス` | `NISA(成)` | `NISA (Growth Investment):Entertainment Account:eMAXIS NASDAQ100 Index` |
| `ｅＭＡＸＩＳ　ＮＡＳＤＡＱ１００インデックス` | `特定` or `特定/一般` | `Entertainment Account:eMAXIS NASDAQ100 Index` |
| `ｅＭＡＸＩＳ　Ｓｌｉｍ　全世界株式（オール・カントリー）` | `NISA(つ)` | `NISA (Periodic Investment):eMAXIS Slim All Countries` |
| `ｅＭＡＸＩＳ　Ｓｌｉｍ　全世界株式（オール・カントリー）` | `NISA(成)` | `NISA (Growth Investment):Entertainment Account:eMAXIS Slim All Countries` |
| `ｅＭＡＸＩＳ　Ｓｌｉｍ　全世界株式（オール・カントリー）` | `特定` or `特定/一般` | `Entertainment Account:eMAXIS Slim All Countries` |
| `ｉＦｒｅｅＮＥＸＴ　ＮＡＳＤＡＱ１００インデックス` | `NISA(つ)` | `NISA (Periodic Investment):iFreeNEXT NASDAQ100 Index` |

All suffixes are below `Assets:JPY - Current Assets:Securities:SBI Securities`.

### USD stocks

| Ticker | Account |
|---|---|
| `QQQ` | `Assets:USD - Current Assets:Securities:SBI Securities:Entertainment Account:Invesco QQQ Trust Series 1` |
| `VGT` | `Assets:USD - Current Assets:Securities:SBI Securities:Entertainment Account:Vanguard Information Technology Index Fund ETF` |

For a sell, the fund split is `-EXEC_AMOUNT`, cash is `+SETTLEMENT`, fees are `+FEES`, and tax is `+TAX`. For a buy, the fund split is `+EXEC_AMOUNT`, cash is `-SETTLEMENT`, and fees and tax remain positive expense splits. Omit zero fee or tax splits. The documented inputs must balance according to the broker's settlement arithmetic.

### USD cash

| Statement pattern | Account |
|---|---|
| Category `分配金` | `Income:Dividend` |
| Description contains `住信SBI` | `Assets:USD - Current Assets:Banks:DOCOMO SMTB Net Bank:Entertainment Account` |
| Description contains `外貨預り金` | `Assets:USD - Current Assets:Banks:DOCOMO SMTB Net Bank:Entertainment Account` |

Ask for a mapping when a ticker, fund, or cash pattern is unknown. All generated transaction descriptions are NULL.

## Source-specific Rules

- JPY fund split: `value_num = signed settlement amount`, `value_denom = 1`, `quantity_num = signed units × 10000`, and `quantity_denom = 10000`. The payable split has the opposite value and uses `quantity_num = value_num`, denominator 1.
- USD stock split: `value_num = signed execution amount × 100`, `value_denom = 100`, `quantity_num = signed shares × 10000`, and `quantity_denom = 10000`. Cash, fee, and tax splits use cents for both value and quantity with denominator 100.
- USD cash splits use signed cents for both value and quantity with denominator 100.
- For JPY fund duplicate detection, when an exact trade-date match is absent but prior import is confirmed, compare the same fund account, signed settlement value, and exact unit quantity within a bounded nearby-date window.
- For USD stock duplicate detection, a single broker order may already be split across multiple SBI Securities subaccounts. Aggregate only matching ticker splits within the bounded date window and require both signed share quantity and execution value to equal the order detail before excluding it as a duplicate.
- Never import an order without `約定結果`; recheck open or unfilled orders on a later run.
- Available history is two years for JPY funds and USD stock orders, and five years for USD cash.
- Source-specific commands are `review` and `sql` for JPY funds, `review-usd-stock` and `sql-usd-stock` for USD stocks, and `review-usd-cash` and `sql-usd-cash` for USD cash.
