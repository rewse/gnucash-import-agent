# Hapitas statement import

Script: `scripts/hapitas_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:Hapitas`
- Unit: Hapitas points (`pt`)
- Accounting valuation: 1 point = 1 JPY

## Access

- Open `https://hapitas.jp/` with `agent-browser --auto-connect open`; CAPTCHA login is manual.
- Remove obstructing popups with `agent-browser --auto-connect eval "document.querySelectorAll('[class*=modal], [class*=popup], [class*=overlay]').forEach(el => el.remove())"`.
- Open `通帳` with `agent-browser --auto-connect open https://hapitas.jp/bankbook/`, select a month and `利用日` or `確定日`, click `検索`, then extract with `agent-browser --auto-connect snapshot -c -s "table.data-table"`.

## Statement Data

Browser columns are `記載日`, `確定日`, `広告名・サービス名`, `状態`, `ポイント`, `宝くじ交換券`, `備考`:

```text
2030-04-05 2030-04-05 3月分紹介特典 有効 12pt 0 -
2030-03-05 2030-03-05 2月分紹介特典 判定中 9pt 0 -
```

Statuses are `有効`, `判定中`, or `無効`; import only `有効`. Script input is three tab-separated fields: `{date}\t{description}\t{points}`.

```text
2030/04/05	3月分紹介特典	12
2030/03/05	2月分紹介特典	9
```

Dates use `YYYY/MM/DD`; points are positive integers and may contain commas.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `X月分紹介特典` | `Income:Point Charge` | `Hapitas Referral` |

## Source-specific Rules

- Import approved rows only.
- The passbook covers about 13 months.
