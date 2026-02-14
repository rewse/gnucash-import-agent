# Ponta Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:Ponta`

## Credentials

- Username: `op://gnucash/Recruit/username`
- Password: `op://gnucash/Recruit/password`

2FA is required at login (authenticator app). You MUST use `agent-browser --headed` and ask the user to enter the 2FA code manually.

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://point.recruit.co.jp/point/`
4. Click "ログイン", fill username and password from 1Password, click "ログイン"
5. Ask user to enter 2FA code manually, then click "認証する"
6. Close any popup if present (click "閉じる")
7. Navigate to ポイント履歴: click "ポイント通帳" then "ポイント履歴を見る"
8. Select time range from tabs (最近の履歴/今月/先月/先々月) or dropdown (up to 13 months back) based on last imported date
9. `agent-browser snapshot` to get table data
10. Prepare RAW_DATA
11. Copy RAW_DATA into `tmp/ponta_import_YYYYMMDD.py`
12. Run `python3 tmp/ponta_import_YYYYMMDD.py review` to show review table
13. User reviews and specifies manual overrides by ID
14. Run `python3 tmp/ponta_import_YYYYMMDD.py sql > tmp/import_ponta.sql` to generate SQL
15. Execute SQL to insert transactions

## Script Template

- `scripts/ponta_import.py`

## Browser Data Format

HTML table with columns: 日付, 場所, ご利用内容, ポイント

Example (from snapshot):
```
2026年1月25日 ＫＤＤＩ加盟店 エンタメサービスご利用分（Ｎｅｔｆｌｉｘ） お買上げ 100
2026年1月22日 三菱ＵＦＪ銀行 三菱ＵＦＪダイレクトログイン サービスご利用 5
2026年1月14日 ＫＤＤＩ定期付与 マンスリー お買上げ 10
```

Notes:
- Date format: YYYY年M月D日
- Time range: tabs for recent/this month/last month/2 months ago, dropdown for up to 13 months back
- All observed transactions are positive (point earning); negative (point usage) has not been observed but may exist
- 場所 (Place) contains merchant/service name with optional detail in parentheses

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| Any positive points | Income:Point Charge | Use 場所 as description (translated to English) |
| Any negative points | (ask user) | Use 場所 as description (translated to English) |

### Description Translation

Translate 場所 (Place) to English for the transaction description:
- ＫＤＤＩ加盟店 エンタメサービスご利用分（Ｎｅｔｆｌｉｘ） → KDDI
- 三菱ＵＦＪ銀行 三菱ＵＦＪダイレクトログイン → MUFG Bank
- ＫＤＤＩ定期付与 マンスリー → KDDI

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 4 columns: `{date}\t{place}\t{type}\t{points}`

```
2026/01/25	KDDI お買上げ	+100
2026/01/22	MUFG Bank	サービスご利用	+5
2026/01/14	KDDI お買上げ	+10
```

Parsing rules:
- Points: positive for earn, negative for use
- Place should already be translated to English

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
- Login requires Recruit ID (shared with other Recruit services like じゃらん, Hot Pepper, etc.)
- 2FA code must be entered manually by user (1Password OTP field does not work for this service)
