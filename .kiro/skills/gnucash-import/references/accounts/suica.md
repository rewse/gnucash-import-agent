# Mobile Suica statement import

Script: `scripts/suica_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Prepaid:Suica iPhone`
- Currency: JPY

## Access

- Open `https://www.mobilesuica.com/` with `agent-browser --auto-connect open`; CAPTCHA login is manual.
- Open `SF（電子マネー） 利用履歴` and extract with `agent-browser --auto-connect snapshot`.

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

Station prefixes may be joined or separated by a space. Script input removes the header and cumulative-balance column:

```text
04/28 入 例駅A 出 例駅B -180
04/26 物販 -590
04/21 ｵｰﾄ 例駅A +5000
04/19 ﾊﾞｽ等 都電都Ｂ -210
04/18 入 地 例駅C 出 例駅D -180
03/25 繰
```

The parser splits on whitespace, skips `繰`, and reads the final field as the signed amount. `入` and `＊入` use `type station1 出 station2 amount`; prefixed station names may include one space. `ﾊﾞｽ等` uses every field between the type and amount as its location. The year is inferred: a month later than the current month belongs to the previous year.

## Mapping

| Statement type | GnuCash account | Description |
|---|---|---|
| `入`, `＊入` | `Expenses:Transit`, or commute account below | Detected railway company |
| `ﾊﾞｽ等` | `Expenses:Transit` | Bus mapping, otherwise `NULL` |
| `物販` | `Expenses:Foods:Dining` | `NULL` |
| `ｵｰﾄ` | `Liabilities:Credit Card:LUMINE CARD` | `NULL` |
| `繰` | Skip | None |

General railway exceptions are: `神谷町`, `溜池山王`, `赤坂見附`, `六本木一`, `後楽園`, `西新宿`, `外苑前`, and `表参道` to Tokyo Metro; `曙橋` to Toei Subway; `南大沢` to Keio; and `青物横丁` to Keikyu. Exceptions, `nearest_station`, and prefixes are checked on both endpoints. Prefixes map `KS` to Keisei, `臨` to TWR, `地` to Tokyo Metro, and `都` to Toei Subway; otherwise use JR. `都電都Ｂ` bus rows map to `Toei Bus`.

## Source-specific Rules

- `nearest_station` comes from `../personal.json`. It classifies that entry station as `Tokyo Metro` and builds personal commute pairs, while remaining separate from the general railway exception table.
- On weekdays, a direct `{nearest_station} ↔ {commute_station_1}` or `{nearest_station} ↔ {commute_station_2}` transit row maps to `Expenses:Business Expenses`. Only that row is classified as business; weekends, `物販`, and `ｵｰﾄ` are not.
- The cumulative balance is retained only for reading the source page; the script uses the signed amount column.
