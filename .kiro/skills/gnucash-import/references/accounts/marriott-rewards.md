# Marriott Rewards statement import

Script: `scripts/marriott_rewards_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:Marriott Rewards`
- Valuation: 1 point = 0.33 JPY (`value = points * 33 / 100`, integer floor)

## Access

- Open `https://www.marriott.com/` with `agent-browser --auto-connect open`; credentials are `op://gnucash/Marriott/username` and `op://gnucash/Marriott/password`.
- Open `https://www.marriott.com/loyalty/myAccount/activity.mi` and change the duration to `Last 24 Months` when needed.
- Extract with `agent-browser --auto-connect snapshot -c`. The default duration is three months and the default page size is 10.

## Statement Data

Browser columns are `POSTED`, `TYPE`, `DESCRIPTION`, `EARNINGS`:

```text
Apr 21, 2030 | Bonus | C-EARN 7500 POINTS FOR 1ST STAY | 1,000 Points
Apr 17, 2030 | Hotel Stay | Example Hotel Apr 17, 2030 - Apr 20, 2030 3 Nights | 500 Points (500 Base, 0 Elite, 0 Extra)
Mar 15, 2030 | Rewards | Bonvoy Points to Partner Currency Transfer Award Redeemed: -300 | 300 Points
Mar 15, 2030 | Rewards | 250 Product, Travel, or Service Awards Redeemed: -250 | 250 Points
```

Rewards show an absolute `EARNINGS` value; `Redeemed: -N` in the description supplies the negative sign. Script input is four tab-separated fields: `{date}\t{description}\t{amount}\t{account}`.

```text
2030/04/21	C-EARN 7500 POINTS FOR 1ST STAY	1000	Income:Point Charge
2030/04/17	Example Hotel	500	Income:Point Charge
2030/03/15	Rakuten Point Transfer	-300	Assets:JPY - Current Assets:Reward Programs:Rakuten Super Point
2030/03/15	Product, Travel, or Service Awards	-250	Expenses:Social Expenses:Charity
```

Input dates use `YYYY/MM/DD`; amounts may contain commas.

## Mapping

| Type and pattern | GnuCash account | Description |
|---|---|---|
| Bonus | `Income:Point Charge` | Bonus description |
| Hotel Stay | `Income:Point Charge` | English hotel name |
| Partner Currency Transfer award | `Assets:JPY - Current Assets:Reward Programs:Rakuten Super Point` | `NULL` |
| Product, Travel, or Service award | `Expenses:Social Expenses:Charity` | `NULL` |

## Source-specific Rules

- Positive points are earned and rewards are negative redemptions.
- Hotel rows include a date range, nights, and Base/Elite/Extra breakdown; use the posted date for script input.
- Points expire after 24 months without qualifying earn or redemption activity.
