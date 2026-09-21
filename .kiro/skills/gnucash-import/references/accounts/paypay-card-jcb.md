# PayPay Card JCB statement import

Script: [`scripts/paypay_card_jcb_import.py`](../../../../../scripts/paypay_card_jcb_import.py)

Use the shared [credit-card workflow and safety rules](../../SKILL.md#credit-cards) for duplicate detection, current-cycle handling, payment registration, review, and SQL execution.

## Accounts

- Card: `Liabilities:Credit Card:PayPay Card JCB`
- Payment debit: `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank`
- Payment date: 27th

## Access

Open `https://www.paypay-card.co.jp/member-login?promptParam=3` with `agent-browser --auto-connect`. Login uses a Yahoo! JAPAN ID passkey, so ask the user to complete authentication. Dismiss the post-login tutorial by clicking each `次へ` control and its final `閉じる` or `完了` control. Additional popups may appear when the statement page first opens.

Open `請求明細`, then the monthly statement at `https://www.paypay-card.co.jp/member/statement/monthly?dispmode=latest`. Transactions appear as menuitem elements in `agent-browser --auto-connect snapshot` output. Use `前月` and `翌月` to change months. Confirmed statements may also offer `明細出力` and `CSVダウンロード`.

## Statement Data

Confirmed (`仮確定`) and unconfirmed (`未確定`) pages expose the same menuitem text:

```text
menuitem "チャージ 2099年1月20日 1,111円"
menuitem "RESTAURANT ABC 2099年1月18日 2,222円"
menuitem "キッチンオリジン、オリジン 2099年1月6日 3,333円"
menuitem "請求書払い 2099年1月4日 44,444円"
menuitem "ヤフージャパン 2098年12月31日 555円"
```

Convert the menuitems to one tab-separated input row per transaction:

```text
チャージ	2099年1月20日	1,111
RESTAURANT ABC	2099年1月18日	2,222
キッチンオリジン、オリジン	2099年1月6日	3,333
請求書払い	2099年1月4日	44,444
ヤフージャパン	2098年12月31日	555
```

Script input columns are `merchant, date, amount`. The parser also accepts a fallback line in the form `merchant YYYY年M月D日 amount円`. It parses Japanese dates, removes amount commas, negates the amount, and preserves merchant spaces and punctuation.

## Mapping

| Statement pattern | GnuCash account | Description | Handling |
|---|---|---|---|
| Exact merchant `チャージ` | `Assets:JPY - Current Assets:Prepaid:PayPay` | NULL | Automatic |
| Merchant containing `オリジン`, `キッチンオリジン`, `マーラータン`, `セブン`, `ファミリーマート`, `ローソン`, `マクドナルド`, `すき家`, `吉野家`, `松屋`, `ガスト`, `サイゼリヤ`, or `RESTAURANT` | `Expenses:Foods:Dining` | Original merchant text | Automatic |
| Merchant containing `ヤフージャパン` or `Yahoo` | Ask the user for split accounts and amounts | First split description | Use a list of `(account_guid, amount, description)` tuples in `MANUAL_OVERRIDES` |
| Merchant containing `請求書払い` | Ask the user for account and description | Ask the user | Use `MANUAL_OVERRIDES` |

Resolve every other row from past GnuCash transactions or ask the user, then add it to `MANUAL_OVERRIDES`.

## Source-specific Rules

- Yahoo! transactions commonly need multiple expense splits. The script accepts either one `(account_guid, description)` tuple or a list of `(account_guid, amount, description)` tuples for any override.
- For a split override, the listed positive amounts must sum to the absolute card charge. The transaction description comes from the first split description.
- Treat `仮確定` and `未確定` as unconfirmed source status under the shared current-cycle rules.
- Accepted commands are `review` and `sql`.
