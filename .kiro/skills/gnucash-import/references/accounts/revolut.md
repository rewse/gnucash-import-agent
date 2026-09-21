# Revolut statement import

Script: `scripts/revolut_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Prepaid:Revolut`
- Currency: JPY

## Access

- Open `https://app.revolut.com/start` with `agent-browser --auto-connect open`; CAPTCHA login is manual.
- Select `すべて表示`, expand each month, and collect the full list with `agent-browser --auto-connect snapshot -i`, scrolling and repeating as needed.

## Statement Data

Each transaction button contains merchant, date, time, JPY amount, and an optional foreign-currency amount. Month headers may be `YYYY年M月` or `M月`.

```text
Example Market 4月3日 15:21 -￥2,060.00 -$12.96
Apple Pay経由でチャージされました 2030年3月26日 14:40 +￥30,000.00
Apple Pay経由でチャージされました 失敗しました · 2030年3月26日 14:39 +￥30,000.00
Example Service 2030年3月26日 13:40 -￥6,256.00 -$39.99
```

Script input is the same, one transaction per line. Preserve status text and both currency amounts:

```text
Example Market 4月3日 15:21 -￥2,060.00 -$12.96
Apple Pay経由でチャージされました 2030年3月26日 14:40 +￥30,000.00
Example Service 2030年3月26日 13:40 -￥6,256.00 -$39.99
```

Dates are `YYYY年M月D日` or `M月D日`; short dates use the current year unless their month is later than the current month. The parser uses the JPY amount, accepts decimals, removes time and amount text from the merchant, and truncates JPY decimals to an integer.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `...経由でチャージされました` or `...経由でお金が追加されました` | `Liabilities:Credit Card:Amazon MasterCard Gold` | `NULL` |
| `カード配送料` | `Expenses:Fees` | `Revolut` |
| `AliExpress` | `Expenses:Groceries` | `AliExpress` |
| Any other merchant | `Expenses:Groceries` | Parsed merchant |

## Source-specific Rules

- Skip rows containing `却下されました`, `失敗しました`, or `取り消されました`, and skip a JPY amount of zero.
- Positive JPY amounts increase Revolut; negative amounts decrease it. Ignore the displayed foreign-currency amount for GnuCash.
- Override overseas travel rows to `Expenses:Entertainment:Travel`; the script does not infer travel from merchant text.
