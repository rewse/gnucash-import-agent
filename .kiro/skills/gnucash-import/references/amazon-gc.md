# Amazon Gift Certificate Statement Import

## Statement URL

https://www.amazon.co.jp/gp/css/gc/balance

## Credentials

Passkey is required. You MUST use `agent-browser --headed` and ask the user to input Passkey manually.

## GnuCash Account

`Assets:JPY - Current Assets:Prepaid:Amazon Gift Certificate`

## Import Workflow

1. Check if `accounts.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.amazon.co.jp/gp/css/gc/balance`
4. Manual login
5. `agent-browser snapshot` to get table data
6. For Payment/Refund transactions, look up order details to get product name and infer GnuCash account
7. Prepare RAW_DATA with resolved account and item info
8. Copy RAW_DATA into `tmp/amazon_gc_import_YYYYMMDD.py`
9. Run `python3 tmp/amazon_gc_import_YYYYMMDD.py review` to show review table
10. User reviews and specifies manual overrides by ID
11. Run `python3 tmp/amazon_gc_import_YYYYMMDD.py sql > tmp/import_amazon_gc.sql` to generate SQL
12. Execute SQL to insert transactions

## Script Template

`scripts/amazon_gc_import.py`

## Browser Data Format

HTML table with columns: 日付, 利用内容, 金額, 残高

Example (from snapshot):
```
日付 利用内容 金額 残高
2026年1月22日 Amazon Pay (シリアル番号2740994645346952)からのギフトカード ￥130 ￥8,730
2026年1月18日 ギフトカードが追加されました ギフトカード番号: xxxx-xxxxxx-W9CT; シリアル番号:2755412458412522 ￥754 ￥8,600
2026年1月9日 Amazon Payの注文に適用されたギフトカード P03-2347286-7139572 -￥19,250 ￥7,846
2026年1月3日 Amazon.co.jpの注文に適用されたギフトカード 250-9968976-8812605 -￥12,607 ￥46,346
2025年11月21日 Amazon.co.jp注文へ適応されたギフトカードの解除 503-9249217-7916650 ￥3,693 ￥70,453
```

Notes:
- Pagination: Click "次へ" to load more history
- Order numbers in description are links to order details

## Conversion Rules

### Transaction Types

| Pattern | Type | GnuCash Account | Description |
|---------|------|-----------------|-------------|
| Amazon.co.jpの注文に適用されたギフトカード | Payment | (lookup by order) | Amazon |
| Amazon Payの注文に適用されたギフトカード | Payment | (lookup by order) | Amazon Pay |
| Amazon Pay...からのギフトカード | Charge | Income:Cash Back | Amazon Pay |
| ギフトカードが追加されました | Charge | Income:Part-Time (default) | NULL (ask user for merchant if known) |
| 注文へ適応されたギフトカードの解除 | Refund | (lookup by order) | Amazon |

### Order Lookup for Payment/Refund Transactions

For "Amazon.co.jpの注文に適用されたギフトカード", "Amazon Payの注文に適用されたギフトカード", and "注文へ適応されたギフトカードの解除":

1. Extract order number from description (e.g., `P03-2347286-7131234` or `250-1234567-1234567`)
2. Look up order details via browser to get product name
3. Infer GnuCash account from product name

#### Order Lookup URLs

- Amazon Pay orders (P03-xxxxxxx-xxxxxxx): `https://payments.amazon.co.jp/jr/your-account/orders/{order_number}`
- Amazon.co.jp orders (xxx-xxxxxxx-xxxxxxx): `https://www.amazon.co.jp/gp/your-account/order-details?orderID={order_number}`

#### Email Lookup for Missing Information

If order details page doesn't show product names, search emails. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 6 columns: `{date}\t{description}\t{amount}\t{balance}\t{account}\t{item}`

```
2026年1月22日	Amazon Pay (シリアル番号2740994645341234)からのギフトカード	￥130	￥8,730	Income:Cash Back	
2026年1月9日	Amazon Payの注文に適用されたギフトカード P03-2347286-7131234	-￥10,000	￥7,846	Expenses:Groceries	コーヒー豆 1kg
2026年1月9日	Amazon Payの注文に適用されたギフトカード P03-2347286-7131234	-￥9,250	￥7,846	Expenses:Books	本
```

- account: GnuCash account path (inferred from product name)
- item: Product name from order lookup (empty for Charge transactions)

Note: Orders often contain multiple items with different accounts, resulting in transactions:splits = 1:N relationship. For multi-item orders, you MUST write multiple rows with the same description and balance. Rows with identical description + balance are grouped into a single transaction with multiple splits.

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference. For multi-split transactions, use sub-numbers (e.g., 1-1, 1-2)
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Type: Charge/Payment/Refund
- Item: For Payment or Refund type, show item name from order lookup
- Desc: Merchant Name
- Transfer: Target account
- Increase/Decrease: Amount

Example for multi-split transaction:
```
ID    Date        Type     Item            Desc        Transfer             Decrease
1     2026-01-09  Payment                  Amazon Pay                       ￥19,250
1-1     (Sat)               コーヒー豆 1kg             Expenses:Groceries   ￥10,000
1-2                         本                         Expenses:Books        ￥9,250
```

## Notes

- Date is in Japanese format (YYYY年M月D日)
- Amount sign indicates direction (positive = charge, negative = payment)
