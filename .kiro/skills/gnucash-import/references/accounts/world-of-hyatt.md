# World of Hyatt statement import

Script: `scripts/world_of_hyatt_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:World of Hyatt`
- Valuation: 1 point = 0.4 JPY (`value = points * 2 / 5`, integer floor)

## Access

- Open `https://www.hyatt.com/ja-JP/member/sign-in?returnUrl=https://www.hyatt.com/loyalty/ja-JP` with `agent-browser --auto-connect --args "--disable-blink-features=AutomationControlled" open`; passkey login is manual.
- Open activity with `agent-browser --auto-connect open https://www.hyatt.com/profile/ja-JP/account-activity`, then extract with `agent-browser --auto-connect snapshot -c`.
- Expand entries when the base, bonus, and eligible-spend breakdown is needed. The anti-detection flag is required.

## Statement Data

Entries contain type, Japanese hotel name, date or stay range, and points:

```text
滞在 ハイアット リージェンシー 例示市 4月8日 - 2030年4月9日 ポイント 0
滞在 グランド ハイアット 例示市 3月19日 - 2030年3月22日 ポイント 3,000
アワードの交換 ハイアット リージェンシー 例示市 2030年2月15日 交換済み無料宿泊 1
```

Use the range end date. Translate hotel names to English. Script input is four tab-separated fields: `{date}\t{description}\t{amount}\t{account}`.

```text
2030/03/22	Grand Hyatt Example City	3000	Income:Point Charge
2030/02/14	Hyatt Place Example City	5000	Income:Point Charge
```

Dates use `YYYY/MM/DD`; point amounts may contain commas and retain their sign.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| Stay with positive points | `Income:Point Charge` | English hotel name |
| Stay with 0 points | Skip | None |
| Redeemed free-night certificate | Skip | None |
| Point award redemption | `Expenses:Entertainment:Travel` | English hotel name |

## Source-specific Rules

- Positive points are earned and negative points are redeemed.
- Activity may take up to 72 hours after checkout to appear.
