# Hapitas Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:Hapitas`

## Credentials

CAPTCHA is required at login. Ask the user to log in manually at https://hapitas.jp/ using `agent-browser --headed`.

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://hapitas.jp/`
4. Ask user to log in manually (CAPTCHA required)
5. Remove popups: `agent-browser eval "document.querySelectorAll('[class*=modal], [class*=popup], [class*=overlay]').forEach(el => el.remove())"`
6. Navigate to 通帳: `agent-browser click` on "通帳" link (or `agent-browser open https://hapitas.jp/bankbook/`)
7. Select target month from dropdown and click "検索"
8. `agent-browser snapshot -c -s "table.data-table"` to get transaction data
9. Repeat for additional months as needed
10. Prepare RAW_DATA
11. Copy RAW_DATA into `tmp/hapitas_import_YYYYMMDD.py`
12. Run `python3 tmp/hapitas_import_YYYYMMDD.py review` to show review table
13. User reviews and specifies manual overrides by ID
14. Run `python3 tmp/hapitas_import_YYYYMMDD.py sql > tmp/import_hapitas.sql` to generate SQL
15. Execute SQL to insert transactions

## Script Template

- `scripts/hapitas_import.py`

## Browser Data Format

HTML table at `https://hapitas.jp/bankbook/` with columns: 記載日, 確定日, 広告名・サービス名, 状態, ポイント, 宝くじ交換券, 備考

Example (from snapshot):
```
2026-02-05 2026-02-05 1月分紹介特典 有効 100pt 0 -
2026-01-05 2026-01-05 12月分紹介特典 有効 50pt 0 -
```

Notes:
- Date format: YYYY-MM-DD
- Month selector dropdown with "検索" button to filter
- Radio buttons to switch between 利用日 (usage date) and 確定日 (confirmation date)
- Points shown as `Npt` (e.g., `12pt`)
- Status: 有効 (approved), 判定中 (pending), 無効 (rejected)
- Only import transactions with 有効 status

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| X月分紹介特典 | Income:Point Charge | Hapitas |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 3 columns: `{date}\t{description}\t{points}`

```
2026/02/05	1月分紹介特典	12
2026/01/05	12月分紹介特典	9
```

Parsing rules:
- Date: YYYY/MM/DD
- Points: integer (always positive for earned points)

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Description
- Transfer: Target account
- Increase: Points

## Notes

- Unit is pt (Hapitas points)
- Passbook shows up to ~13 months of history
- Popups may appear on page load; remove them before interacting
