# Mobile Suica Statement Import

## GnuCash Account

`Root Account:Assets:JPY - Current Assets:Prepaid:Suica iPhone`

## Credentials

CAPTCHA is required. You MUST use `agent-browser --headed` and ask the user to input CAPTCHA manually.

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.mobilesuica.com/`
4. Manual login (CAPTCHA required)
5. Click "SF（電子マネー） 利用履歴"
6. `agent-browser snapshot` to get table data
7. Prepare RAW_DATA
8. Copy RAW_DATA into `tmp/suica_import_YYYYMMDD.py`
9. Run `python3 tmp/suica_import_YYYYMMDD.py review` to show review table
10. User reviews and specifies manual overrides by ID
11. Run `python3 tmp/suica_import_YYYYMMDD.py sql > tmp/import_suica.sql` to generate SQL
12. Execute SQL to insert transactions

## Script Template

- `scripts/suica_import.py`

## Browser Data Format

HTML table with columns: 月日, 種別, 利用場所, 種別, 利用場所, 残額, 入金・利用額

Example (white-space separated text from snapshot):
```
月日 種別 利用場所 種別 利用場所 残額 入金・利用額
01/28 入 目黒 出 新宿 4,822 -178
01/26 物販 5,000 -590
01/21 ｵｰﾄ 新宿 5,590 +5,000
01/18 入 地 渋谷 出 北参道 590 -178
11/25 繰 768
```

Notes:
- Station names with prefix (地, 都) may or may not have a space (e.g., "地 新宿" or "地麻布十")
- 繰 (carried balance) rows have no amount

## Conversion Rules

### Transaction Types

| 種別 | Meaning | GnuCash Account | Description |
|------|---------|-----------------|-------------|
| 入/出 | Train entry/exit | Expenses:Transit or Expenses:Business Expenses | Railway company |
| ＊入 | Transfer entry | Expenses:Transit or Expenses:Business Expenses | Railway company |
| 物販 | Shopping | Expenses:Foods:Dining (default) | NULL (ask user for merchant if known) |
| ｵｰﾄ | Auto-charge | Liabilities:Credit Card:LUMINE CARD | NULL |
| 繰 | Carried balance | (skip) | - |

### Business Expense Detection

On weekdays, if the following pattern appears on the same day, classify ALL transit transactions on that day as `Expenses:Business Expenses`:

1. {nearest_station} → 地 新宿
2. 新宿 → 目黒
3. 目黒 → 新宿
4. 地 新宿 → {nearest_station} (Optional)

See [references/personal.md](references/personal.md) for the nearest station.

Rules:
- Check all transit transactions on the same date, not just sequential ones
- 物販 or ｵｰﾄ transactions do not affect the pattern
- If pattern matches, ALL transit transactions on that day become business expenses

### Railway Company Detection

Determine railway company from entry station:

1. Check station-specific mappings first (see below)
2. Check station name prefix:
   - `地` prefix → Tokyo Metro
   - `都` prefix → Toei Subway
   - `ゆ` prefix → Yurikamome
   - No prefix → JR (default)

#### Station-Specific Mappings

Stations without prefix that are NOT JR:

| Station | Railway |
|---------|---------|
| 溜池山王 | Tokyo Metro |
| 赤坂見附 | Tokyo Metro |
| 南大沢 | Keio |

Add new stations here when discovered.

### Description Format

For train/bus rides, use the railway/bus company name in English:
- JR
- Tokyo Metro
- Toei Subway
- Keio
- Tokyo Monorail
- Toei Bus

For 物販 (shopping) and ｵｰﾄ (auto-charge), set description to NULL unless user specifies a merchant name.

## Script Input Format

Same as Browser Data Format, but without header row and 残額 column:
```
01/28 入 目黒 出 新宿 -178
01/26 物販 -590
01/21 ｵｰﾄ 新宿 +5000
01/18 入 地 渋谷 出 北参道 -178
11/25 繰
```

Parsing rules:
- Split by whitespace
- Skip 繰 (carried balance) rows
- Skip rows with amount 0
- Amount is the last numeric value

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Purpose: "駅名 → 駅名" for transit, "物販" for shopping, "オート" for auto-charge
- Desc: Railway company or merchant name (becomes transaction description in GnuCash)
- Transfer: Target account
- Increase/Decrease: Amount

## Notes

- Year is not shown; infer from current date (if month > current month, use previous year)
- Balance column is cumulative; use amount column for actual transaction value
- Always show review table before inserting to database
- User can specify manual overrides by ID for account and/or description
