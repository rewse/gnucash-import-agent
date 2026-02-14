# Rakuten Super Point Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:Rakuten Super Point`

## Credentials

- Username/Password: `op://gnucash/Rakuten`

No CAPTCHA or OTP required.

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open 'https://login.account.rakuten.com/sso/authorize?client_id=rakuten_ichiba_top_web&service_id=s245&response_type=code&scope=openid&redirect_uri=https://www.rakuten.co.jp/#/sign_in'`
4. Fill username from 1Password (`op://gnucash/Rakuten/username`), click 次へ
5. Fill password from 1Password (`op://gnucash/Rakuten/password`), click 次へ
6. After login, `agent-browser open 'https://point.rakuten.co.jp/history/'`
7. Default view shows last 7 months. If older data is needed, click さらに絞り込む and change the date range
8. `agent-browser snapshot` to get transaction data
9. Prepare RAW_DATA
10. Copy RAW_DATA into `tmp/rakuten_super_point_import_YYYYMMDD.py`
11. Run `python3 tmp/rakuten_super_point_import_YYYYMMDD.py review` to show review table
12. User reviews and specifies manual overrides by ID
13. Run `python3 tmp/rakuten_super_point_import_YYYYMMDD.py sql > tmp/import_rakuten_super_point.sql` to generate SQL
14. Execute SQL to insert transactions

## Script Template

- `scripts/rakuten_super_point_import.py`

## Browser Data Format

HTML table with columns: 日付, サービス, 内容, ポイント利用・獲得, 備考

The page displays up to 7 months by default. Older data requires clicking さらに絞り込む to change the date range.

Example (from snapshot):
```
2026 02/04 | 楽天ポイントカード | ケンタッキーフライドチキン○○店 によるポイント付与 [2026/02/02] ランクアップ対象 | 獲得 | 3
2026 01/22 | 楽天マガジン | 楽天マガジン [2026/01/02] ランクアップ対象 | 獲得 | 5
2026 01/02 | 楽天マガジン | 楽天マガジン でポイント利用 [2026/01/02] | 利用 | 100
2025 10/22 | 楽天市場 購入履歴 | ○○ショップ でお買い物 [2025/10/21] 詳細 ランクアップ対象 | 獲得 | 130
2025 10/04 | 楽天キャッシュ | 2025年9月 楽天キャッシュご利用分のポイント獲得 [2025/10/03] ランクアップ対象 | 獲得 | 1
2025 08/10 | アフィリエイト | 楽天アフィリエイト成果報酬【楽天キャッシュ】2025年06月度 [2025/08/10] | チャージ キャッシュ | 200
```

Notes:
- Date format: YYYY MM/DD
- Points: always a positive number; the type column (獲得/利用/チャージ キャッシュ) determines direction
- 内容 may contain store name, date in brackets, and ランクアップ対象 tag
- The actual transaction date is in brackets within 内容 (e.g., [2026/02/02])

## Conversion Rules

### Transaction Types

| Type | Service Pattern | GnuCash Account | Description |
|------|----------------|-----------------|-------------|
| 獲得 | 楽天ポイントカード | Income:Point Charge | (store name from 内容, in English) |
| 獲得 | 楽天マガジン | Income:Point Charge | Rakuten Magazine |
| 獲得 | 楽天市場 | Income:Point Charge | (shop name from 内容, in English) |
| 獲得 | 楽天キャッシュ | Income:Point Charge | Rakuten Cash |
| 利用 | 楽天マガジン | Expenses:Entertainment:Books | Rakuten Magazine |
| 利用 | Other | (ask user) | (ask user) |
| チャージ キャッシュ | アフィリエイト | Special: source=Rakuten Cash, counter=Income:Part-Time | Rakuten Affiliate |

### Special: チャージ キャッシュ Transactions

For チャージ キャッシュ transactions, the source account is `Assets:JPY - Current Assets:Prepaid:Rakuten Cash` (NOT Rakuten Super Point), and the counter account is `Income:Part-Time`.

### Store Name Mapping

Extract store name from 内容 and convert to English:
- ケンタッキーフライドチキン○○店 → KFC
- カレーハウスCoCo壱番屋○○店 → CoCo Ichibanya
- ロイヤルホスト ○○店 → Royal Host
- STEVEN ALAN SHINJUKU → Steven Alan
- For 楽天市場 shops, use the shop name before でお買い物 (e.g., "adidas Online Shop 楽天市場店" → "adidas")
- If store name is unclear, ask the user

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 6 columns: `{date}\t{service}\t{detail}\t{type}\t{points}\t{desc}`

```
2026/02/04	楽天ポイントカード	ケンタッキーフライドチキン○○店 によるポイント付与 [2026/02/02]	獲得	3	KFC
2026/01/22	楽天マガジン	楽天マガジン [2026/01/02]	獲得	5	Rakuten Magazine
2026/01/02	楽天マガジン	楽天マガジン でポイント利用 [2026/01/02]	利用	100	Rakuten Magazine
2025/08/10	アフィリエイト	楽天アフィリエイト成果報酬【楽天キャッシュ】2025年06月度 [2025/08/10]	チャージ	200	Rakuten Affiliate
```

Parsing rules:
- Date: YYYY/MM/DD
- Type: 獲得 (earn, positive), 利用 (use, negative), チャージ (cash charge, special handling)
- Points: always positive integer; sign determined by type
- Desc: English description, prepared by agent when building RAW_DATA (see Store Name Mapping)
- Strip ランクアップ対象, 詳細, and extra whitespace from detail

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Service: サービス name
- Detail: 内容 (abbreviated)
- Desc: Transaction description (English)
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- 1 point = 1 JPY
- Default view shows last 7 months; use さらに絞り込む for older data
- Page shows all transactions at once (no monthly navigation needed within the 7-month window)
- GnuCash account name for DB queries: 'Rakuten Super Point'
