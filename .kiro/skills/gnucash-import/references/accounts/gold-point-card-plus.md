# GOLD POINT CARD + statement import

Script: [`scripts/gold_point_card_plus_import.py`](../../../../../scripts/gold_point_card_plus_import.py)

Use the shared [credit-card workflow and safety rules](../../SKILL.md#credit-cards) for duplicate detection, current-cycle handling, payment registration, review, and SQL execution.

## Accounts

- Card: `Liabilities:Credit Card:GOLD POINT CARD +`
- Payment debit: `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank`
- Payment date: 27th, or the next business day when the 27th is a holiday

## Access

Open `https://secure.goldpoint.co.jp/gpm/authentication/index.html` with `agent-browser --auto-connect --args "--disable-blink-features=AutomationControlled"`. Retrieve credentials from `op://gnucash/Yodobashi Camera/username` and `op://gnucash/Yodobashi Camera/password`; the browser profile may prefill the email address.

Open `ご利用明細の照会`, select an `お支払い月`, and click `照会`. Extract `document.querySelector('body').innerText`. The selector provides the past 15 months and future unconfirmed months.

## Statement Data

### Confirmed format

The Webご利用明細 output is tab-separated, with a leading tab on each transaction row:

```text
EXAMPLE USER 様 ご利用分 9999-97**-****-**** （ゴールドポイントカードプラス）
	99/06/03	ヨドバシドットコム	1,246	１	１	1,246
	99/06/21	ヨドバシカメラ	2,357	１	１	2,357
＜お支払金額総合計＞			3,603
```

After removing the leading tab, script input columns are `date, merchant, amount, pay_type, installment, pay_amount, [foreign_fields]`. The parser identifies the confirmed form by the leading tab, converts `YY/MM/DD`, and negates the comma-stripped amount. Full-width payment and installment numbers are accepted because those fields are not parsed.

### Unconfirmed format

Selecting a future month such as `2099年9月以降` produces rows without a leading tab:

```text
99/07/08	ヨドバシドットコム	EXAMPLE USER	1回払い		99/08	864
```

Script input columns are `date, merchant, card_holder, pay_type, installment_count, pay_month, amount, [foreign_fields]`. The parser identifies the unconfirmed form by the missing leading tab and reads the amount from column 7.

For both forms, lines containing `ご利用分` or `＜お支払金額総合計＞` and blank lines are skipped.

## Mapping

| Statement pattern | GnuCash account | Description | Handling |
|---|---|---|---|
| `ヨドバシドットコム` | Account determined from order details | `Yodobashi.com` | Use `MANUAL_OVERRIDES` after [email lookup](../email-lookup.md) |
| `ヨドバシカメラ` | Ask the user | `Yodobashi Camera` | Use `MANUAL_OVERRIDES` |

The script has no automatic merchant mappings. Resolve every row and add it to `MANUAL_OVERRIDES`; order-confirmation email matching uses date and amount.

## Source-specific Rules

- Keep the leading-tab distinction between confirmed and unconfirmed rows when preparing `RAW_DATA`.
- Online purchases usually require item-level order details to select an expense account.
- Accepted commands are `review` and `sql`.
