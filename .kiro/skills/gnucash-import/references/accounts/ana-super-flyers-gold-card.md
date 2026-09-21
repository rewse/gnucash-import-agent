# ANA Super Flyers Gold Card statement import

Script: [`scripts/ana_super_flyers_gold_card_import.py`](../../../../../scripts/ana_super_flyers_gold_card_import.py)

Use the shared [credit-card workflow and safety rules](../../SKILL.md#credit-cards) for duplicate detection, current-cycle handling, payment registration, review, and SQL execution.

## Accounts

- Card: `Liabilities:Credit Card:ANA Super Flyers Gold Card`
- Payment debit: `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank`
- Payment date: 10th, or the next business day when the 10th is a holiday

## Access

Open `https://www.smbc-card.com/mem/index.jsp` with `agent-browser --auto-connect`. The Vpass password field does not accept automated input, so ask the user to enter the password and complete login.

Select `ＡＮＡ　ＶＩＳＡゴールド` in the card selector, open `ご利用明細`, and select billing months from `お支払い月`. Extract `document.querySelector('body').innerText`. The month selector provides the past 15 months.

## Statement Data

### Confirmed format

The WEB明細書 output is tab-separated. Transaction rows may start with `B#` or `#`:

```text
EXAMPLE USER 様 ご利用分 9999-98**-****-**** （ＡＮＡＶＩＳＡゴールド）
B#	99/03/06	レストラン　新宿店	1,111	１	１	1,111		◎
#	99/03/14	ソフトウェア会社	222	１	１	222		◎
#	99/03/25	ALIEXPRESS (SINGAPORE )	1,851	１	１	1,851	12.00	USD	154.250	03 25	◎
＜お支払金額総合計＞			3,184
```

After removing an optional `B#` or `#`, script input columns are `date, merchant, amount, pay_type, installment, pay_amount, [remarks | local_amount, currency_code, exchange_rate, exchange_date]`. The parser skips lines containing `ご利用分` or `お支払金額総合計`, converts `YY/MM/DD` to `20YY-MM-DD`, and negates the comma-stripped amount. It ignores a domestic `◎` marker. For foreign rows, fields 7 and 8 become `{local_amount} {currency_code}` when the currency is one of `AUD`, `CAD`, `EUR`, `GBP`, `HKD`, `SGD`, `THB`, `TRY`, or `USD`.

### Unconfirmed format

The ご利用明細照会 output is tab-separated:

```text
99/04/09	レストラン　新宿店	EXAMPLE USER	1回払い		99/05	777
```

Script input columns are `date, merchant, card_holder, pay_type, empty, pay_month, amount`. The parser detects this form when column 3 is not numeric and reads the amount from column 7.

## Mapping

| Statement pattern | GnuCash account | Description | Handling |
|---|---|---|---|
| `セブン－イレブン` or normalized `SEVEN-ELEVEN` | `Expenses:Foods:Dining` | `SEVEN-ELEVEN` | Automatic |
| Merchant containing `ファミリーマート` | `Expenses:Foods:Dining` | `Family Mart` | Automatic |
| Merchant containing `ローソン` | `Expenses:Foods:Dining` | `LAWSON` | Automatic |
| `ALIEXPRESS` | Account determined from order details | `AliExpress` | Use `MANUAL_OVERRIDES` after [email lookup](../email-lookup.md) |

Resolve every other row from past GnuCash transactions or ask the user, then add it to `MANUAL_OVERRIDES`.

## Source-specific Rules

- Strip only a leading `B#` or `#` marker before parsing the date and fields.
- Merchant and remarks normalization converts full-width ASCII, digits, spaces, periods, and asterisks to half-width before automatic matching.
- Preserve non-`◎` remarks and foreign amount/currency details for classification.
- Accepted commands are `review` and `sql`.
