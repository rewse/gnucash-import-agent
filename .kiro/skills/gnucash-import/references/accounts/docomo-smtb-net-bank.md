# DOCOMO SMTB Net Bank Statement Import

Script: [`scripts/docomo_smtb_net_bank_import.py`](../../../../../scripts/docomo_smtb_net_bank_import.py)

## Accounts

- JPY: `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank`
- USD: `Assets:USD - Current Assets:Banks:DOCOMO SMTB Net Bank`
- JPY purpose accounts:
  - `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Longterm Account`
  - `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Reserved Account`
  - `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Retirement Account`
- USD purpose accounts:
  - `Assets:USD - Current Assets:Banks:DOCOMO SMTB Net Bank:Entertainment Account`
  - `Assets:USD - Current Assets:Banks:DOCOMO SMTB Net Bank:Longterm Account`

## Access

Open `https://www.netbk.co.jp/contents/pages/wpl010101E/i010101CT/DI01010240` with `agent-browser --auto-connect`, then ask the user to log in manually. Open `入出金明細` from the navigation bar.

For the JPY primary account, select `代表口座` and `円`, choose each required month in the left sidebar, and capture `agent-browser --auto-connect snapshot -c -s "main"`. For USD, change the currency from `円` to `米ドル` and capture each required month the same way. The page shows one month at a time.

## Statement Data

The monthly list appears below a `YYYY年M月` heading with columns `日付`, `取引内容`, `出金金額`, `入金金額`, `残高`, and `メモ`. The first row for a date uses `time` and `text`; later rows on the same date omit `time` and use `term`:

```text
heading "2026年2月" [level=2]
  time: 14日
  text: 振込＊ＥＸＡＭＰＬＥ
    - listitem: 10,000円
    - listitem: 1,200,000円
term: 口座振替 ＤＦ トウキユウカード
    - listitem: 5,000円
    - listitem: 1,195,000円
  time: 10日
  text: 振込＊ＳＡＭＰＬＥ
    - listitem: 20,000円
    - listitem: 1,215,000円
```

```text
heading "2025年12月" [level=2]
  time: 21日
  text: 国税
    - listitem: 0.02USD
    - listitem: 0.14USD
term: 利息
    - listitem: 0.16USD
    - listitem: 0.16USD
  time: 19日
  text: 普通 円 代表口座
    - listitem: 1,789.10USD
    - listitem: 0.00USD
```

Combine the day with the heading year and month. Infer deposit versus withdrawal from balance changes. JPY values use commas and an `円` suffix; USD values use decimals and a `USD` suffix.

Enter script data as tab-separated `CURRENCY\tDATE\tDESCRIPTION\tWITHDRAWAL\tDEPOSIT`. Preserve empty amount fields and remove commas and currency suffixes:

```text
JPY	2026/02/14	振込＊ＥＸＡＭＰＬＥ	10000	0
JPY	2026/02/12	口座振替 ＤＦ トウキユウカード	5000	0
JPY	2026/02/10	振込＊ＳＡＭＰＬＥ		20000
JPY	2026/02/05	普通 円 予備費	150000	0
JPY	2025/12/19	普通 米ドル 代表口座	250000	0
USD	2025/12/19	普通 円 代表口座		1789.10
USD	2025/12/21	国税	0.02	0
USD	2025/12/21	利息		0.16
```

Fields are currency (`JPY` or `USD`), date (`YYYY/MM/DD`), statement description, withdrawal, and deposit. Empty amounts are zero; the signed amount is deposit minus withdrawal. The parser normalizes full-width spaces in descriptions.

## Mapping

Personal transfer classification comes from `transfer_rules.docomo_smtb_net_bank` in `../personal.json`; use [`../personal.example.json`](../personal.example.json) only as its schema. Do not put names, relationships, fixed personal amounts, or personal account paths in this document.

### Public transfers

| Statement pattern | Direction | Account | Description |
|---|---|---|---|
| `振込＊０１８サポートキユウフキン` | Deposit | `Income:National Allowance` | `Tokyo` |
| `振込＊アマゾンウエブサービスジヤパン*` | Deposit | `Assets:JPY - Current Assets:Reimbursement:AWS Japan` | `AWS Japan` |
| `振込＊シガクザイダンチユウガクジヨセイ*` | Deposit | `Income:National Allowance` | `Tokyo` |
| `振込＊ジドウテアテ*` | Deposit | `Income:National Allowance` | `Japan` |

### Direct debits

| Statement pattern | Account | Description |
|---|---|---|
| `口座振替 ＡＰアプラス` | `Liabilities:Credit Card:Luxury Card Mastercard Titanium` | NULL |
| `口座振替 ＤＦ ＧＰマーケテインク` | `Liabilities:Credit Card:GOLD POINT CARD +` | NULL |
| `口座振替 ＤＦ トウキユウカード` | `Liabilities:Credit Card:TOKYU CARD ClubQ JMB` | NULL |
| `口座振替 ＰａｙＰａｙカード` | `Liabilities:Credit Card:PayPay Card JCB` | NULL |
| `口座振替 ミツイスミトモカード*` | Ask whether it settles `Liabilities:Credit Card:Amazon MasterCard Gold` or `Liabilities:Credit Card:ANA Super Flyers Gold Card` | NULL |

### Purpose accounts

| Statement pattern | Account | Description |
|---|---|---|
| `普通 円 予備費` | `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Reserved Account` | NULL |
| `普通 円 老後資金` | `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Retirement Account` | NULL |
| `普通 円 長期貯蓄` | `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Longterm Account` | NULL |

### Tax and interest

| Currency | Statement pattern | Account | Description |
|---|---|---|---|
| JPY | `モバイルレジ（コウキン）*` or `取消 モバイルレジ（コウキン）*` | `Expenses:Tax:Fixed Assets Tax` | `Tokyo` |
| JPY | `ヨツヤゼイムシヨ*` | `Expenses:Tax:Income Tax` | `Japan` |
| JPY or USD | `国税` | `Expenses:Tax:Income Tax` | `Japan` |
| JPY or USD | `利息` | `Income:Interest Income` | NULL |
| JPY | `地方税` | `Expenses:Tax:Income Tax` | `Tokyo` |

## Source-specific Rules

- Match JPY `普通 米ドル 代表口座` and USD `普通 円 代表口座` entries by date. Do not emit the USD statement row separately. The transaction currency is JPY: the JPY split uses its signed amount for `value_num` and `quantity_num` with denominator 1; the USD-account split uses the balancing JPY value with `value_denom = 1` and the matched signed USD cents for `quantity_num` with `quantity_denom = 100`.
- Do not import purpose-account views separately. Their entries in the primary-account view are the authoritative side of the mirror transfer.
- Skip `口座振替 ＤＦ エムアイカード*` and `約定返済 円 住宅*`.
- Treat cancellation rows according to the sign shown by the statement balance change.
- Search the preceding two months for duplicates. Transfers to another imported bank may already exist from that bank's import, so compare date, amount, and description row by row rather than relying on the latest imported date.
- Account selectors include `代表口座`, `予備費`, `長期貯蓄`, `老後資金`, `生活費`, and `娯楽費`; currency selectors include `円`, `米ドル`, `ユーロ`, `英ポンド`, `豪ドル`, `NZドル`, `カナダドル`, `スイスフラン`, `香港ドル`, and `南アランド`. Transaction history extends back several years.
