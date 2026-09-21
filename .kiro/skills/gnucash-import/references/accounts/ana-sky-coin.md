# ANA SKY Coin statement import

Script: `scripts/ana_sky_coin_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:ANA SKY Coin`
- Commodity: ANA SKY Coin reward units, `commodity_scu = 1`
- Accounting valuation: 1 coin = 1 JPY

## Access

- Open `https://www.ana.co.jp/ja/jp/amc/` with `agent-browser --auto-connect open`; credentials are `op://gnucash/ANA/username` and `op://gnucash/ANA/password`.
- After login, open `https://cam.ana.co.jp/psz/amcj/jsp/renew/ecoupon/ecouponReference.jsp` and authenticate again if prompted.
- Extract with `agent-browser --auto-connect snapshot -c -s "#meisaitable"`. Click month links under `過去分（月別）` for older data.

## Statement Data

The `#meisaitable` table (`summary="Utilization particulars"`) has `ご利用日`, `内容`, `使用`, `追加`, `有効期限` columns:

```text
2030/04/15  航空券購入  -30,000
2030/04/10  ＡＮＡ ＳＫＹ コイン 入金  50,000  2031年04月末
2030/03/20  ＡＮＡアップグレードポイントからＡＮＡ ＳＫＹ コイン交換  5,000  2031年03月末
```

Each row has a value in either `使用` or `追加`; usage values are negative and link to details. Preserve full-width characters. Script input is four tab-separated fields: `{date}\t{description}\t{amount}\t{account}`; use adjacent tabs for an empty description.

```text
2030/04/15	ANA	-30000	Expenses:Entertainment:Travel
2030/04/10		50000	Assets:JPY - Current Assets:Reward Programs:ANA Mileage Club
2030/03/20	ANA	5000	Income:Point Charge
```

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `航空券購入` | `Expenses:Entertainment:Travel` | `ANA` |
| `ＡＮＡ ＳＫＹ コイン 入金` | `Assets:JPY - Current Assets:Reward Programs:ANA Mileage Club` | `NULL` |
| Upgrade points to SKY Coin exchange | `Income:Point Charge` | `ANA` |

## Source-specific Rules

- Positive amounts add coins; negative amounts use coins. Comma-separated amounts are accepted.
