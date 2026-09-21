# Sompo Japan DC Securities Statement Import

Script: [`scripts/sompo_japan_dc_import.py`](../../../../../scripts/sompo_japan_dc_import.py)

## Accounts

- Transfer: `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities`
- `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities:One Japan Stock Index Fund <DC Pension>`
- `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities:Index Fund Global Stock NoHedge (DC)`

A `掛金` buy moves value from the transfer account to the fund on the settlement date.

## Access

Open `https://www.rk.sjdc.co.jp/RKWEB/RkDCMember/Common/JP_D_BFKLogin.aspx` with `agent-browser --auto-connect`. Retrieve the username and password from `op://gnucash/Sompo Japan DC Securities/username` and `op://gnucash/Sompo Japan DC Securities/password`. If prompted, select `今はパスワードを変更しない`.

Open `取引履歴等の確認 > 取引履歴`, select `当月を含む12ヶ月`, and click `実行`. Extract `document.querySelector('body').innerText`; capture each 10-row page with `次へ >>`. No CSV download is available.

## Statement Data

Each transaction is one tab-separated row:

```text
2026/01/28	2026/01/29	Ｏｎｅ国内株式インデックス	598	6.4375	10,000	買 掛金
2026/01/28	2026/01/30	インデックス海外株式ヘッジなし	4,599	11.1212	40,000	買 掛金
```

Columns are trade date, settlement date, fund name, quantity in units (`口`), unit price (`円/口`), settlement amount in JPY, and transaction type. Dates use `YYYY/MM/DD`; numeric fields may contain commas. Paste these rows directly into `RAW_DATA`. The parser retains both dates and posts on the settlement date.

## Mapping

| Browser fund name | Account |
|---|---|
| `インデックス海外株式ヘッジなし` | `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities:Index Fund Global Stock NoHedge (DC)` |
| `ＤＩＡＭ国内株式インデックス` | `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities:One Japan Stock Index Fund <DC Pension>` |
| `Ｏｎｅ国内株式インデックス` | `Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities:One Japan Stock Index Fund <DC Pension>` |

`買 掛金` transactions have a NULL description. Ask for a mapping when the fund name is unknown.

## Source-specific Rules

- Fund split: `value_num = settlement amount`, `value_denom = 1`, `quantity_num = units × 10000`, and `quantity_denom = 10000`.
- Transfer-account split: `value_num = quantity_num = -settlement amount`, with both denominators equal to 1.
- The review and posting date is the settlement date; retain the trade date from the first input column for source comparison.
- For duplicate detection, compare both the trade date and settlement date against nearby GnuCash dates, then require the same fund account, settlement value, and exact unit quantity. Historical imports may have used the trade date, but new imports continue to post on the settlement date.
- History is limited to the current month plus the preceding 11 months.
- Source-specific commands are `review` and `sql`.
