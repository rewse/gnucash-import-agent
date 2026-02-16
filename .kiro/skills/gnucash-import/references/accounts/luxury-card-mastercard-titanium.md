# Luxury Card Mastercard Titanium Statement Import

## GnuCash Accounts

- Card: `Liabilities:Credit Card:Luxury Card Mastercard Titanium`
- Points: `Assets:JPY - Current Assets:Reward Programs:Luxury Reward`
- Payment debit: `Assets:JPY - Current Assets:Banks:d NEOBANK`
- Payment date: 27th (or next business day if 27th is a holiday)

## Credentials

- Username: `op://gnucash/Luxury Card/username`
- Password: `op://gnucash/Luxury Card/password`

## Import Workflow

This is a credit card with an associated rewards program (Luxury Reward points). The import handles both card transactions and point earnings.

IMPORTANT: This site has bot protection. You MUST NOT navigate by opening URLs directly. Always use link clicks within the page to navigate. Direct URL access will invalidate the session.

### Card Transaction Import

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. `agent-browser --headed open https://www.aplus.co.jp/myaplus/login.html`
3. Fill ID and password from 1Password, click ログイン
4. From top page, click `サイトマップ` link
5. Click `ご利用明細照会` link
6. For each billing month (starting from the most recent, using the combobox):
   a. Note the `お支払い金額` and status (確定/未確定)
   b. Check if this total already exists in GnuCash (see SKILL.md "Credit Card: Billing Total Check")
   c. If the total exists → stop going further back
   d. If the total does NOT exist → extract transactions via `agent-browser snapshot -c`
7. Perform per-transaction duplicate detection (see SKILL.md "Credit Card: Duplicate Detection")
8. Prepare RAW_DATA with only new transactions (one button text per line)
9. Copy RAW_DATA into `tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py`
10. Run `python3 tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py review`
11. User reviews and specifies manual overrides by ID
12. Run `python3 tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py sql > tmp/import_luxury_card.sql`
13. Execute SQL to insert transactions

### Current Statement (Unconfirmed)

To view unconfirmed transactions, click the "YYYY/MM以降" tab in the date navigation. This tab is an `<a>` inside `.m-navDate__next`. Use:
```
agent-browser eval "document.querySelector('.m-navDate__next a').click()"
```

Unconfirmed transactions have pagination. Check for page numbers at the bottom and click to load more.

See SKILL.md "Credit Card: Current Statement (Unconfirmed)".

### Points Import

1. From top page, click `ポイント` link (or from sitemap, click `ポイント照会・交換`)
2. `agent-browser snapshot -c` to get point history
3. Each month shows: 通常ポイント, 優待ポイント, 特別ポイント, 交換ポイント, 調整ポイント
4. Sum all categories for each month to get net point change
5. Prepare RAW_DATA_POINTS (one line per month: `YYYY-MM\tpoints`)
6. Run `python3 tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py points-review`
7. Run `python3 tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py points-sql`

## Script Template

- `scripts/luxury_card_mastercard_titanium_import.py`

## Browser Data Format

### Confirmed Billing (ご利用明細照会)

Data extracted via `agent-browser snapshot -c` from the billing details page. Each transaction appears as a button element.

Button text format:
```
加盟店名 YY.MM.DD 1回払い 金額円
```

Example:
```
アフラツク（ウエブ） 25.12.01 1回払い 1,000円
トウキヨウガス・１６５９－２４７－１０４５ 25.12.03 1回払い 5,000円
ＡＰＰＬＥ ＣＯＭ ＢＩＬＬ 25.12.13 1回払い 1,500円
ＰＡＹＰＡＬ ＊ＩＨＥＲＢ ＬＬＣ 25.12.15 1回払い 2,000円
ＳＢＩ証券 25.12.16 1回払い 10,000円
```

Header info:
- `MM/DD お支払い金額` + `確定` + `金額円` (confirmed)

Details (when button expanded):
- カード番号: ≪****-****-****-****≫
- ご利用金額: 金額円
- 売上種別: ショッピング
- 摘要: (usually empty, sometimes has foreign currency info)
- Foreign: `現地通貨額XXX／換算レートYYY円`

### Unconfirmed Billing (利用明細 - 未請求)

Button text format:
```
加盟店名 YY.MM.DD 1回払い お支払い方法変更可能 金額円
```

Example:
```
カブシキガイシヤループ 26.02.12 1回払い お支払い方法変更可能 200円
フルナビマネー 26.02.11 1回払い お支払い方法変更可能 10,000円
ケンタツキ－フライドチキン 26.02.02 1回払い お支払い方法変更可能 500円
```

Header info:
- `未請求のご利用金額` + `未確定` + `金額円`

Details (when button expanded):
- カード番号下4桁: ****
- 売上種別: ショッピング
- 初回年月: YY/MM

### Points (ポイント照会・交換)

Monthly summary from snapshot. Each month row contains:
- 通常ポイント(1): earned from card usage
- 優待ポイント(2): campaign bonuses
- 特別ポイント(3): special promotions
- 交換ポイント(4): redeemed (negative)
- 調整ポイント(5): adjustments

Example:
```
2026-02	408
2026-01	636
2025-12	328
```

Notes:
- Full-width characters for merchant names (e.g., `ＡＰＰＬＥ ＣＯＭ ＢＩＬＬ`)
- Full-width numbers in some merchant names (e.g., `１６５９－２４７－１０４５`)
- Katakana merchant names (e.g., `アフラツク`, `トウキヨウガス`)
- `／ＮＦＣ` suffix indicates NFC (contactless) payment
- `ＳＱ＊` prefix indicates Square payment
- `ＰＡＹＰＡＬ ＊` prefix indicates PayPal payment

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| カブシキガイシヤループ | Expenses:Bike | LUUP |
| ＳＱ＊マラドウ | Expenses:Foods:Dining | Mala Do |
| ロイヤルホスト | Expenses:Foods:Dining | Royal Host |
| マクドナルドモバイルオ－ダ－ | Expenses:Foods:Dining | McDonald's |
| サブウエイ | Expenses:Foods:Dining | Subway |
| ヨ－クフ－ズ シヨクヒン | Expenses:Foods:Foodstuffs | York Foods |
| シヤトレーゼ | Expenses:Foods:Foodstuffs | Chateraise |
| パルシステムセイカツキヨウドウクミア | Expenses:Insurances:Health Insurances | Palsystem |
| ココカラフアイン | Expenses:Supplies | Cocokara Fine |
| カジ－ | Expenses:House:Maintenance | CaSy |
| ユニクロ | Expenses:Clothes | UNIQLO |
| パ－ソナルジムアスピ | Expenses:Entertainment:Sports | ASPI |
| ラクテンマガジン | Expenses:Entertainment:Books | Rakuten Magazine |
| ノート | Expenses:Entertainment:Books | note |
| ＵＱｍｏｂｉｌｅご利用料金 | Expenses:Utilities:Phone:Mobile | UQ Mobile |
| ニホンツウシンカブシキガイシヤ | Expenses:Utilities:Phone:Mobile | Nihon Tsushin |
| フルナビマネー | Expenses:Tax:Furusato Tax | Furunavi |
| ミカタシヨウガクタンキホケン | Expenses:Insurances | MIKATA Small Amount Short Term Insurance |
| ＡＰＰＬＥ ＣＯＭ ＢＩＬＬ | (email lookup) | Apple |
| ビツクカメラドツトコム | (email lookup) | Bic Camera |
| ムジルシリヨウヒン | (ask user) | MUJI |
| エフエヌジエイ デンキリヨウキン | Expenses:Utilities | FNJ |
| スミビヤキニク チヨウシユンカン | Expenses:Foods:Dining | Choshunkan |
| カブシキガイシヤタカギ | Expenses:Supplies | Takagi |
| ネツトオウル | Expenses:Computers:Software | XServer |
| ブラステルコクサイデンワ | Expenses:Utilities:Phone:Mobile | Brastel |
| モスノネツトチユウモン | Expenses:Foods:Dining | Mos Burger |

### KDDI Split Transaction

ＫＤＤＩ料金 is a fixed split into 3 accounts:

- `Expenses:Utilities:Internet` — ¥4,454
- `Expenses:Utilities:Phone:Landline` — ¥1,214
- `Expenses:Entertainment:Movies` — ¥2,290

### Unmapped Merchants

For any transaction not matching the above patterns, check past GnuCash transactions for the same merchant. If no match found, ask the user.

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

### Points Conversion

Points are recorded as income:
- Earned points (positive): debit Luxury Reward, credit Income
- Redeemed points (negative): handled when the redemption target is known

## Script Input Format

### Card Transactions

One transaction per line, extracted from button text in snapshot:

Confirmed format:
```
加盟店名 YY.MM.DD 1回払い 金額円
```

Unconfirmed format:
```
加盟店名 YY.MM.DD 1回払い お支払い方法変更可能 金額円
```

Parsing rules:
- Match pattern: `(.+)\s+(\d{2}\.\d{2}\.\d{2})\s+\d+回払い\s+(?:お支払い方法変更可能\s+)?([\d,]+)円`
- Merchant: group 1 (full-width katakana/ASCII)
- Date: group 2 → `20YY-MM-DD`
- Amount: group 3 → remove commas, parse as integer, negate (credit card spending)

### Points

Tab-separated: `YYYY-MM\tpoints`

Parsing rules:
- Split by tab
- Date: 15th of month
- Points: integer (positive = earned, negative = redeemed/adjusted)

## Review Table Structure

### Card Transactions

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Merchant: Merchant name (normalized to ASCII where possible)
- Desc: Description for GnuCash
- Transfer: Target account
- Amount: Amount (JPY, shown as positive for readability)

### Points

- ID: Sequential number
- Date: YYYY-MM
- Points: Net points for the month
- Transfer: Income account

## Notes

- All descriptions MUST be in English
- Bot protection: NEVER navigate by direct URL; always click links within the page
- The site uses Angular; wait for page loads after navigation
- Card name on site: ＬＣチタンカード-****
- Points program name: ラグジュアリー・リワード
- Points are awarded on the 15th of each month (e.g., 2026年3月15日進呈予定)
