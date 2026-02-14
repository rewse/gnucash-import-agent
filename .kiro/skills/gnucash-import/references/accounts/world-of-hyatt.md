# World of Hyatt Statement Import

## GnuCash Account

`Assets:JPY - Current Assets:Reward Programs:World of Hyatt`

## Credentials

Passkey is required. You MUST use `agent-browser --headed` and ask the user to input Passkey manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed --args "--disable-blink-features=AutomationControlled" open https://www.hyatt.com/ja-JP/member/sign-in?returnUrl=https://www.hyatt.com/loyalty/ja-JP`
4. User manually logs in with passkey
5. After login, navigate to account activity: `agent-browser open https://www.hyatt.com/profile/ja-JP/account-activity`
6. `agent-browser snapshot -c` to get transaction data
7. Expand entries with the expand button if detail breakdown is needed
8. Prepare RAW_DATA
9. Copy RAW_DATA into `tmp/world_of_hyatt_import_YYYYMMDD.py`
10. Run `python3 tmp/world_of_hyatt_import_YYYYMMDD.py review` to show review table
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/world_of_hyatt_import_YYYYMMDD.py sql > tmp/import_world_of_hyatt.sql` to generate SQL
13. Execute SQL to insert transactions

## Script Template

- `scripts/world_of_hyatt_import.py`

## Browser Data Format

Structured entries on the account activity page at `https://www.hyatt.com/profile/ja-JP/account-activity`. Each entry contains type, hotel name, date range, and points.

Example (from snapshot):
```
滞在 ハイアット リージェンシー 横浜 2月8日 - 2025年2月9日 ポイント 0
滞在 グランド ハイアット シアトル 2月19日 - 2024年2月22日 ポイント 3,000
アワードの交換 ハイアット リージェンシー 横浜 2024年2月15日 交換済み無料宿泊 1
滞在 ハイアット プレイス サンカルロス 2月10日 - 2024年2月14日 ポイント 5,000
```

Notes:
- Hotel names are in Japanese on the activity page; translate to English for descriptions
- Date format varies: "2月8日 - 2025年2月9日" (range) or "2024年2月15日" (single)
- Use the end date of the range as the transaction date
- Kasada bot protection requires `--disable-blink-features=AutomationControlled` flag
- Activity may take up to 72 hours after checkout to appear
- Expanded details show breakdown (base points, bonus points, eligible spend)

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| 滞在 {hotel} (points > 0) | Income:Point Charge | Hotel name in English |
| 滞在 {hotel} (0 points) | (skip) | No point movement |
| アワードの交換 {hotel} (交換済み無料宿泊) | (skip) | Free night certificate, no point movement |
| アワードの交換 {hotel} (points) | Expenses:Entertainment:Travel | Hotel name in English (point redemption) |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format with 4 columns: `{date}\t{description}\t{amount}\t{account}`

```
2024/02/22	Grand Hyatt Seattle	3000	Income:Point Charge
2024/02/14	Hyatt Place San Carlos	5000	Income:Point Charge
```

Parsing rules:
- Date: YYYY/MM/DD (use end date of stay range)
- Amount: positive for points earned, negative for points redeemed (no comma separators)
- Description: hotel name in English
- Account: full GnuCash account path for the transfer account
- Skip rows with 0 points and free night certificate redemptions

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Hotel name in English
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- Unit is pt (World of Hyatt points)
- Transaction currency is JPY (1 point = 0.4 JPY for accounting)
- Hotel names on the activity page are in Japanese; translate to English
