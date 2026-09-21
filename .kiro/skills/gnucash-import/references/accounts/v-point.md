# V Point statement import

Script: `scripts/v_point_import.py` (`review`, `sql`)

## Accounts

- Regular source: `Assets:JPY - Current Assets:Reward Programs:V Point`
- Store-limited source: `Assets:JPY - Current Assets:Reward Programs:V Point - ANA Mileage Transferable Points`
- Valuation: 1 point = 1 JPY

## Access

- Open `https://tsite.jp/tm/pc/login/STKIp0001001.do` with `agent-browser --auto-connect open`; Yahoo! JAPAN email or SMS authentication is manual.
- Complete cookie consent, log in, open `マイページ` then `ポイント履歴`, and select `利用日順`.
- Extract with `agent-browser --auto-connect snapshot -c`. Click `もっと見る` and repeat for additional rows. History covers up to three years; the alternative sort is `反映日順`.

## Statement Data

Each transaction is a paragraph containing date, description, points, and optional tags. Preserve quoted negative point lines and blank lines:

```text
2030/04/25
三井住友カード カードご利用分 ＡＮＡ ＶＩＳＡゴールド
15 pt
ストア限定

2030/03/31
Ｖポイント
"-50 pt"
失効
期間限定

2030/04/11
三井住友カード ＶポイントＰａｙ残高チャージ（ポイント優先払い）
"-500 pt"
```

Tags include `ストア限定`, `期間限定`, and `失効`, and may be combined. Script input is tab-separated `{date}\t{description}\t{points}\t{tags}`; keep the empty description or tags field with adjacent or trailing tabs.

```text
2030/04/11		-515
2030/04/25	SMBC Card	15	ストア限定
2030/03/31		-50	失効,期間限定
2030/03/13	Yoshinoya	3
```

Dates use `YYYY/MM/DD`; points are signed integers and may contain commas. Tags are comma-separated; descriptions are prepared in English or left empty.

## Mapping

| Statement pattern | Source / transfer account | Description |
|---|---|---|
| `ストア限定` | Store-limited source / normal transfer mapping | As below |
| Other tags, including `期間限定` | Regular source / normal transfer mapping | As below |
| Positive points | Selected source / `Income:Point Charge` | English description |
| `失効` | Selected source / `Expenses:Point Lapse` | `NULL` |
| Negative points with an empty description | Selected source / `Assets:JPY - Current Assets:Prepaid:V Point Pay` | `NULL` |
| Other negative points | Selected source / user-selected account | English description |

Known translations include SMBC Card earnings and prepaid-charge benefits to `SMBC Card`, V Point Pay balance charge to an empty description, Seven Mile exchange to `Seven Eleven`, return points to `V POINT`, and Yoshinoya and Lotteria to their English names.

## Source-specific Rules

- `ストア限定` selects the ANA Mileage Transferable Points source account. `期間限定` alone remains in the regular account.
- Positive points are earned; negative points are used or expire.
