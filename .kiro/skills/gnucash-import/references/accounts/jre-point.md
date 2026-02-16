# JRE Point Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:JRE Point`

## Credentials

- Second Password: `op://gnucash/JRE POINT/password`

Passkey is required. You MUST use `agent-browser --headed` and ask the user to input Passkey manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. Ask the user to log in to https://www.jrepoint.jp/ using JRE ID and complete SMS authentication
4. Once logged in, `agent-browser --headed open https://www.jrepoint.jp/member/pointlog/`
5. Second password page appears — fill from 1Password (`op://gnucash/JRE POINT/password`) and click 再認証
6. Navigate months using 前の月/次の月 links based on last imported date
7. `agent-browser snapshot` to get table data for each month
8. Prepare RAW_DATA
9. Copy RAW_DATA into `tmp/jre_point_import_YYYYMMDD.py`
10. Run `python3 tmp/jre_point_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/jre_point_import_YYYYMMDD.py sql > tmp/import_jre_point.sql` to generate SQL
13. Execute SQL to insert transactions

## Script Template

- `scripts/jre_point_import.py`

## Browser Data Format

HTML table with columns: (channel), ポイント反映日, 利用場所, 内容, ポイント

The page displays one month at a time, navigated by 前の月/次の月 links. URL pattern: `/member/pointlog/?move=prev&selectMonth=YYYYMM`

Example (from snapshot):
```
アプリ 2026年01月16日 ビューカード ビューカードご利用分 +100
アプリ 2026年01月02日 JRE POINT JRE BANKプラス（2025年12月付与分） +15
アプリ 2025年11月13日 ルミネ新宿 スティーブンアラン １１／１３ お買い物 +10
アプリ 2025年10月07日 アトレ目黒 無印良品 １０／７ お買い物 +10
```

Notes:
- Date format: YYYY年MM月DD日
- Points: +N for earn, -N for use
- 利用場所 can be: ビューカード, JRE POINT, or store name (e.g., アトレ目黒 無印良品)
- 内容 describes the transaction detail
- Channel column (アプリ etc.) is not used for mapping

## Conversion Rules

### Transaction Types

| Pattern | Type | GnuCash Account | Description |
|---------|------|-----------------|-------------|
| ビューカードご利用分 | Earn | Income:Point Charge | VIEW CARD |
| JRE BANKプラス | Earn | Income:Point Charge | JRE BANK |
| お買い物 | Earn | Income:Point Charge | (store name from 利用場所) |
| Suicaチャージ | Use | Assets:JPY - Current Assets:Prepaid:Suica iPhone | null |
| Other use | Use | (ask user) | (ask user) |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 4 columns: `{date}\t{location}\t{detail}\t{points}`

```
2026/01/16	ビューカード	ビューカードご利用分	+100
2026/01/02	JRE POINT	JRE BANKプラス（2025年12月付与分）	+15
2025/11/13	ルミネ新宿 スティーブンアラン	１１／１３ お買い物	+10
```

Parsing rules:
- Points: positive for Earn, negative for Use (no comma separators expected for typical amounts)
- Date: YYYY/MM/DD

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Location: 利用場所
- Detail: 内容
- Desc: Transaction description
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- 1 point = 1 JPY
- Point history is monthly; navigate with 前の月/次の月
- Second password is required to access point history (re-authentication)
- SMS OTP is required at login; user must complete login manually
