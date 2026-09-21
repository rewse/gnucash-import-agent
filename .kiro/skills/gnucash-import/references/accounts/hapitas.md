# Hapitas statement import

Script: `scripts/hapitas_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:Hapitas`
- Unit: Hapitas points (`pt`)
- Accounting valuation: 1 point = 1 JPY

## Access

- Open `https://hapitas.jp/` with `agent-browser --auto-connect open`; CAPTCHA login is manual.
- Remove obstructing popups with `agent-browser --auto-connect eval "document.querySelectorAll('[class*=modal], [class*=popup], [class*=overlay]').forEach(el => el.remove())"`.
- Open `https://hapitas.jp/bankbook/`; it redirects to the v2 passbook at `https://hapitas.jp/v2/bankbook?tab=pending`.
- Select the `有効` tab with `.filter_tab_valid`, choose `全期間`, and load additional rows with `.advertisement_use_load_more_button` while the visible row count increases.
- Extract each `.advertisement_use_content .advertisement_use_list_row`. If `もっと見る` remains visible but a click no longer increases the row count, keep the rows already returned and report the retrieval limit instead of repeatedly clicking it.

## Statement Data

The v2 `有効` view presents one card per approved entry. Each card contains the confirmed date, service name, recorded date, and points:

```text
2030/04/05
3月分紹介特典
記載日　2030/03/05
12
pt

2030/03/05
2月分紹介特典
記載日　2030/02/05
9
pt
```

Use the confirmed date, shown first in the card, as the script date. Script input is three tab-separated fields: `{date}\t{description}\t{points}`.

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

- Import rows from the `有効` tab only. Do not import `判定中` or `無効` rows.
- Use the confirmed date for new transactions. During duplicate detection, compare both the confirmed date and recorded date because an earlier import may have used either one. Require the quantity, description, and occurrence count to match before treating a nearby-date row as a duplicate.
- The `全期間` view covers the history retained by the site. Treat any retention start shown by the passbook as a retrieval boundary, not as proof that older GnuCash history is complete.
