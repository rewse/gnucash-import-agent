# Bic Point Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:Bic Point`

## Credentials

- Username: `op://gnucash/Bic Camera/username`
- Password: `op://gnucash/Bic Camera/password`

CAPTCHA is required at login. You MUST use `agent-browser --headed` with `--args "--disable-blink-features=AutomationControlled"` and ask the user to complete the CAPTCHA manually.

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed --args "--disable-blink-features=AutomationControlled" open https://www.biccamera.com/bc/member/SfrLogin.jsp`
4. Fill username and password from 1Password, ask user to complete CAPTCHA, then click "ログインする"
5. `agent-browser open https://www.biccamera.com/bc/member/MemBcPointHistory.jsp`
6. Select time range from dropdown (3ヶ月以内 / 6ヶ月以内 / 1年以内) based on last imported date
7. `agent-browser snapshot` to get table data
8. For "利用ポイント" transactions, look up order details via "詳しく見る" link to get product name and infer GnuCash account
9. Prepare RAW_DATA with resolved account and item info
10. Copy RAW_DATA into `tmp/bic_point_import_YYYYMMDD.py`
11. Run `python3 tmp/bic_point_import_YYYYMMDD.py review` to show review table
12. User reviews and specifies manual overrides by ID
13. Run `python3 tmp/bic_point_import_YYYYMMDD.py sql > tmp/import_bic_point.sql` to generate SQL
14. Execute SQL to insert transactions

## Script Template

- `scripts/bic_point_import.py`

## Browser Data Format

HTML table with columns: ポイント獲得（利用）日, ポイントご利用内容, ご注文番号/購入店舗, 獲得ポイント, 利用ポイント, ご購入の詳細

Example (from snapshot):
```
2026年1月18日 店舗でのご購入 ビックカメラ 渋谷東口店 100 - 詳しく見る
2025年12月31日 ビックカメラ.comにてご注文 1104521833 50 - 詳しく見る
2025年12月31日 ビックカメラ.comにてご注文 1104521833 - 5,000 詳しく見る
2025年12月21日 ビックカメラ.comにてご注文 1103984740 200 - 詳しく見る
2025年11月22日 ビックカメラ.comにてご注文 1102971845 30 - 詳しく見る
```

Notes:
- Date format: YYYY年M月D日
- Filter dropdown: 3ヶ月以内 (default), 6ヶ月以内, 1年以内
- Earn and Use are separate columns; "-" means no value
- Same order number can appear in both earn and use rows

## Conversion Rules

### Transaction Types

| Pattern | Type | GnuCash Account | Description |
|---------|------|-----------------|-------------|
| 店舗でのご購入 (earn) | Earn | Income:Point Charge | Bic Camera |
| ビックカメラ.comにてご注文 (earn) | Earn | Income:Point Charge | Bic Camera |
| 店舗でのご購入 (use) | Use | (ask user) | Bic Camera |
| ビックカメラ.comにてご注文 (use) | Use | (lookup by order) | Bic Camera |

### Order Lookup for Usage Transactions

For online order usage (ビックカメラ.comにてご注文 with 利用ポイント):

1. Click "詳しく見る" link to view order details
2. Get product name from order details page
3. Infer GnuCash account from product name using [account-uuid-cache.json](../account-uuid-cache.json)

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 5 columns: `{date}\t{type}\t{description}\t{points}\t{account}`

```
2026/01/18	Earn	店舗でのご購入 ビックカメラ 渋谷東口店	+100	Income:Point Charge
2025/12/31	Earn	ビックカメラ.comにてご注文 1104521833	+50	Income:Point Charge
2025/12/31	Use	ビックカメラ.comにてご注文 1104521833 電池	-5000	Expenses:Electronics
2025/12/21	Earn	ビックカメラ.comにてご注文 1103984740	+200	Income:Point Charge
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
- Point history page shows up to 1 year of transactions
- Anti-detection flag `--disable-blink-features=AutomationControlled` is required to avoid WAF blocking
