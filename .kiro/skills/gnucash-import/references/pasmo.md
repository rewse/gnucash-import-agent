# Mobile PASMO Statement Import

## Statement URL

https://www.mobile.pasmo.jp/

## Credentials

CAPTCHA is required. You MUST use `agent-browser --headed` and ask the user to input CAPTCHA manually.

## GnuCash Account

`Assets:JPY - Current Assets:Prepaid:PASMO Kayano`

## Import Workflow

1. Check if `accounts.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.mobile.pasmo.jp/
4. Manual login (CAPTCHA required)
5. Click "次へ"
6. Click "SF（電子マネー） 利用履歴"
7. `agent-browser snapshot` to get table data
8. Prepare RAW_DATA
9. Copy RAW_DATA into `tmp/pasmo_import_YYYYMMDD.py`
10. Run `python3 tmp/pasmo_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/pasmo_import_YYYYMMDD.py sql > tmp/import_pasmo.sql` to generate SQL
13. Execute SQL to insert transactions

## Script Template

- `scripts/suica_import.py` (same format as Mobile Suica)

## Source Table Structure

Columns from Mobile PASMO website:
- 月日: Date (MM/DD format)
- 種別: Type (入/出/＊入/物販/ｵｰﾄ/繰)
- 利用場所: Entry station
- 種別: Type (出 for exit)
- 利用場所: Exit station
- 残額: Balance after transaction
- 入金・利用額: Amount (+charge / -expense)

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Purpose: "駅名 → 駅名" for transit, "物販" for shopping, "オート" for auto-charge
- Desc: Railway company or merchant name (becomes transaction description in GnuCash)
- Transfer: Target account
- Increase/Decrease: Amount

## Data Parsing

Raw data format from browser snapshot:
```
01/28 入 目黒 出 新宿 -178
01/26 物販 -590
01/21 ｵｰﾄ 新宿 +5000
01/18 入 地 渋谷 出 北参道 -178
11/25 繰
```

Parsing rules:
- Split by whitespace
- Station names with prefix (地, 都) may or may not have a space (e.g., "地 新宿" or "地麻布十")
- Skip 繰 (carried balance) rows
- Skip rows with amount 0
- Amount is the last numeric value

## Transaction Types

| 種別 | Meaning | GnuCash Account | Description |
|------|---------|-----------------|-------------|
| 入/出 | Train entry/exit | Expenses:Transit or Expenses:Business Expenses | Railway company |
| ＊入 | Transfer entry | Expenses:Transit or Expenses:Business Expenses | Railway company |
| 物販 | Shopping | Assets:JPY - Current Assets:Reimbursement:Kayano (default) | Vending Machine (default) |
| ｵｰﾄ | Auto-charge | Liabilities:Credit Card:TOKYU CARD ClubQ JMB | NULL |
| 繰 | Carried balance | (skip) | - |

## Railway Company Detection

Determine railway company from entry station:

1. Check station-specific mappings first (see below)
2. Check station name prefix:
   - `地` prefix → Tokyo Metro
   - `都` prefix → Toei Subway
   - `ゆ` prefix → Yurikamome
   - No prefix → JR (default)

### Station-Specific Mappings

Stations without prefix that are NOT JR:

| Station | Railway |
|---------|---------|
| 溜池山王 | Tokyo Metro |
| 赤坂見附 | Tokyo Metro |
| 南大沢 | Keio |

Add new stations here when discovered.

## Description Format

For train/bus rides, use the railway/bus company name in English:
- JR
- Tokyo Metro
- Toei Subway
- Keio
- Tokyo Monorail
- Toei Bus

For 物販 (shopping) and ｵｰﾄ (auto-charge), set description to NULL unless user specifies a merchant name.

## Notes

- Year is not shown; infer from current date (if month > current month, use previous year)
- Balance column is cumulative; use amount column for actual transaction value
- Always show review table before inserting to database
- User can specify manual overrides by ID for account and/or description
