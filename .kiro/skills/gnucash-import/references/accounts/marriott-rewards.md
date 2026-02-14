# Marriott Rewards Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:Marriott Rewards`

## Credentials

- Username: `op://gnucash/Marriott/username`
- Password: `op://gnucash/Marriott/password`

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://www.marriott.com/`
4. Click "サインインまたは入会する" → "サインイン", fill username and password from 1Password, click "サインイン"
5. After login, navigate to Activity page: `https://www.marriott.com/loyalty/myAccount/activity.mi`
6. Change duration filter to "Last 24 Months" (or appropriate range) to see all transactions since last import
7. `agent-browser snapshot -c` to get transaction data
8. Prepare RAW_DATA
9. Copy RAW_DATA into `tmp/marriott_rewards_import_YYYYMMDD.py`
10. Run `python3 tmp/marriott_rewards_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/marriott_rewards_import_YYYYMMDD.py sql > tmp/import_marriott_rewards.sql` to generate SQL
13. Execute SQL to insert transactions

## Script Template

- `scripts/marriott_rewards_import.py`

## Browser Data Format

Table on the activity page at `https://www.marriott.com/loyalty/myAccount/activity.mi` with columns: POSTED, TYPE, DESCRIPTION, EARNINGS.

Example (from snapshot):
```
Sep 21, 2025 | Bonus | C-EARN 7500 POINTS FOR 1ST STAY | 1,000 Points
Sep 17, 2025 | Hotel Stay | Aloft Dublin City Sep 17, 2025 - Sep 20, 2025 3 Nights | 500 Points (500 Base, 0 Elite, 0 Extra)
Apr 15, 2024 | Rewards | Bonvoy Points to Partner Currency Transfer Award Redeemed: -300 | 300 Points
Apr 15, 2024 | Rewards | 250 Product, Travel, or Service Awards Redeemed: -250 | 250 Points
```

Notes:
- Date format: MMM DD, YYYY (e.g., "Sep 21, 2025")
- Default filter shows last 3 months; change to "Last 24 Months" for full history
- Hotel Stay entries include date range and number of nights, plus Base/Elite/Extra breakdown
- Rewards entries show absolute value in EARNINGS column but "Redeemed: -XXXX" in description indicates deduction
- Page size dropdown can be changed (default 10)

## Conversion Rules

### Transaction Types

| Type | Pattern | GnuCash Account | Description |
|------|---------|-----------------|-------------|
| Bonus | Any bonus description | Income:Point Charge | Marriott |
| Hotel Stay | {hotel_name} {date_range} {nights} | Income:Point Charge | Hotel name in English |
| Rewards | Bonvoy Points to Partner Currency Transfer | Assets:JPY - Current Assets:Reward Programs:Rakuten Super Point | null |
| Rewards | Product, Travel, or Service Awards | Expenses:Social Expenses:Charity | null |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 4 columns: `{date}\t{description}\t{amount}\t{account}`

```
2025/09/21	C-EARN 7500 POINTS FOR 1ST STAY	1000	Income:Point Charge
2025/09/17	Aloft Dublin City	500	Income:Point Charge
2024/04/15	Rakuten Point Transfer	-300	Assets:JPY - Current Assets:Reward Programs:Rakuten Super Point
2024/04/15	Product, Travel, or Service Awards	-250	Expenses:Social Expenses:Charity
```

Parsing rules:
- Date: YYYY/MM/DD
- Amount: positive for points earned, negative for points redeemed
- Description: in English
- Account: full GnuCash account path for the transfer account
- For Rewards type, negate the amount (description shows "Redeemed: -XXXX", use that negative value)

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Description
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- Unit is pt (Marriott Bonvoy points)
- Transaction currency is JPY (1 point = 0.33 JPY for accounting)
- Date format from browser is MMM DD, YYYY (needs conversion to YYYY/MM/DD for script input)
- Hotel names are in English on the activity page
- Points expiration: must earn or redeem within 24 months of last qualifying activity
