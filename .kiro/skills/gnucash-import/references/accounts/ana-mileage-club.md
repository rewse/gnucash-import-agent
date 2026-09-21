# ANA Mileage Club statement import

Script: `scripts/ana_mileage_club_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:ANA Mileage Club`
- Commodity: ANA reward units, `commodity_scu = 1`
- Accounting valuation: 1 mile = 1 JPY

## Access

- Open `https://www.ana.co.jp/ja/jp/amc/` with `agent-browser --auto-connect open`; credentials are `op://gnucash/ANA/username` and `op://gnucash/ANA/password`.
- Open `マイレージ情報・事後登録` then `マイル口座残高照会`, switch to the new tab, and use `https://cam.ana.co.jp/psz/amcj/jsp/renew/mile/reference.jsp`. Confirm login again if prompted.
- Extract with `agent-browser --auto-connect snapshot -c -s "#meisaitable"`. Click month links under `過去分（月別）` for older data.

## Statement Data

The `#meisaitable` columns are `ご利用日`, `便名`, `内容`, `クラス`, `運賃種別`, `加算マイル`, `ボーナス`, `減算マイル`, `合計`, `プレミアムポイント`, `有効期限`. Preserve empty columns and full-width text.

```text
2030/04/21  TK 0198  EXAMPLE CITY - TOKYO/HANEDA  M       4,023          4,023  4,023  2033/04
2030/04/16           ＡＮＡカードマイルプラス スターバックス ウェブ    40             40         2033/04
2030/04/02           ＡＮＡアップグレ－ド                       -25,000  -25,000
2030/04/07           ＡＮＡ ＰＡＹ                              -1,500   -1,500
```

Use `合計`, which equals `加算マイル + ボーナス` for flights. Script input is four tab-separated fields: `{date}\t{description}\t{amount}\t{account}`. An empty description is represented by adjacent tabs.

```text
2030/04/21	Turkish Airlines	4023	Income:Point Charge
2030/04/16	Starbucks	40	Income:Point Charge
2030/04/07		-1500	Assets:JPY - Current Assets:Prepaid:ANA Pay
```

Dates use `YYYY/MM/DD`; amounts may contain commas and are positive when earned and negative when used.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| `NH ####` flight | `Income:Point Charge` | `ANA` |
| `TK ####` flight | `Income:Point Charge` | `Turkish Airlines` |
| Other Star Alliance flight | `Income:Point Charge` | English airline name |
| `ＡＮＡカードマイルプラス {merchant}` | `Income:Point Charge` | English merchant name |
| `ＳＦＣ...` or other bonus | `Income:Point Charge` | `ANA` |
| `ＡＮＡ ＰＡＹ` | `Assets:JPY - Current Assets:Prepaid:ANA Pay` | `NULL` |
| `ＡＮＡＳＫＹコイン` | `Assets:JPY - Current Assets:Reward Programs:ANA SKY Coin` | `NULL` |
| `ＡＮＡアップグレ－ド` | `Expenses:Entertainment:Travel` | `ANA` |

## Source-specific Rules

- Airline prefixes `NH` and `TK` map to ANA and Turkish Airlines. Look up other airline codes and use the English airline name.
