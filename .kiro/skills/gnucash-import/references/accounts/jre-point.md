# JRE Point statement import

Script: `scripts/jre_point_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:JRE Point`
- Valuation: 1 point = 1 JPY

## Access

- Open `https://www.jrepoint.jp/` with `agent-browser --auto-connect open`; passkey and SMS authentication are manual.
- Open `https://www.jrepoint.jp/member/pointlog/`, enter the second password from `op://gnucash/JRE POINT/password`, and select `再認証`.
- Extract each month with `agent-browser --auto-connect snapshot`. Navigate with `前の月` and `次の月`; URLs use `/member/pointlog/?move=prev&selectMonth=YYYYMM`.

## Statement Data

Browser columns are `(channel)`, `ポイント反映日`, `利用場所`, `内容`, `ポイント`:

```text
アプリ 2030年04月16日 ビューカード ビューカードご利用分 +100
アプリ 2030年04月02日 JRE POINT JRE BANKプラス（2030年03月付与分） +15
アプリ 2030年03月13日 ルミネ例示店 ストア名 ３／１３ お買い物 +10
```

The channel is not used for mapping. Script input is four tab-separated fields: `{date}\t{location}\t{detail}\t{points}`.

```text
2030/04/16	ビューカード	ビューカードご利用分	+100
2030/04/02	JRE POINT	JRE BANKプラス（2030年03月付与分）	+15
2030/03/13	ルミネ例示店 ストア名	３／１３ お買い物	+10
```

Dates use `YYYY/MM/DD`; points retain their sign. Commas and leading `+` are accepted.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `ビューカードご利用分` | `Income:Point Charge` | `VIEW CARD` |
| `JRE BANKプラス` | `Income:Point Charge` | `JRE BANK` |
| `お買い物` | `Income:Point Charge` | `利用場所` |
| Other positive row | `Income:Point Charge` | `利用場所` |
| `Suicaチャージ` | `Assets:JPY - Current Assets:Prepaid:Suica iPhone` | `NULL` |
| Other negative row | User-selected account | User-selected English description |

## Source-specific Rules

- Positive points are earned and negative points are used.
- Point history is monthly and requires second-password reauthentication.
