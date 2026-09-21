# Amazon Point statement import

Script: `scripts/amazon_point_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:Amazon Point`
- Valuation: 1 point = 1 JPY

## Access

- Open `https://www.amazon.co.jp/Amazon%E3%83%9D%E3%82%A4%E3%83%B3%E3%83%88/b/?ie=UTF8&node=2632478051` with `agent-browser --auto-connect open`; passkey authentication is manual.
- Open `マイポイントページへ`, then extract the table with `agent-browser --auto-connect snapshot`.
- Use the date filter and click `次のページ` for older rows. Order numbers are embedded in `注文詳細を見る` links.

## Statement Data

Browser columns are `日付`, `項目`, `リンク`, `種類`, `ポイント`:

```text
2030/04/13 商品名 1.5L 8本 注文詳細を見る お買い物ポイント +22 ＊獲得予定
2030/04/13 ポイントの利用 注文詳細を見る 利用・キャンセル -1,500
2030/04/12 セールス・イベント ポイントアップキャンペーン(3月1日 - 3月9日) 調整分 ボーナスポイント +35 期間限定
2030/04/09 コンビニでのAmazon Mastercardご利用分 (1.5%ポイント還元) Amazon Mastercard +93
```

Script input is five tab-separated fields: `{date}\t{description}\t{type}\t{points}\t{account}`.

```text
2030/04/13	ポイントの利用 123-2345678-3456789	Use	-1500	Expenses:Groceries
2030/04/12	セールス・イベント ポイントアップキャンペーン 調整分	Earn	+35	Income:Point Charge
2030/04/09	コンビニでのAmazon Mastercardご利用分	Earn	+93	Income:Point Charge
```

`type` is `Earn` or `Use`. Points retain their sign; commas are accepted. Every row remains an independent transaction.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `お買い物ポイント`, `ボーナスポイント`, campaign events | `Income:Point Charge` | `Amazon` |
| Any Amazon Mastercard variant | `Income:Point Charge` | `Amazon` |
| `利用・キャンセル` with `ポイントの利用` | Order-derived account | `Amazon` |

Amazon Mastercard variants include Amazon purchases, convenience-store purchases, non-Amazon purchases, convenience-store campaigns, and Amazon Prime Mastercard offers.

## Source-specific Rules

- Import `＊獲得予定` rows; they are confirmed later.
- Follow the order-details link, get the product name, and select an available account from `../account-guid-cache.json`. If the page omits product names, use [`../email-lookup.md`](../email-lookup.md).
- Positive points are earned and negative points are used.
