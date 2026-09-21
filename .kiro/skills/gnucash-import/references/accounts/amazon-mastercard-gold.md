# Amazon MasterCard Gold statement import

Script: [`scripts/amazon_mastercard_gold_import.py`](../../../../../scripts/amazon_mastercard_gold_import.py)

Use the shared [credit-card workflow and safety rules](../../SKILL.md#credit-cards) for duplicate detection, current-cycle handling, payment registration, review, and SQL execution.

## Accounts

- Card: `Liabilities:Credit Card:Amazon MasterCard Gold`
- Payment debit: `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank`
- Payment date: 26th, or the next business day when the 26th is a holiday

## Access

Open `https://www.smbc-card.com/mem/index.jsp` with `agent-browser --auto-connect`. The Vpass password field does not accept automated input, so ask the user to enter the password and complete login.

Select `Ａｍａｚｏｎ旧ゴールド` with `#vp-view-VC0205-001_RS0051_cardIdentifyKey`, then open `ご利用明細`. Select each billing month from `お支払い月` and extract `document.querySelector('body').innerText`. The selector provides the past 15 months. Both `Amazonマスター` and `ApplePay` sections map to the same card account.

## Statement Data

### Confirmed format

The WEB明細書 output is tab-separated. Section headers and totals surround transaction rows:

```text
EXAMPLE USER 様 ご利用分 9999-99**-****-**** （Ａｍａｚｏｎマスター）
	99/04/02	ＡＭＡＺＯＮ．ＣＯ．ＪＰ	1,237	１	１	1,237
	99/04/11	ＡｍａｚｏｎＰａｙ提携サイト	678	１	１	678	ＡＭＺ＊アマゾン社員食堂
	99/04/19	ALIEXPRESS (SINGAPORE )	2,468	１	１	2,468	16.00	USD	154.250	04 19
＜お支払金額総合計＞			4,383
```

Script input columns are `date, merchant, amount, pay_type, installment, pay_amount, [remarks | local_amount, currency_code, exchange_rate, exchange_date]`. Transaction rows may have a leading tab. The parser skips lines containing `ご利用分` or `お支払金額総合計`, converts `YY/MM/DD` to `20YY-MM-DD`, and negates the comma-stripped amount. For domestic rows, field 7 is retained as remarks. For foreign rows, fields 7 and 8 become `{local_amount} {currency_code}` when the currency is one of `AUD`, `CAD`, `EUR`, `GBP`, `HKD`, `SGD`, `THB`, `TRY`, or `USD`.

### Unconfirmed format

The ご利用明細照会 output is tab-separated with no required leading tab:

```text
99/05/07	ＡＭＡＺＯＮ．ＣＯ．ＪＰ	EXAMPLE USER	1回払い		99/06	912
```

Script input columns are `date, merchant, card_holder, pay_type, empty, pay_month, amount`. The parser detects this form when column 3 is not numeric and reads the amount from column 7.

## Mapping

| Statement pattern | GnuCash account | Description | Handling |
|---|---|---|---|
| `ＡｍａｚｏｎＰａｙ提携サイト` with remarks containing `AMZ*` after normalization and `アマゾン社員食堂` | `Expenses:Foods:Dining` | `AMZ Employee Cafe` | Automatic |
| `セブン－イレブン` or normalized `SEVEN-ELEVEN` | `Expenses:Foods:Dining` | `SEVEN-ELEVEN` | Automatic |
| Merchant containing `ファミリーマート` | `Expenses:Foods:Dining` | `Family Mart` | Automatic |
| Merchant containing `ローソン` | `Expenses:Foods:Dining` | `LAWSON` | Automatic |
| `ＡＭＡＺＯＮ．ＣＯ．ＪＰ` | Account determined from order details | `Amazon` | Use `MANUAL_OVERRIDES` after [email lookup](../email-lookup.md) |
| Other `ＡｍａｚｏｎＰａｙ提携サイト` | Account determined from order details | Description from order details | Use `MANUAL_OVERRIDES` after [email lookup](../email-lookup.md) |
| `ALIEXPRESS` | Account determined from order details | `AliExpress` | Use `MANUAL_OVERRIDES` after [email lookup](../email-lookup.md) |

Resolve every other row from past GnuCash transactions or ask the user, then add it to `MANUAL_OVERRIDES`.

## Source-specific Rules

- Merchant and remarks normalization converts full-width ASCII, digits, spaces, periods, and asterisks to half-width before automatic matching.
- Preserve remarks because Amazon Pay and foreign-currency rows may require them for classification.
- Accepted commands are `review` and `sql`.
