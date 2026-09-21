# Amazon Gift Certificate statement import

Script: `scripts/amazon_gc_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Prepaid:Amazon Gift Certificate`
- Currency: JPY

## Access

- Open `https://www.amazon.co.jp/gp/css/gc/balance` with `agent-browser --auto-connect open`; passkey authentication is manual.
- Extract the table with `agent-browser --auto-connect snapshot`.
- Click `次へ` for older history. Order numbers in descriptions link to order details.

## Statement Data

Browser columns are `日付`, `利用内容`, `金額`, `残高`:

```text
2030年4月22日 Amazon Pay (シリアル番号1234567890123456)からのギフトカード ￥120 ￥8,720
2030年4月18日 ギフトカードが追加されました ギフトカード番号: xxxx-xxxxxx-AB1C; シリアル番号:2345678901234567 ￥730 ￥8,600
2030年4月9日 Amazon Payの注文に適用されたギフトカード P03-1234567-2345678 -￥9,200 ￥7,870
2030年4月3日 Amazon.co.jpの注文に適用されたギフトカード 123-2345678-3456789 -￥6,400 ￥17,070
2030年3月21日 Amazon.co.jp注文へ適応されたギフトカードの解除 234-3456789-4567890 ￥3,100 ￥23,470
```

Script input is six tab-separated fields: `{date}\t{description}\t{amount}\t{balance}\t{account}\t{item}`. Keep an empty final item field for charges.

```text
2030年4月9日	Amazon Payの注文に適用されたギフトカード P03-1234567-2345678	-￥5,000	￥7,870	Expenses:Groceries	コーヒー豆 1kg
2030年4月9日	Amazon Payの注文に適用されたギフトカード P03-1234567-2345678	-￥4,200	￥7,870	Expenses:Books	本
```

Dates use `YYYY年M月D日`; amounts retain `￥`, commas, and signs. The parser groups rows by date, description, and balance, so repeated rows form one transaction with multiple splits.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `Amazon.co.jpの注文に適用されたギフトカード` | Order-derived account | `Amazon` |
| `Amazon Payの注文に適用されたギフトカード` | Order-derived account | `Amazon Pay` |
| `Amazon Pay...からのギフトカード` | `Income:Cash Back` | `Amazon Pay` |
| `ギフトカードが追加されました` | `Income:Part-Time` by default | Item field, otherwise `NULL` |
| `注文へ適応されたギフトカードの解除` | Order-derived account | `Amazon` |

## Source-specific Rules

- Positive amounts charge the gift certificate; negative amounts pay from it.
- For payment and refund rows, open `https://payments.amazon.co.jp/jr/your-account/orders/{order_number}` for `P03-xxxxxxx-xxxxxxx`, or `https://www.amazon.co.jp/gp/your-account/order-details?orderID={order_number}` for Amazon.co.jp orders. Use the product name to select the account.
- If an order page omits product names, use [`../email-lookup.md`](../email-lookup.md).
