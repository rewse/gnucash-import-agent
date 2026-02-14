# ANA Mileage Club Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:ANA Mileage Club`

## Credentials

- Username: `op://gnucash/ANA/username`
- Password: `op://gnucash/ANA/password`

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.ana.co.jp/ja/jp/amc/`
4. Click "ログイン", fill username and password from 1Password, click "ログイン"
5. If a confirmation dialog appears, click "ログイン" again
6. After login, click "マイレージ情報・事後登録" → "マイル口座残高照会" (opens in new tab, switch to it)
7. Statement page URL: `https://cam.ana.co.jp/psz/amcj/jsp/renew/mile/reference.jsp`
8. Default view shows latest transactions; click month links under "過去分（月別）" for older data
9. `agent-browser snapshot -c -s "#meisaitable"` to get transaction table
10. Prepare RAW_DATA
11. Copy RAW_DATA into `tmp/ana_mileage_club_import_YYYYMMDD.py`
12. Run `python3 tmp/ana_mileage_club_import_YYYYMMDD.py review` to show review table
13. User reviews and specifies manual overrides by ID
14. Run `python3 tmp/ana_mileage_club_import_YYYYMMDD.py sql > tmp/import_ana_mileage_club.sql` to generate SQL
15. Execute SQL to insert transactions

## Script Template

- `scripts/ana_mileage_club_import.py`

## Browser Data Format

HTML table (`#meisaitable`) with columns: ご利用日, 便名, 内容, クラス, 運賃種別, 加算マイル, ボーナス, 減算マイル, 合計, プレミアムポイント, 有効期限

Example (from snapshot):
```
2025/09/21  TK 0198  ISTANBUL - TOKYO/HANEDA  M       4,023          4,023  4,023  2028/09
2025/09/16           ＡＮＡカードマイルプラス スターバックス ウェブ    40             40         2028/09
2025/05/20  NH 0879  TOKYO/HANEDA - SYDNEY     U       3,000  1,200  4,200  4,500  2028/05
2025/05/02           ＡＮＡアップグレ－ド                       -25,000  -25,000
2025/12/07           ＡＮＡ ＰＡＹ                              -1,500   -1,500
2026/02/07           ＡＮＡＳＫＹコイン                          -40,000  -40,000
2025/12/02           ＳＦＣ手帳カレンダー送付不要で５００マイル   500              500         2028/12
```

Notes:
- Use the "合計" (total) column as the transaction amount
- For flights, 合計 = 加算マイル + ボーナス
- Pagination: click month links under "過去分（月別）" for older data
- Full-width characters (e.g., ＡＮＡ) are used in content field

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| Flight (NH ####) | Income:Point Charge | ANA |
| Flight (TK ####) | Income:Point Charge | Turkish Airlines |
| Flight (other Star Alliance) | Income:Point Charge | Airline name in English |
| ＡＮＡカードマイルプラス {merchant} | Income:Point Charge | Merchant name in English |
| ＳＦＣ... / other bonus | Income:Point Charge | ANA |
| ＡＮＡ ＰＡＹ | Assets:JPY - Current Assets:Prepaid:ANA Pay | (empty) |
| ＡＮＡＳＫＹコイン | Assets:JPY - Current Assets:Reward Programs:ANA SKY Coin | (empty) |
| ＡＮＡアップグレ－ド | Expenses:Entertainment:Travel | ANA |

### Flight Number to Airline Mapping

| Prefix | Airline |
|--------|---------|
| NH | ANA |
| TK | Turkish Airlines |

For other airline codes, search the web for the English airline name.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 4 columns: `{date}\t{description}\t{amount}\t{account}`

```
2025/09/21	Turkish Airlines	4023	Income:Point Charge
2025/09/16	Starbucks	40	Income:Point Charge
2025/05/20	ANA	4200	Income:Point Charge
2025/05/02	ANA	-25000	Expenses:Entertainment:Travel
2025/12/07		-1500	Assets:JPY - Current Assets:Prepaid:ANA Pay
2026/02/07		-40000	Assets:JPY - Current Assets:Reward Programs:ANA SKY Coin
2025/12/02	ANA	500	Income:Point Charge
```

Parsing rules:
- Amount: positive for miles earned, negative for miles used (comma-separated thousands)
- Description can be empty (for ANA PAY / ANA SKY Coin exchanges)
- Account: full GnuCash account path for the transfer account

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Description
- Transfer: Target account
- Increase/Decrease: Miles

## Notes

- Transaction currency is JPY (1 mile = 1 JPY for accounting)
- Account commodity is ANA (Reward namespace), commodity_scu = 1
- Date format from browser is YYYY/MM/DD
