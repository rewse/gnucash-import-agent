# SBI Shinsei Bank Statement Import

Script: [`scripts/sbi_shinsei_bank_import.py`](../../../../../scripts/sbi_shinsei_bank_import.py)

## Accounts

- JPY savings: `Assets:JPY - Current Assets:Banks:SBI Shinsei Bank`
- SBI Hyper Deposit: `Assets:JPY - Current Assets:Banks:SBI Shinsei Bank:SBI Hyper Deposit`
- USD savings: `Assets:USD - Current Assets:Banks:SBI Shinsei Bank`

## Access

Open `https://bk.web.sbishinseibank.co.jp/SFC/apps/services/www/SFC/desktopbrowser/default/login?mode=1` with `agent-browser --auto-connect`, then ask the user to log in manually. Navigate from the authenticated top page; opening history URLs directly terminates the session with `CME0042`.

- JPY savings: use `入出金明細` under `円普通預金`.
- SBI Hyper Deposit: use `入出金明細` under `SBIハイパー預金`.
- USD savings: open `外貨預金 > 保有明細`, then use the `入出金明細` link in the `米ドル普通預金` row. The global navigation link always opens JPY savings.

Each history page offers `明細をCSVでダウンロードする`. The default view contains 10 rows. To widen it, update its AngularJS scope rather than typing into `#beginDate`, which leaves the model empty:

```javascript
const sc = angular.element(document.getElementById('beginDate')).scope();
sc.$apply(function () {
  sc.refineCd = 'range';
  sc.changeTransactionPeriodRadio();
  sc.beginDate = '2026 / 05 / 01';
  sc.endDate = '2026 / 08 / 17';
  sc.pageSize = 200;
});
sc.search();
```

After the search completes, `sc.data` contains `{postingDate, description, debit, credit, balance}` rows. For example:

```javascript
sc.data.map(r => ['JPY', r.postingDate, r.description, r.debit || '', r.credit || ''].join('\t')).join('\n')
```

## Statement Data

The history table columns are `取引日`, `摘要`, `出金`, `入金`, `残高`, and `メモ`. JPY amounts use commas and ` 円`; USD amounts use decimals and ` USD`. An empty withdrawal or deposit cell is significant.

```text
row "2026/02/11 ATM 現金出金（提携取引） 10,000 円 100,000 円":
  - cell "2026/02/11"
  - cell "ATM 現金出金（提携取引）"
  - cell "10,000 円"
  - cell
  - cell "100,000 円"

row "2026/02/02 SBI証券精算 200 円 5,000,000 円":
  - cell "2026/02/02"
  - cell "SBI証券精算"
  - cell
  - cell "200 円"
  - cell "5,000,000 円"

row "2025/11/04 被仕向事務手数料 15.00 USD 500.00 USD":
  - cell "2025/11/04"
  - cell "被仕向事務手数料"
  - cell "15.00 USD"
  - cell
  - cell "500.00 USD"
```

Enter script data as tab-separated `ACCOUNT_TYPE\tDATE\tDESCRIPTION\tWITHDRAWAL\tDEPOSIT`, using `JPY`, `HYPER`, or `USD`. Remove commas and suffixes but preserve empty fields:

```text
JPY	2026/02/11	ATM 現金出金（提携取引）	10000	0
JPY	2026/02/01	税引前利息		500
HYPER	2026/02/02	SBI証券精算		200
USD	2026/01/01	税引前利息		2.00
USD	2025/11/04	被仕向事務手数料	15.00	0
```

The signed amount is deposit minus withdrawal. `JPY` and `HYPER` use JPY denominator 1; `USD` uses denominator 100.

## Mapping

### JPY savings

| Statement pattern | Account | Description |
|---|---|---|
| `ATM 現金出金（提携取引）` | `Assets:JPY - Current Assets:Cash` | NULL |
| `振込 ｶ) ｱﾌﾟﾗｽ` | `Liabilities:Credit Card:Luxury Card Mastercard Titanium` | NULL |
| `振込手数料` | `Expenses:Fees` | `SBI Shinsei Bank` |
| `満期解約 パワーダイレクト円定期100` | Maturity splits below | NULL |
| `地方税` | `Expenses:Tax:Income Tax` | `Tokyo` |
| `国税` | `Expenses:Tax:Income Tax` | `Japan` |
| `税引前利息` | `Income:Interest Income` | `SBI Shinsei Bank` |
| `ｼﾖｳｶｲｷﾔﾝﾍﾟ-ﾝ` | `Income:Cash Back` | `Referral Campaign` |

A named `振込` or `ＮＥＴ 振込・振替` has no fixed counter-account; ask what it settles. For `ＮＥＴ 資金振替-{account_no}`, use the SBI Shinsei account on the other side of the transfer.

### SBI Hyper Deposit

| Statement pattern | Account | Description |
|---|---|---|
| `SBI証券精算` | `Assets:JPY - Current Assets:Securities:SBI Securities` | NULL |
| `円普通預金` | `Assets:JPY - Current Assets:Banks:SBI Shinsei Bank` | NULL |
| `地方税` | `Expenses:Tax:Income Tax` | `Tokyo` |
| `国税` | `Expenses:Tax:Income Tax` | `Japan` |
| `税引前利息` | `Income:Interest Income` | `SBI Shinsei Bank` |

### USD savings

| Statement pattern | Account | Description |
|---|---|---|
| `円普通預金` | `Assets:JPY - Current Assets:Banks:SBI Shinsei Bank` | NULL |
| `地方税` | `Expenses:Tax:Income Tax` | `Tokyo` |
| `国税` | `Expenses:Tax:Income Tax` | `Japan` |
| `税引前利息` | `Income:Interest Income` | `SBI Shinsei Bank` |
| `被仕向事務手数料` | `Expenses:Fees` | `SBI Shinsei Bank` |
| `外為送金` | `Assets:USD - Current Assets:Securities:Morgan Stanley` | `Morgan Stanley` |

Ask for a mapping when no exact pattern matches.

## Source-specific Rules

- Import both `振込手数料` rows when a fee is charged and then rebated. They offset each other but remain separate statement rows.
- A `満期解約` credit contains principal plus after-withholding interest. Configure `SPLIT_OVERRIDES` so its counter-splits sum exactly to the statement amount: principal goes to `Assets:JPY - Current Assets:Banks:SBI Shinsei Bank:Saving Account` and the remainder to `Income:Interest Income`. Ask for the maturity notice when gross interest and withholding must be split separately.
- SBI Hyper Deposit is the automatic settlement account for SBI Securities; preserve both sides' dates and apply normal mirror-transfer duplicate detection.
- Transaction history runs from the current day back to the same month two years earlier.
