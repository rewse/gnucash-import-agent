# Mobile PASMO statement import

Script: `scripts/pasmo_import.py` (`review`, `sql`)

## Accounts

- Source account: `accounts.pasmo.source` from ignored `../personal.json`
- Shopping account: `accounts.pasmo.shopping` from ignored `../personal.json`
- Schema and dummy values: `../personal.example.json`
- Currency: JPY

## Access

- Open `https://www.mobile.pasmo.jp/` with `agent-browser --auto-connect open`; CAPTCHA login is manual.
- Select `次へ`, then `SF（電子マネー） 利用履歴`, and extract with `agent-browser --auto-connect snapshot`.

## Statement Data

Browser columns are `月日`, `種別`, `利用場所`, `種別`, `利用場所`, `残額`, `入金・利用額`:

```text
月日 種別 利用場所 種別 利用場所 残額 入金・利用額
04/28 入 例駅A 出 例駅B 4,820 -180
04/26 物販 5,000 -590
04/21 ｵｰﾄ 例駅A 5,590 +5,000
04/18 入 地 例駅C 出 例駅D 590 -180
03/25 繰 770
```

Station prefixes may be joined or separated by a space, such as `地例駅` and `地 例駅`. Script input removes the header and cumulative-balance column:

```text
04/28 入 例駅A 出 例駅B -180
04/26 物販 -590
04/21 ｵｰﾄ 例駅A +5000
04/18 入 地 例駅C 出 例駅D -180
04/15 定 曙橋 出 都 例駅E -180
04/12 ﾊﾞｽ等 江ノ電Ｂ -390
03/25 繰
```

The parser splits on whitespace. The amount is the final field. For `ｵｰﾄ` and `ﾊﾞｽ等`, the location is every field between the type and amount. `入`, `＊入`, and `定` use `type station1 出 station2 amount`, allowing prefixed station names with a space. The year is inferred: a month later than the current month belongs to the previous year.

## Mapping

| Statement type | GnuCash account | Description |
|---|---|---|
| `入`, `＊入`, `定` | `Expenses:Transit` | Detected railway company |
| `ﾊﾞｽ等` | `Expenses:Transit` | Bus mapping, otherwise `NULL` |
| `物販` | `accounts.pasmo.shopping` from ignored `../personal.json` | `NULL` |
| `ｵｰﾄ` | `Liabilities:Credit Card:TOKYU CARD ClubQ JMB` | `NULL` |
| `繰` or amount 0 | Skip | None |

Railway detection checks these general exceptions before prefixes: `溜池山王`, `赤坂見附`, `後楽園`, `西新宿`, `外苑前`, and `表参道` are Tokyo Metro; `南大沢` is Keio; `江電鎌倉`, `長谷`, `稲村ケ崎`, and `江ノ島` are Enoshima Electric Railway. Exceptions, `nearest_station`, and prefixes are checked on both endpoints. Prefixes map `KS` to Keisei, `地` to Tokyo Metro, `都` to Toei Subway, and `ゆ` to Yurikamome; otherwise use JR. `江ノ電Ｂ` maps to Enoden Bus.

## Source-specific Rules

- `accounts.pasmo.source`, `accounts.pasmo.shopping`, and `nearest_station` are read from ignored `../personal.json`; use `../personal.example.json` as the schema. Account paths are resolved through the account cache and actual configured values are never printed.
- Missing, blank, or malformed `nearest_station` prevents ambiguous railway classification. Public station exceptions and prefixes listed above remain usable without it.
- PASMO never maps transit automatically to `Expenses:Business Expenses`. Override leisure trips to `Expenses:Entertainment:Travel` when needed.
- The cumulative balance is retained only for reading the source page; the script uses the signed amount column.
