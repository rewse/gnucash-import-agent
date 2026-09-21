# Bic Point statement import

Script: `scripts/bic_point_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:Bic Point`
- Valuation: 1 point = 1 JPY

## Access

- Open `https://www.biccamera.com/bc/member/SfrLogin.jsp` with `agent-browser --auto-connect --args "--disable-blink-features=AutomationControlled" open`; credentials are `op://gnucash/Bic Camera/username` and `op://gnucash/Bic Camera/password`.
- CAPTCHA completion is manual. Then open the history with `agent-browser --auto-connect open https://www.biccamera.com/bc/member/MemBcPointHistory.jsp`.
- Select `3ヶ月以内`, `6ヶ月以内`, or `1年以内`, then extract with `agent-browser --auto-connect snapshot`.

## Statement Data

Browser columns are `ポイント獲得（利用）日`, `ポイントご利用内容`, `ご注文番号/購入店舗`, `獲得ポイント`, `利用ポイント`, `ご購入の詳細`:

```text
2030年4月18日 店舗でのご購入 ビックカメラ 例示店 100 - 詳しく見る
2030年3月31日 ビックカメラ.comにてご注文 1204567890 50 - 詳しく見る
2030年3月31日 ビックカメラ.comにてご注文 1204567890 - 5,000 詳しく見る
```

Earn and use are separate columns; `-` means no value. The same order may have separate earn and use rows. Script input is five tab-separated fields: `{date}\t{type}\t{description}\t{points}\t{account}`.

```text
2030/04/18	Earn	店舗でのご購入 ビックカメラ 例示店	+100	Income:Point Charge
2030/03/31	Earn	ビックカメラ.comにてご注文 1204567890	+50	Income:Point Charge
2030/03/31	Use	ビックカメラ.comにてご注文 1204567890 電池	-5000	Expenses:Electronics
```

`type` is `Earn` or `Use`; commas and leading `+` are accepted.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| Store or online purchase, earned | `Income:Point Charge` | `Bic Camera` |
| Store purchase, used | User-selected account | `Bic Camera` |
| Online purchase, used | Order-derived account | `Bic Camera` |

## Source-specific Rules

- Open `詳しく見る` for online point usage, get the product name, and select an account from `../account-guid-cache.json`.
- If the order cannot be resolved from the page, use [`../email-lookup.md`](../email-lookup.md).
- The history is limited to one year. The anti-detection browser flag is required.
