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
