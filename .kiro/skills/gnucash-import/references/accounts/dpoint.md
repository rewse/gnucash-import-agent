# dPOINT Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:dPOINT`

## Credentials

Login via passkey (dAccount). You MUST use `agent-browser --headed` and ask the user to authenticate manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://dpoint.docomo.ne.jp/`
4. Click "dアカウントでログイン", ask user to authenticate via passkey
5. Click on "dポイント合計 Nポイント" link to go to point details
6. Click "ポイント獲得・利用履歴を見る"
7. Select month from dropdown (up to 13 months back) based on last imported date
8. `agent-browser snapshot -c -d 3` to get transaction data
9. Repeat for each month needed
10. Prepare RAW_DATA
11. Copy RAW_DATA into `tmp/d_point_import_YYYYMMDD.py`
12. Run `python3 tmp/d_point_import_YYYYMMDD.py review` to show review table
13. User reviews and specifies manual overrides by ID
14. Run `python3 tmp/d_point_import_YYYYMMDD.py sql > tmp/import_d_point.sql` to generate SQL
15. Execute SQL to insert transactions

## Script Template

- `scripts/d_point_import.py`

## Browser Data Format

Transaction list on the point history page. Each entry contains:

- 反映日 (reflection date): YYYY/MM/DD
- Description: full-width text (merchant name or bonus description)
- Amount: +/-NP 獲得/利用/失効
- 利用日 (usage date): YYYY/MM/DD
- 有効期限 (expiry): YYYY/MM/DD (only for 期間・用途限定 points)
- Tags: 期間・用途限定, ランク判定対象, ポイント倍率アップ特典対象

Example (from snapshot):
```
2026/01/29(反映日)
ＣＦ新宿三丁目店
+34P 獲得
利用日：2026/01/29
ランク判定対象
ポイント倍率アップ特典対象

2026/01/23(反映日)
モスバーガー新宿三丁目店
-100P 利用
利用日：2026/01/23

2026/01/01(反映日)
失効ポイント
-10P 失効
期間・用途限定
```

Notes:
- Month selector dropdown at top of page (up to 13 months back)
- Filter tabs: すべて / 獲得 / 利用 / 失効
- Descriptions use full-width characters (e.g., ＡＭＡＺＯＮ．ＣＯ．ＪＰ)
- Rank bonus entries start with 【ｄポイントカード】ポイント倍率アップ特典
- Campaign entries may be prefixed with （キャンペーン）

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 獲得 (earn, any) | Income:Point Charge | Merchant name (translated to English) |
| 利用 (use): モスバーガー | Expenses:Foods:Dining | Mos Burger |
| 利用 (use): others | (ask user) | Merchant name (translated to English) |
| 失効 (expiry) | Expenses:Point Lapse | Point Expiry |

### Known Merchants

| Browser Text | English Description |
|-------------|-------------------|
| ＡＭＡＺＯＮ．ＣＯ．ＪＰ | Amazon |
| （キャンペーン）ＡＭＡＺＯＮ．ＣＯ．ＪＰ | Amazon |
| モスバーガー新宿三丁目店 | Mos Burger |
| ＣＦ新宿三丁目店 | Ito-Yokado |
| 鼎泰豐 | Din Tai Fung |
| 失効ポイント | null |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 3 columns: `{date}\t{description}\t{points}`

```
2026/01/29	Ito-Yokado	+34
2026/01/29	Rank Bonus	+17
2026/01/23	Mos Burger	-374
2026/01/23	Mos Burger	+9
2026/01/01	Point Expiry	-10
```

Parsing rules:
- Points: positive for earn, negative for use/expiry
- Description should already be translated to English
- Rank bonus and campaign entries are separate transactions (do not merge with the base earn)

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Description (English)
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- 1 point = 1 JPY
- Point history page shows up to 13 months of transactions
- Login requires dAccount (passkey authentication)
- 期間・用途限定 (limited period/purpose) points have an expiry date and expire at end of month
- Rank bonus points are always 期間・用途限定
