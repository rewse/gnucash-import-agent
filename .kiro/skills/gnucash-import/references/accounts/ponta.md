# Ponta statement import

Script: `scripts/ponta_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:Ponta`
- Valuation: 1 point = 1 JPY

## Access

- Open `https://point.recruit.co.jp/point/` with `agent-browser --auto-connect open`; credentials are `op://gnucash/Recruit/username` and `op://gnucash/Recruit/password`.
- Authenticator-app 2FA is manual. Close popups, then open `ポイント通帳` and `ポイント履歴を見る`.
- Select a recent-month tab or a month from the dropdown, up to 13 months back, then extract with `agent-browser --auto-connect snapshot`.

## Statement Data

Browser columns are `日付`, `場所`, `ご利用内容`, `ポイント`:

```text
2030年4月25日 ＫＤＤＩ加盟店 エンタメサービスご利用分（Ｎｅｔｆｌｉｘ） お買上げ 100
2030年4月22日 三菱ＵＦＪ銀行 三菱ＵＦＪダイレクトログイン サービスご利用 5
2030年4月14日 ＫＤＤＩ定期付与 マンスリー お買上げ 10
```

Script input is four tab-separated fields: `{date}\t{place}\t{type}\t{points}`.

```text
2030/04/25	KDDI	お買上げ	+100
2030/04/22	MUFG Bank	サービスご利用	+5
2030/04/14	KDDI	お買上げ	+10
```

Dates use `YYYY/MM/DD`; points retain their sign and may contain commas. Translate `場所` to English before input.

## Mapping

| Statement pattern | GnuCash account | Description |
|---|---|---|
| Positive points | `Income:Point Charge` | English `場所` |
| Negative points | User-selected account | English `場所` |

Known translations are KDDI entertainment-service and monthly-grant rows to `KDDI`, and Mitsubishi UFJ Direct login rows to `MUFG Bank`.

## Source-specific Rules

- Positive rows have been observed; preserve a negative sign if a usage row appears.
- Recruit ID is shared with other Recruit services, and the 2FA code must be entered manually.
