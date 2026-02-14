# IHG Rewards Club Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:IHG Rewards Club`

## Credentials

- Username: `op://gnucash/IHG/username`
- Password: `op://gnucash/IHG/password`

## Import Workflow

1. Check if `account-uuid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.ihg.com/hotels/jp/ja/reservation`
4. Click "ログイン", fill username and password from 1Password, click "ログイン"
5. After login, click "Account Home" → "アカウントアクティビティ"
6. Activity page URL: `https://www.ihg.com/rewardsclub/jp/ja/account-mgmt/activity`
7. `agent-browser snapshot -c` to get transaction data
8. Prepare RAW_DATA
9. Copy RAW_DATA into `tmp/ihg_rewards_club_import_YYYYMMDD.py`
10. Run `python3 tmp/ihg_rewards_club_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/ihg_rewards_club_import_YYYYMMDD.py sql > tmp/import_ihg_rewards_club.sql` to generate SQL
13. Execute SQL to insert transactions

## Script Template

- `scripts/ihg_rewards_club_import.py`

## Browser Data Format

Plain text lines on the account activity page at `https://www.ihg.com/rewardsclub/jp/ja/account-mgmt/activity` with format: `{date} {description} {hotel} {points} ポイント`

Example (from snapshot):
```
2025/09/18 対象となるご宿泊 Holiday Inn Istanbul - Old City 1,500 ポイント
2025/08/19 無料宿泊特典 voco Seoul Myeongdong 0 ポイント
2025/07/12 08/13/2025の無料宿泊特典をキャンセル voco Seoul Myeongdong 33,000 ポイント
2025/07/12 2025年08月12日の無料宿泊特典に交換したポイント voco Seoul Myeongdong -34,000 ポイント
```

Notes:
- Date format: YYYY/MM/DD
- Shows past 365 days of activity
- Points may take up to 5 business days to appear after a stay
- Promotional points may take up to 6 weeks
- Transactions with 0 points (無料宿泊特典) represent the stay record only; skip these

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 対象となるご宿泊 {hotel} | Income:Point Charge | Hotel name in English |
| {date}の無料宿泊特典に交換したポイント {hotel} | Expenses:Entertainment:Travel | Hotel name in English |
| {date}の無料宿泊特典をキャンセル {hotel} | Expenses:Entertainment:Travel | Hotel name in English |
| 無料宿泊特典 {hotel} (0 points) | (skip) | No point movement |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 4 columns: `{date}\t{description}\t{amount}\t{account}`

```
2025/09/18	Holiday Inn Istanbul - Old City	1500	Income:Point Charge
2025/07/12	voco Seoul Myeongdong	33000	Expenses:Entertainment:Travel
2025/07/12	voco Seoul Myeongdong	-34000	Expenses:Entertainment:Travel
```

Parsing rules:
- Date: YYYY/MM/DD
- Amount: positive for points earned/refunded, negative for points redeemed (comma-separated thousands)
- Description: hotel name in English
- Account: full GnuCash account path for the transfer account
- Skip rows with 0 points

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Description
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- Unit is pt (IHG One Rewards points)
- Transaction currency is JPY (1 point = 1 JPY for accounting)
- Date format from browser is YYYY/MM/DD
- Hotel names are already in English on the activity page
