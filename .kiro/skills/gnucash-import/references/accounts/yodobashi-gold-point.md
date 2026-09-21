# Yodobashi Gold Point statement import

Script: `scripts/yodobashi_gold_point_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:Yodobashi Gold Point`
- Valuation: 1 point = 1 JPY

## Access

- Open `https://order.yodobashi.com/yc/login/index.html?returnUrl=https://www.yodobashi.com/` with `agent-browser --auto-connect --args "--disable-blink-features=AutomationControlled" open`; credentials are `op://gnucash/Yodobashi Camera/username` and `op://gnucash/Yodobashi Camera/password`.
- Open history with `agent-browser --auto-connect open https://order.yodobashi.com/yc/mypage/pointhistory/index.html`.
- Extract with `agent-browser --auto-connect snapshot`. Collect every 20-row page through `次のページ`. History covers three months.

## Statement Data

Browser columns are `ご利用日`, `ご利用場所`, `ステータス`, `ご利用ゴールドポイント`, `取得ゴールドポイント`, `ゴールドポイント残高`, `備考`:

```text
2030/04/09 13:02  ヨドバシ･ドット･コム  商品購入      -    100  31,790
2030/03/28 01:51  ヨドバシ･ドット･コム  ポイントご利用  4,000  -    31,230
2030/03/23 06:13  GPC+                              -    100  35,340  キャンペーン
2030/03/17 06:28  他ポイントから移行                   -    200  35,030  GPM
```

Earn and use are separate columns; `-` means no value. Balance is cumulative. Script input is five tab-separated fields: `{date}\t{type}\t{description}\t{points}\t{account}`.

```text
2030/04/09	Earn	Yodobashi Camera	+100	Income:Point Charge
2030/03/28	Use	Yodobashi Camera	-4000	Expenses:Supplies
2030/03/23	Earn	Gold Point Marketing	+100	Income:Point Charge
2030/03/17	Earn	Yodobashi Camera	+200	Income:Point Charge
```

`type` is `Earn` or `Use`; points retain their sign, and commas and leading `+` are accepted.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `商品購入`, earned | `Income:Point Charge` | `Yodobashi Camera` |
| `ポイントご利用` | Order-derived account | `Yodobashi Camera` plus product context in input |
| `GPC+` with `キャンペーン` | `Income:Point Charge` | `Gold Point Marketing` |
| `他ポイントから移行` with `GPM` | `Income:Point Charge` | `Yodobashi Camera` |

## Source-specific Rules

- For point usage, open `https://order.yodobashi.com/yc/orderhistory/index.html`, match by date, get the product name, and select an account from `../account-guid-cache.json`. If the order remains unclear, use [`../email-lookup.md`](../email-lookup.md).
- Positive points are earned and negative points are used. Do not copy the cumulative balance into script input.
- The anti-detection browser flag is required.
