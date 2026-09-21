# Rakuten Super Point statement import

Script: `scripts/rakuten_super_point_import.py` (`review`, `sql`)

## Accounts

- Source account: `Assets:JPY - Current Assets:Reward Programs:Rakuten Super Point`
- Cash-charge source: `Assets:JPY - Current Assets:Prepaid:Rakuten Cash`
- Valuation: 1 point = 1 JPY

## Access

- Open the Rakuten sign-in URL with `agent-browser --auto-connect open 'https://login.account.rakuten.com/sso/authorize?client_id=rakuten_ichiba_top_web&service_id=s245&response_type=code&scope=openid&redirect_uri=https://www.rakuten.co.jp/#/sign_in'`; credentials are under `op://gnucash/Rakuten`.
- Open history with `agent-browser --auto-connect open 'https://point.rakuten.co.jp/history/'`, then extract with `agent-browser --auto-connect snapshot`.
- The default view covers seven months. Use `さらに絞り込む` for older dates; rows in the selected range load without monthly pagination.

## Statement Data

Browser columns are `日付`, `サービス`, `内容`, `ポイント利用・獲得`, `備考`:

```text
2030 04/04 | 楽天ポイントカード | ケンタッキーフライドチキン例示店 によるポイント付与 [2030/04/02] ランクアップ対象 | 獲得 | 3
2030 03/22 | 楽天マガジン | 楽天マガジン [2030/03/02] ランクアップ対象 | 獲得 | 5
2030 03/02 | 楽天マガジン | 楽天マガジン でポイント利用 [2030/03/02] | 利用 | 100
2030 02/10 | アフィリエイト | 楽天アフィリエイト成果報酬【楽天キャッシュ】2030年01月度 [2030/02/10] | チャージ キャッシュ | 200
```

Browser points are unsigned; the type determines direction. Keep the bracketed transaction date in `detail`; convert the left-hand history date to the script date. Script input is six tab-separated fields: `{date}\t{service}\t{detail}\t{type}\t{points}\t{desc}`.

```text
2030/04/04	楽天ポイントカード	ケンタッキーフライドチキン例示店 によるポイント付与 [2030/04/02]	獲得	3	KFC
2030/03/02	楽天マガジン	楽天マガジン でポイント利用 [2030/03/02]	利用	100	Rakuten Magazine
2030/02/10	アフィリエイト	楽天アフィリエイト成果報酬【楽天キャッシュ】2030年01月度 [2030/02/10]	チャージ	200	Rakuten Affiliate
```

Input points remain positive. Strip `ランクアップ対象`, `詳細`, and extra whitespace from detail; prepare `desc` in English.

## Mapping

| Type and service | Source / transfer account | Description |
|---|---|---|
| `獲得` | Rakuten Super Point / `Income:Point Charge` | Prepared English description |
| `利用`, Rakuten Magazine | Rakuten Super Point / `Expenses:Entertainment:Books` | `Rakuten Magazine` |
| Other `利用` | Rakuten Super Point / user-selected account | User-selected description |
| `チャージ`, affiliate | Rakuten Cash / `Income:Part-Time` | `Rakuten Affiliate` |

Store mappings include KFC, CoCo Ichibanya, Royal Host, and Steven Alan. For Rakuten Market, use the shop name before `でお買い物` and remove marketplace suffixes; ask when unclear.

## Source-specific Rules

- `獲得` is positive, `利用` is negated by the script, and `チャージ` is positive in the Rakuten Cash source account.
- The database account name is `Rakuten Super Point`.
