# Luxury Card Mastercard Titanium statement import

Script: [`scripts/luxury_card_mastercard_titanium_import.py`](../../../../../scripts/luxury_card_mastercard_titanium_import.py)

Use the shared [credit-card workflow and safety rules](../../SKILL.md#credit-cards) for duplicate detection, current-cycle handling, payment registration, review, and SQL execution.

## Accounts

- Card: `Liabilities:Credit Card:Luxury Card Mastercard Titanium`
- Payment debit: `Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank`
- Payment date: 27th, or the next business day when the 27th is a holiday
- Points: `Assets:JPY - Current Assets:Reward Programs:Luxury Reward`
- Points income: `Income:Point Charge`

## Access

Open `https://www.aplus.co.jp/myaplus/login.html` with `agent-browser --auto-connect`. Retrieve credentials from `op://gnucash/Luxury Card/username` and `op://gnucash/Luxury Card/password`.

The site invalidates sessions after direct URL navigation. After login, navigate only by clicking links: open `サイトマップ`, then `ご利用明細照会`. Select billing months with the page controls and extract each page with `agent-browser --auto-connect snapshot -c`. Check the page numbers below the transaction list and capture every page for both confirmed and unconfirmed months.

Open the unconfirmed view by clicking the `YYYY/MM以降` link inside `.m-navDate__next`:

```javascript
document.querySelector('.m-navDate__next a').click()
```

For points, click `ポイント` from the top page or `ポイント照会・交換` from the sitemap, then capture the monthly history with `snapshot -c`.

## Statement Data

### Confirmed card format

Each transaction button contributes one line:

```text
アフラツク（ウエブ） 99.08.01 1回払い 1,239円
トウキヨウガス・００００－０００－００００ 99.08.03 1回払い 5,678円
ＡＰＰＬＥ ＣＯＭ ＢＩＬＬ 99.08.13 1回払い 2,345円
```

The header contains `MM/DD お支払い金額`, `確定`, and the amount. Expanded details may contain a masked card number, `売上種別`, and foreign details such as `現地通貨額XXX／換算レートYYY円`.

### Unconfirmed card format

Unconfirmed buttons include an extra status phrase:

```text
カブシキガイシヤループ 99.09.12 1回払い お支払い方法変更可能 321円
フルナビマネー 99.09.11 1回払い お支払い方法変更可能 12,345円
```

The header contains `未請求のご利用金額`, `未確定`, and the amount. Expanded details may contain the card's last four digits, `売上種別`, and `初回年月`.

For both forms, paste one button text per `RAW_DATA` line. The parser accepts `merchant YY.MM.DD N回払い [お支払い方法変更可能] amount円`, converts the date to `20YY-MM-DD`, removes amount commas, and negates the amount. Full-width merchant text is normalized for selected matching and review output; `／ＮＦＣ`, `ＳＱ＊`, and `ＰＡＹＰＡＬ ＊` remain meaningful merchant qualifiers.

### Points format

Sum `通常ポイント`, `優待ポイント`, `特別ポイント`, `交換ポイント`, and `調整ポイント` for each month. Paste one tab-separated monthly net change per `RAW_DATA_POINTS` line:

```text
2099-09	417
2099-08	638
2099-07	-291
```

The parser posts each monthly value on the 15th. Positive values debit Luxury Reward and credit `Income:Point Charge`; negative values use the reverse signs. Use `points-sql` for a negative entry only after confirming that it is a reversal or adjustment whose counter-account is `Income:Point Charge`. An actual points exchange must not be processed with unchanged `points-sql`; generate and review manual SQL that uses the confirmed exchange destination account as the counter-account.

## Mapping

| Statement pattern | GnuCash account | Description | Handling |
|---|---|---|---|
| `カブシキガイシヤループ` | `Expenses:Bike` | `LUUP` | Automatic |
| `ＳＱ＊` after normalization and merchant containing `マラドウ` | `Expenses:Foods:Dining` | `Mala Do` | Automatic |
| `ロイヤルホスト` | `Expenses:Foods:Dining` | `Royal Host` | Automatic |
| `マクドナルド` | `Expenses:Foods:Dining` | `McDonald's` | Automatic |
| `サブウエイ` | `Expenses:Foods:Dining` | `Subway` | Automatic |
| `ヨ－クフ－ズ` | `Expenses:Foods:Foodstuffs` | `York Foods` | Automatic |
| `シヤトレーゼ` | `Expenses:Foods:Foodstuffs` | `Chateraise` | Automatic |
| `パルシステム` | `Expenses:Insurances:Health Insurances` | `Palsystem` | Automatic |
| `ココカラフアイン` | `Expenses:Supplies` | `Cocokara Fine` | Automatic |
| `カジ－` | `Expenses:House:Maintenance` | `CaSy` | Automatic |
| `ユニクロ` | `Expenses:Clothes` | `UNIQLO` | Automatic |
| `パ－ソナルジムアスピ` | `Expenses:Entertainment:Sports` | `ASPI` | Automatic |
| `ラクテンマガジン` | `Expenses:Entertainment:Books` | `Rakuten Magazine` | Automatic |
| Exact merchant `ノート` | `Expenses:Entertainment:Books` | `note` | Automatic |
| `ＵＱｍｏｂｉｌｅ` | `Expenses:Utilities:Phone:Mobile` | `UQ Mobile` | Automatic |
| `ニホンツウシンカブシキガイシヤ` | `Expenses:Utilities:Phone:Mobile` | `Nihon Tsushin` | Automatic |
| `フルナビマネー` | `Expenses:Tax:Furusato Tax` | `Furunavi` | Automatic |
| `ミカタシヨウガクタンキホケン` | `Expenses:Insurances` | `MIKATA Small Amount Short Term Insurance` | Automatic |
| `ＫＤＤＩ` | Fixed split below | `KDDI` | Automatic; `MANUAL_OVERRIDES[id] = 'KDDI'` is also accepted |
| `ＡＰＰＬＥ ＣＯＭ ＢＩＬＬ` | Account determined from receipt | `Apple` | Use `MANUAL_OVERRIDES` after [email lookup](../email-lookup.md) |
| `ビツクカメラドツトコム` | Account determined from order details | `Bic Camera` | Use `MANUAL_OVERRIDES` after [email lookup](../email-lookup.md) |
| `ムジルシリヨウヒン` | Ask the user | `MUJI` | Use `MANUAL_OVERRIDES` |
| `エフエヌジエイ デンキリヨウキン` | `Expenses:Utilities` | `FNJ` | Use `MANUAL_OVERRIDES` |
| `スミビヤキニク チヨウシユンカン` | `Expenses:Foods:Dining` | `Choshunkan` | Use `MANUAL_OVERRIDES` |
| `カブシキガイシヤタカギ` | `Expenses:Supplies` | `Takagi` | Use `MANUAL_OVERRIDES` |
| `ネツトオウル` | `Expenses:Computers:Software` | `XServer` | Use `MANUAL_OVERRIDES` |
| `ブラステルコクサイデンワ` | `Expenses:Utilities:Phone:Mobile` | `Brastel` | Use `MANUAL_OVERRIDES` |
| `モスノネツトチユウモン` | `Expenses:Foods:Dining` | `Mos Burger` | Use `MANUAL_OVERRIDES` |

Resolve other rows from past GnuCash transactions or ask the user.

## Source-specific Rules

- A KDDI transaction is split into `Expenses:Utilities:Internet` ¥4,454, `Expenses:Utilities:Phone:Landline` ¥1,214, and `Expenses:Entertainment:Movies` ¥2,290. Verify that the statement total is ¥7,958 before generating SQL because the script uses these fixed amounts.
- Card pagination applies to confirmed and unconfirmed views; missing a page omits transactions.
- The card label is `ＬＣチタンカード-****`; the points program is `ラグジュアリー・リワード`.
- Points are normally awarded on the 15th of each month.
- Accepted commands are `review`, `sql`, `points-review`, and `points-sql`.
