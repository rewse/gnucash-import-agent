# Yodobashi Gold Point Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:Yodobashi Gold Point`

## Credentials

- Username: `op://gnucash/Yodobashi Camera/username`
- Password: `op://gnucash/Yodobashi Camera/password`

No CAPTCHA required. You MUST use `agent-browser --headed` with `--args "--disable-blink-features=AutomationControlled"` to avoid WAF blocking.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed --args "--disable-blink-features=AutomationControlled" open "https://order.yodobashi.com/yc/login/index.html?returnUrl=https://www.yodobashi.com/"`
4. Fill username and password from 1Password, click "ログイン"
5. `agent-browser open "https://order.yodobashi.com/yc/mypage/pointhistory/index.html"`
6. `agent-browser snapshot` to get table data; check for pagination ("次のページ" link) and collect all pages
7. For "ポイントご利用" transactions, look up order details from order history or email to determine what was purchased and infer GnuCash account
8. Prepare RAW_DATA with resolved account and item info
9. Copy RAW_DATA into `tmp/yodobashi_gold_point_import_YYYYMMDD.py`
10. Run `python3 tmp/yodobashi_gold_point_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/yodobashi_gold_point_import_YYYYMMDD.py sql > tmp/import_yodobashi_gold_point.sql` to generate SQL
13. Execute SQL to insert transactions

## Script Template

- `scripts/yodobashi_gold_point_import.py`

## Browser Data Format

HTML table with columns: ご利用日, ご利用場所, ステータス, ご利用ゴールドポイント, 取得ゴールドポイント, ゴールドポイント残高, 備考

Example (from snapshot):
```
2026/02/09 13:02  ヨドバシ･ドット･コム  商品購入      -    100  31,791
2026/01/28 01:51  ヨドバシ･ドット･コム  ポイントご利用  4,000  -    31,236
2026/01/23 06:13  GPC+                              -    100  35,341  キャンペーン
2026/01/17 06:28  他ポイントから移行                   -    200  35,031  GPM
```

Notes:
- Date format: YYYY/MM/DD HH:MM
- History shows 3 months from login date (no time range selector)
- Pagination: 20 rows per page, "次のページ" link for more
- Earn and Use are separate columns; "-" means no value
- 備考 column: キャンペーン (campaign bonus), GPM (point migration), or blank

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 商品購入 (earn) | Income:Point Charge | Yodobashi Camera |
| ポイントご利用 (use) | (lookup by order) | Yodobashi Camera |
| GPC+ キャンペーン (earn) | Income:Point Charge | Gold Point Marketing |
| 他ポイントから移行 GPM (earn) | Income:Point Charge | Yodobashi Camera |

### Order Lookup for Usage Transactions

For point usage (ポイントご利用):

1. Check order history at `https://order.yodobashi.com/yc/orderhistory/index.html` to find matching order by date
2. Get product name from order details
3. Infer GnuCash account from product name using [account-guid-cache.json](../account-guid-cache.json)
4. If unclear, ask the user

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 5 columns: `{date}\t{type}\t{description}\t{points}\t{account}`

```
2026/02/09	Earn	Yodobashi Camera	+100	Income:Point Charge
2026/01/28	Use	Yodobashi Camera	-4000	Expenses:Supplies
2026/01/23	Earn	Gold Point Marketing	+100	Income:Point Charge
2026/01/17	Earn	Yodobashi Camera	+200	Income:Point Charge
```

Parsing rules:
- Type is either "Earn" or "Use"
- Points: positive for Earn, negative for Use (comma-separated thousands)
- For Use type, description should include product name for reference

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Type: Earn/Use
- Desc: Description
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- 1 point = 1 JPY
- Point history page shows up to 3 months of transactions
- Anti-detection flag `--disable-blink-features=AutomationControlled` is required to avoid WAF blocking
