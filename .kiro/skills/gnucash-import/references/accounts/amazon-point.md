# Amazon Point Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:Amazon Point`

## Credentials

Passkey is required. You MUST use `agent-browser --headed` and ask the user to input Passkey manually.

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.amazon.co.jp/Amazon%E3%83%9D%E3%82%A4%E3%83%B3%E3%83%88/b/?ie=UTF8&node=2632478051`
4. Manual login
5. Click "マイポイントページへ" to navigate to point history
6. `agent-browser snapshot` to get table data
7. For "利用・キャンセル" transactions, look up order details to get product name and infer GnuCash account from [account-uuid-cache.json](../account-uuid-cache.json)
8. Prepare RAW_DATA with resolved account and item info
9. Copy RAW_DATA into `tmp/amazon_point_import_YYYYMMDD.py`
10. Run `python3 tmp/amazon_point_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/amazon_point_import_YYYYMMDD.py sql > tmp/import_amazon_point.sql` to generate SQL
13. Execute SQL to insert transactions

## Script Template

`scripts/amazon_point_import.py`

## Browser Data Format

HTML table with columns: 日付, 項目, リンク, 種類, ポイント

Example (from snapshot):
```
日付 項目 リンク 種類 ポイント
2026/02/13 キリン ソルティライチ 1.5L 8本 注文詳細を見る お買い物ポイント +22 ＊獲得予定
2026/02/13 ポイントの利用 注文詳細を見る 利用・キャンセル -1,500
2026/02/12 セールス・イベント ポイントアップキャンペーン(11月21日 - 12月1日) 調整分 ボーナスポイント +35 期間限定
2026/02/09 コンビニでのAmazon Mastercardご利用分 (1.5%ポイント還元) Amazon Mastercard +93
2026/02/09 Amazon以外でのAmazon Mastercardご利用分 Amazon Mastercard +41
2026/02/09 ポイントの利用 注文詳細を見る 利用・キャンセル -3,000
```

Notes:
- Pagination: Click "次のページ" to load more history
- Date filter dropdown available to select time range
- "期間限定" suffix indicates limited-time points
- Order numbers are embedded in "注文詳細を見る" links

## Conversion Rules

### Transaction Types

| Pattern | Type | GnuCash Account | Description |
|---------|------|-----------------|-------------|
| お買い物ポイント | Earn | Income:Point Charge | Amazon |
| ボーナスポイント | Earn | Income:Point Charge | Amazon |
| Amazon Mastercard | Earn | Income:Point Charge | Amazon |
| 利用・キャンセル (ポイントの利用) | Use | (lookup by order) | Amazon |

### Order Lookup for Usage Transactions

For "利用・キャンセル" with "ポイントの利用":

1. Extract order URL from "注文詳細を見る" link
2. Look up order details via browser to get product name
3. Infer GnuCash account from product name using [account-uuid-cache.json](../account-uuid-cache.json) as reference for available accounts

#### Order Lookup URL

Extract from the snapshot link, e.g.: `https://www.amazon.co.jp/gp/your-account/order-details?orderID={order_number}`

### Email Lookup for Missing Information

If order details page doesn't show product names, search emails. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 5 columns: `{date}\t{description}\t{type}\t{points}\t{account}`

```
2026/02/13	ポイントの利用 250-1234567-1234567	Use	-1500	Expenses:Groceries
2026/02/12	セールス・イベント ポイントアップキャンペーン 調整分	Earn	+35	Income:Point Charge
2026/02/09	コンビニでのAmazon Mastercardご利用分	Earn	+93	Income:Point Charge
2026/02/09	Amazon以外でのAmazon Mastercardご利用分	Earn	+41	Income:Point Charge
2026/02/09	ポイントの利用 250-9876543-7654321	Use	-3000	Expenses:Books
```

Parsing rules:
- Type is either "Earn" or "Use"
- Points: positive for Earn, negative for Use (comma-separated thousands)
- For Use type, description should include order number for reference
- For multi-item orders, write multiple rows with the same date and order number; rows with identical date + description are grouped into a single transaction with multiple splits

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference. For multi-split transactions, use sub-numbers (e.g., 1-1, 1-2)
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Type: Earn/Use
- Desc: Description
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- Date format from browser is YYYY/MM/DD
- 1 point = 1 JPY
