# LUMINE CARD statement import

Script: [`scripts/lumine_card_import.py`](../../../../../scripts/lumine_card_import.py)

Use the shared [credit-card workflow and safety rules](../../SKILL.md#credit-cards) for duplicate detection, current-cycle handling, payment registration, review, and SQL execution.

## Accounts

- Card: `Liabilities:Credit Card:LUMINE CARD`
- Payment debit: `Assets:JPY - Current Assets:Banks:JRE Bank`
- Payment date: 4th, or the next business day when the 4th is a holiday

## Access

Open `https://www.viewsnet.jp/default.htm` with `agent-browser --auto-connect --args "--disable-blink-features=AutomationControlled"`. Retrieve credentials from `op://gnucash/VIEWs NET/username` and `op://gnucash/VIEWs NET/password`. After login, hide the popup before interacting with the page:

```javascript
document.getElementById('rtoaster_popup').style.display='none'; document.getElementById('rt.popup-overlay_rtoaster_popup').style.display='none'
```

Open `ご利用明細照会` and select `ルミネカード` when a card selector is shown. Confirmed statements have a `明細CSVダウンロード` button. Convert downloaded Shift-JIS CSV data to UTF-8 before placing it in `RAW_DATA`.

For unconfirmed rows, open `請求予定の明細` and extract:

```javascript
document.querySelector('table[summary*="ご利用年月日"]').innerText
```

## Statement Data

### Confirmed format

The downloaded CSV includes metadata, a column header, and a cardholder line before the transaction rows:

```text
会員番号,****-****-****-0000
対象カード,ルミネカード
お支払日,2099年08月04日
今回お支払金額,"5,508"

ご利用年月日,ご利用箇所,ご利用額,払戻額,ご請求額（うち手数料・利息）,支払区分（回数）,今回回数,今回ご請求額・弁済金（うち手数料・利息）,現地通貨額,通貨略称,換算レート
****-****-****-0000 EXAMPLE USER
2099/06/10,イイトルミネ新宿店　ランディーズドーナツ,"1,249",,"1,187",１回払,,"1,187",,   ,
2099/06/17,東京都交通局　春日駅　オートチャージ（モバイル）,"4,321",,"4,321",１回払,,"4,321",,   ,
```

Script input columns are `date, merchant, usage_amount, refund, billed_amount, pay_type, installment, current_billed, foreign_amount, currency, exchange_rate`. The CSV parser accepts quoted comma-separated amounts, skips rows whose first field is not `YYYY/MM/DD`, and uses `billed_amount` at zero-based index 4.

### Unconfirmed format

The HTML table output contains a year line followed by a tab-separated transaction line. A discounted amount may be in the amount field or on the following line:

```text
2099
07/12	****-****-****-0000	東京都交通局　曙橋駅　オートチャージ（モバイル）	4,321
(4,321)	 		 	ショッピング１回払い
2099
07/27	イイトルミネ新宿店　ババンコク屋台カオサン	1,360
(1,292)	 		 	ショッピング１回払い
```

Literal `\n` and `\t` sequences are normalized first. The parser reads `YYYY` plus `MM/DD`, skips fields matching a masked card number, takes the first nonnumeric field as the merchant, and takes the first later numeric field as the amount. It uses a parenthesized discounted amount from the same field or the next line when present. The card-number field may be absent.

The parser auto-detects confirmed CSV when a line begins with `YYYY/MM/DD,`; all other input uses the unconfirmed parser.

## Mapping

| Statement pattern | GnuCash account | Description | Handling |
|---|---|---|---|
| Merchant containing `オートチャージ` | `Assets:JPY - Current Assets:Prepaid:Suica iPhone` | `Auto-charge (Mobile Suica)` | Automatic |

Resolve every other row from past GnuCash transactions or ask the user, then add it to `MANUAL_OVERRIDES`.

## Source-specific Rules

- LUMINE and NEWoMan purchases may receive a 5% discount. Always post the billed amount, not the original usage amount.
- The confirmed CSV is Shift-JIS and must be converted to UTF-8 before use.
- The `--disable-blink-features=AutomationControlled` browser flag and popup-hiding JavaScript are required for reliable access.
- Accepted commands are `review` and `sql`.
