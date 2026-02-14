# ANA SKY Coin Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:ANA SKY Coin`

## Credentials

- Username: `op://gnucash/ANA/username`
- Password: `op://gnucash/ANA/password`

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.ana.co.jp/ja/jp/amc/`
4. Click "ログイン", fill username and password from 1Password, click "ログイン"
5. If a confirmation dialog appears, click "ログイン" again
6. Navigate to `https://cam.ana.co.jp/psz/amcj/jsp/renew/ecoupon/ecouponReference.jsp`
7. If prompted to log in again on cam.ana.co.jp, fill the same credentials
8. Default view shows latest transactions; click month links under "過去分（月別）" for older data
9. `agent-browser snapshot -c -s "#meisaitable"` to get transaction table
10. Prepare RAW_DATA
11. Copy RAW_DATA into `tmp/ana_sky_coin_import_YYYYMMDD.py`
12. Run `python3 tmp/ana_sky_coin_import_YYYYMMDD.py review` to show review table
13. User reviews and specifies manual overrides by ID
14. Run `python3 tmp/ana_sky_coin_import_YYYYMMDD.py sql > tmp/import_ana_sky_coin.sql` to generate SQL
15. Execute SQL to insert transactions

## Script Template

- `scripts/ana_sky_coin_import.py`

## Browser Data Format

HTML table (`#meisaitable`, summary="Utilization particulars") with columns: ご利用日, 内容, 使用, 追加, 有効期限

Example (from snapshot):
```
2026/01/15  航空券購入  -30,000
2026/01/10  ＡＮＡ ＳＫＹ コイン 入金  50,000  2027年01月末
2025/06/20  ＡＮＡアップグレードポイントからＡＮＡ ＳＫＹ コイン交換  5,000  2026年06月末
```

Notes:
- "使用" column contains negative amounts (deductions)
- "追加" column contains positive amounts (additions)
- A transaction has a value in either "使用" or "追加", not both
- "使用" amounts have a clickable detail link
- Full-width characters (e.g., ＡＮＡ) are used in content field
- Pagination: click month links under "過去分（月別）" for older data

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 航空券購入 | Expenses:Entertainment:Travel | ANA |
| ＡＮＡ ＳＫＹ コイン 入金 | Assets:JPY - Current Assets:Reward Programs:ANA Mileage Club | (empty) |
| ＡＮＡアップグレードポイントからＡＮＡ ＳＫＹ コイン交換 | Income:Point Charge | ANA |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 4 columns: `{date}\t{description}\t{amount}\t{account}`

```
2026/01/15	ANA	-30000	Expenses:Entertainment:Travel
2026/01/10		50000	Assets:JPY - Current Assets:Reward Programs:ANA Mileage Club
2025/06/20	ANA	5000	Income:Point Charge
```

Parsing rules:
- Amount: positive for coins added, negative for coins used (comma-separated thousands)
- Description can be empty (for mile-to-coin deposits)
- Account: full GnuCash account path for the transfer account

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Description
- Transfer: Target account
- Increase/Decrease: Coins

## Notes

- Transaction currency is JPY (1 coin = 1 JPY for accounting)
- Account commodity is ANA SKY Coin (Reward namespace), commodity_scu = 1
- Date format from browser is YYYY/MM/DD
