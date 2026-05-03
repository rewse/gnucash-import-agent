# Email Lookup

Search emails for transaction details when order pages don't show product names.

## Apple Mail Envelope Index

Use Apple Mail's SQLite index for fast searches:

```bash
sqlite3 ~/Library/Mail/V10/MailData/"Envelope Index" "
SELECT m.ROWID, s.subject, datetime(m.date_sent, 'unixepoch', 'localtime') as sent
FROM messages m
JOIN subjects s ON m.subject = s.ROWID
WHERE s.subject LIKE '%KEYWORD%' AND m.date_sent > strftime('%s', '2026-01-01')
ORDER BY m.date_sent DESC
LIMIT 10;
"
```

## Searching by Amount

The `summaries` table contains email body text and can be searched by amount:

```bash
sqlite3 ~/Library/Mail/V10/MailData/"Envelope Index" "
SELECT m.ROWID, s.subject, su.summary
FROM messages m
JOIN subjects s ON m.subject = s.ROWID
JOIN summaries su ON m.summary = su.ROWID
WHERE su.summary LIKE '%¥1,234%'
AND m.date_sent > strftime('%s', '2026-01-01')
ORDER BY m.date_sent;
"
```

Note: Not all emails have summaries indexed (`m.summary` is NULL for some). If a needed email has no summary, fall back to reading the emlx file directly (path: `~/Library/Mail/V10/.../Data/{s[2]}/{s[1]}/{s[0]}/Messages/{ROWID}.emlx` where s = str(ROWID)).

## Amazon Order/Shipped Email Patterns

- **注文済み** emails: contain item names and individual prices, order total
- **発送済み** emails: contain items in this shipment and `合計 {amount} JPY` (the actual charged amount, after discounts)
- Use **発送済み** emails to match the exact charged amount to the credit card statement
- Multiple items from the same order may ship separately with separate charges
