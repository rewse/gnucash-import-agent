# Starbucks Card statement import

Script: `scripts/starbucks_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Prepaid:Starbucks`
- Currency: JPY

## Access

- Open `https://login.starbucks.co.jp/login` with `agent-browser --auto-connect open`; credentials are `op://gnucash/Starbucks/username` and `op://gnucash/Starbucks/password`.
- Open history with `agent-browser --auto-connect open https://sbcard.starbucks.co.jp/card/history`, then extract with `agent-browser --auto-connect snapshot`.
- The page loads about four months of history without pagination.

## Statement Data

Items are grouped by `YYYY年MM月`; each item has a description line followed by an amount and date line:

```text
2030年04月
オートチャージ
¥2,000 2030/04/27
モバイルオーダー&ペイ
- ¥481 2030/04/27
例示店
- ¥496 2030/03/19
他社ポイント交換
¥4,000 2030/02/25
```

Script input is three tab-separated fields: `{description}\t{amount}\t{date}`.

```text
オートチャージ	¥2,000	2030/04/27
モバイルオーダー&ペイ	- ¥481	2030/04/27
例示店	- ¥496	2030/03/19
他社ポイント交換	¥4,000	2030/02/25
```

Preserve the `- ` prefix in source examples. The parser removes `¥`, commas, and spaces; dates use `YYYY/MM/DD`.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `オートチャージ` | `Liabilities:Credit Card:ANA Super Flyers Gold Card` | `NULL` |
| Any other row, including mobile order, store payment, and point exchange | `Expenses:Foods:Dining` | `Starbucks` |

## Source-specific Rules

- Positive amounts charge the card; negative amounts pay from it.
- Use a manual override when a non-auto-charge row is not dining.
