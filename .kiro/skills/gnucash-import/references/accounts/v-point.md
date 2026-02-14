# V Point Statement Import

## GnuCash Account

- Regular: `Assets:JPY - Current Assets:Reward Programs:V Point`
- Store-limited (ANA Mileage Transferable): `Assets:JPY - Current Assets:Reward Programs:V Point - ANA Mileage Transferable Points`

## Credentials

Email authentication is required. You MUST use `agent-browser --headed` and ask the user to log in manually.

## Import Workflow

1. Check if `account-guid-cache.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open https://tsite.jp/tm/pc/login/STKIp0001001.do`
4. Click "設定を始める" (cookie consent)
5. Click "Yahoo! JAPAN IDでログイン"
6. Ask user to complete Yahoo! JAPAN ID login manually (email/SMS auth)
7. After login, click "マイページ"
8. Click "ポイント履歴" to view history
9. Select "利用日順" for date ordering
10. `agent-browser snapshot -c` to get transaction data
11. Click "もっと見る" to load more transactions if needed (repeat snapshot)
12. Prepare RAW_DATA
13. Copy RAW_DATA into `tmp/v_point_import_YYYYMMDD.py`
14. Run `python3 tmp/v_point_import_YYYYMMDD.py review` to show review table
15. User reviews and specifies manual overrides by ID
16. Run `python3 tmp/v_point_import_YYYYMMDD.py sql > tmp/import_v_point.sql` to generate SQL
17. Execute SQL to insert transactions

## Script Template

- `scripts/v_point_import.py`

## Browser Data Format

Paragraphs grouped per transaction: date, description, points, and optional tags.

Example (from snapshot):
```
2026/01/25
三井住友カード カードご利用分 ＡＮＡ ＶＩＳＡゴールド
15 pt
ストア限定

2025/12/19
三井住友カード プリペイドカードチャージ特典 ＡＮＡ ＶＩＳＡゴールド
12 pt

2025/10/31
Ｖポイント
"-50 pt"
失効
期間限定

2026/02/11
三井住友カード ＶポイントＰａｙ残高チャージ（ポイント優先払い）
"-500 pt"
```

Notes:
- Date format: YYYY/MM/DD
- Positive points: `NNN pt`, negative points: `"-NNN pt"` (quoted with minus)
- Optional tags appear after points: `ストア限定`, `期間限定`, `失効`
- A transaction may have multiple tags (e.g., `失効` + `期間限定` or `失効` + `ストア限定`)
- History shows up to 3 years of transactions
- "もっと見る" button loads more transactions (pagination)
- Two sort modes: 利用日順 (by usage date) and 反映日順 (by posting date)

## Conversion Rules

### Account Selection

- Transactions tagged `ストア限定` → `Assets:JPY - Current Assets:Reward Programs:V Point - ANA Mileage Transferable Points`
- All other transactions (including `期間限定`) → `Assets:JPY - Current Assets:Reward Programs:V Point`

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| Positive points (earning) | Income:Point Charge | Translate description to English |
| Negative points with `失効` tag (expiry) | Expenses:Point Lapse | null |
| Negative points, VポイントPay残高チャージ | Assets:JPY - Current Assets:Prepaid:V Point Pay | null |
| Other negative points | (ask user) | Translate description to English |

### Description Translation

Translate Japanese descriptions to English:
- 三井住友カード カードご利用分 ＡＮＡ ＶＩＳＡゴールド → SMBC Card
- 三井住友カード プリペイドカードチャージ特典 ＡＮＡ ＶＩＳＡゴールド → SMBC Card
- 三井住友カード ＶポイントＰａｙ残高チャージ（ポイント優先払い）→ null
- セブンマイル交換 → Seven Eleven
- おかえりＶポイント → V POINT
- 吉野家 → Yoshinoya
- ロッテリア → Lotteria

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

Tab-separated format: `{date}\t{description}\t{points}\t{tags}`

```
2026/02/11	V POINT -515	
2026/01/25	SMBC Card 15	ストア限定
2025/10/31		-50	失効,期間限定
2025/10/13	Yoshinoya 3	
```

Parsing rules:
- Points: integer, positive for earn, negative for use/expiry
- Tags: comma-separated, may be empty
- Description should already be translated to English

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
- Desc: Description (English)
- Account: Source account (V Point or ANA Mileage Transferable)
- Transfer: Target account
- Increase/Decrease: Points

## Notes

- 1 point = 1 JPY
- Point history page shows up to 3 years of transactions
- ストア限定 (store-limited) points can only be used at specific stores and are tracked in the ANA Mileage Transferable Points account
- 期間限定 (time-limited) points have an expiration date but are tracked in the regular V Point account
- Connected services shown on my page: 三井住友カード, 三井住友銀行（Olive）
