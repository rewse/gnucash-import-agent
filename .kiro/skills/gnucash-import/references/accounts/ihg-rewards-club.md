# IHG Rewards Club statement import

Script: `scripts/ihg_rewards_club_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:IHG Rewards Club`
- Valuation: 1 point = 0.5 JPY (`value = points * 1 / 2`, integer floor)

## Access

- Open `https://www.ihg.com/hotels/jp/ja/reservation` with `agent-browser --auto-connect open`; credentials are `op://gnucash/IHG/username` and `op://gnucash/IHG/password`.
- Open `Account Home`, then `アカウントアクティビティ`, or `https://www.ihg.com/rewardsclub/jp/ja/account-mgmt/activity`.
- Extract with `agent-browser --auto-connect snapshot -c`. Activity covers the past 365 days.

## Statement Data

The page emits `{date} {description} {hotel} {points} ポイント` lines:

```text
2030/04/18 対象となるご宿泊 Holiday Inn Example City 1,500 ポイント
2030/03/19 無料宿泊特典 voco Example Central 0 ポイント
2030/02/12 03/13/2030の無料宿泊特典をキャンセル voco Example Central 33,000 ポイント
2030/02/12 2030年03月12日の無料宿泊特典に交換したポイント voco Example Central -34,000 ポイント
```

Script input is four tab-separated fields: `{date}\t{description}\t{amount}\t{account}`.

```text
2030/04/18	Holiday Inn Example City	1500	Income:Point Charge
2030/02/12	voco Example Central	33000	Expenses:Entertainment:Travel
2030/02/12	voco Example Central	-34000	Expenses:Entertainment:Travel
```

Dates use `YYYY/MM/DD`; amounts may contain commas. Skip zero-point rows.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| Eligible stay | `Income:Point Charge` | English hotel name |
| Points exchanged for a free-night award | `Expenses:Entertainment:Travel` | English hotel name |
| Free-night award cancellation | `Expenses:Entertainment:Travel` | English hotel name |
| Free-night stay record with 0 points | Skip | None |

## Source-specific Rules

- Positive points are earned or refunded; negative points are redeemed.
- Stay points may post within five business days; promotions may take six weeks.
