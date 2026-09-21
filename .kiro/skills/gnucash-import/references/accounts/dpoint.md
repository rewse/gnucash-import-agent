# dPoint statement import

Script: `scripts/dpoint_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:dPoint`
- Valuation: 1 point = 1 JPY

## Access

- Open `https://dpoint.docomo.ne.jp/` with `agent-browser --auto-connect open`; dAccount passkey authentication is manual.
- Open the total-points link, then `ポイント獲得・利用履歴を見る`.
- Select each required month, up to 13 months back, and extract with `agent-browser --auto-connect snapshot -c -d 3`. Filters are `すべて`, `獲得`, `利用`, and `失効`.

## Statement Data

Each entry contains reflection date, full-width description, signed point amount and action, usage date, optional expiry, and optional tags. Preserve the blank lines between fields:

```text
2030/04/29(反映日)
ＣＦ例示店
+34P 獲得
利用日：2030/04/29
ランク判定対象
ポイント倍率アップ特典対象

2030/04/23(反映日)
モスバーガー例示店
-100P 利用
利用日：2030/04/23

2030/04/01(反映日)
失効ポイント
-10P 失効
期間・用途限定
```

Rank bonuses start with `【ｄポイントカード】ポイント倍率アップ特典`; campaigns may start with `（キャンペーン）`. Script input is three tab-separated fields: `{date}\t{description}\t{points}`. Leading tabs are tolerated.

```text
2030/04/29	Ito-Yokado	+34
2030/04/29	Rank Bonus	+17
2030/04/23	Mos Burger	-374
2030/04/01	Point Expiry	-10
```

Descriptions are prepared in English. Commas and leading `+` are accepted.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| Any earned points | `Income:Point Charge` | English merchant name |
| Used at Mos Burger | `Expenses:Foods:Dining` | `Mos Burger` |
| Other usage | User-selected account | English merchant name |
| Expiry | `Expenses:Point Lapse` | `Point Expiry` |

Known translations include `ＡＭＡＺＯＮ．ＣＯ．ＪＰ` and its campaign-prefixed form to `Amazon`, Mos Burger store names to `Mos Burger`, `ＣＦ...店` to `Ito-Yokado`, `鼎泰豐` to `Din Tai Fung`, and `失効ポイント` to `NULL` at extraction time.

## Source-specific Rules

- Positive points are earned; negative points are used or expire.
- Keep base earnings, rank bonuses, and campaign entries as separate transactions.
- `期間・用途限定` points carry an expiry date; rank bonuses are limited-period points.
