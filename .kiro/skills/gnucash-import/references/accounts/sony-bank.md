# Sony Bank Statement Import

Script: [`scripts/sony_bank_import.py`](../../../../../scripts/sony_bank_import.py)

## Accounts

- JPY: `Assets:JPY - Current Assets:Banks:Sony Bank`
- USD: `Assets:USD - Current Assets:Banks:Sony Bank`

## Access

Open `https://sonybank.jp/pages/da/daya010a/?lang=ja` with `agent-browser --auto-connect`, then ask the user to log in manually. Open `通帳 > 普通預金取引履歴`, select a currency (`円`, `米ドル`, `ユーロ`, or `豪ドル`), set the display period, and download the CSV.

The downloaded name is always `FutsuRireki.csv`, regardless of currency. Keep each currency's file distinct in the run workspace and convert it from Shift-JIS to UTF-8 before copying rows into the script:

```bash
iconv -f SHIFT_JIS -t UTF-8 "$work_dir/FutsuRireki.csv" > "$work_dir/statement-utf8.csv"
```

Run the import separately for JPY and USD.

## Statement Data

The JPY CSV has seven columns; USD adds an eighth exchange-rate column:

```csv
"取引日","摘要","参考情報","通貨","預入額","引出額","差引残高"
"2025年2月17日","決算お利息","","JPY","2.000000","","354.000000"
"2025年7月19日","振込 ＥＸＡＭＰＬＥ","","JPY","12345.000000","","67890.000000"
"2025年7月19日","カード再発行手数料（税込）","","JPY","","1650.000000","98704.000000"
```

```csv
"取引日","摘要","参考情報","通貨","預入額","引出額","差引残高","為替レート"
"2025年7月23日","円普通預金より振替","","USD","204.060000","","204.060000","147.010000"
"2025年8月19日","Visaデビット 01　313056　ＥＸＡＭＰＬＥ　ＭＥＲＣＨＡＮＴ","","USD","","120.000000","286.860000",""
```

Paste UTF-8 CSV rows into `RAW_DATA`; the header may be present. Parse CSV quoting rather than splitting literal commas. Fields are date (`YYYY年M月D日`), description, reference, currency, deposit, withdrawal, balance, and optional exchange rate. Empty amounts are zero; signed amount is deposit minus withdrawal. JPY values are converted to denominator 1 and USD values to cents with denominator 100.

## Mapping

Personal self-transfer classification comes from `transfer_rules.sony_bank.self_transfer` in `../personal.json`; use [`../personal.example.json`](../personal.example.json) only as its schema. It applies to JPY descriptions containing `振込` and the configured `contains` value. Do not put personal names or account paths in this document.

### JPY

| Statement pattern | Account | Description |
|---|---|---|
| `カイガイジムテスウリヨウキヤツシユバツク` | `Income:Cash Back` | NULL |
| `デビツトカイガイリヨウキヤツシユバツク` | `Income:Cash Back` | NULL |
| `外貨普通預金（米ドル）へ振替` / `へ振替（積立購入）` | `Assets:USD - Current Assets:Banks:Sony Bank` | NULL |
| `外貨普通預金（米ドル）より振替` | `Assets:USD - Current Assets:Banks:Sony Bank` | NULL |
| `決算お利息` or `決算利息` | `Income:Interest Income` | NULL |

### USD

| Statement pattern | Account | Description |
|---|---|---|
| `円普通預金へ振替` | `Assets:JPY - Current Assets:Banks:Sony Bank` | NULL |
| `円普通預金より振替` / `より振替（デビット01）` / `より振替（積立購入）` | `Assets:JPY - Current Assets:Banks:Sony Bank` | NULL |
| `決算利息` | `Income:Interest Income` | NULL |

Ask for a mapping when no pattern matches. All generated transaction descriptions are NULL.

## Source-specific Rules

- Generated SQL for JPY/USD currency-transfer rows is unsafe to execute unchanged: the script writes both splits' `quantity` in the currency of the current run, including the split for the other-currency account.
- Match the JPY and USD statement sides, then replace their generated rows with one manually constructed transaction. Do not import the mirror side as a second transaction.
- Use one transaction currency and make the two split `value` amounts equal and opposite in that currency. When using JPY as the transaction currency, the JPY-account `value` and `quantity` use the signed JPY statement amount with denominator 1; the USD-account `value` is the exact opposite JPY value with denominator 1, while its `quantity` uses the corresponding signed USD statement cents with denominator 100. Take both statement amounts and their signs from the matched sides rather than deriving a commodity quantity from the script output.
- Visa Debit rows retain the full-width merchant text in the statement description used for review and manual classification.
