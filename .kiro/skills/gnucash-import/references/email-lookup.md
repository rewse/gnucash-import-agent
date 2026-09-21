# Email lookup

Search email only when the source reference requires details that the statement or order page does not provide.

## Locate the Mail index

List the versioned Mail directories and select the active directory, normally the newest one containing `MailData/Envelope Index`:

```bash
ls -dt ~/Library/Mail/V*/
```

Set `MAIL_VERSION` to that directory's basename and choose the earliest relevant date as `START_DATE`:

```bash
MAIL_VERSION="VNN"
START_DATE="YYYY-MM-DD"
ENVELOPE_INDEX="$HOME/Library/Mail/$MAIL_VERSION/MailData/Envelope Index"
```

## Search by subject

```bash
sqlite3 "$ENVELOPE_INDEX" "
SELECT m.ROWID, s.subject, datetime(m.date_sent, 'unixepoch', 'localtime') AS sent
FROM messages m
JOIN subjects s ON m.subject = s.ROWID
WHERE s.subject LIKE '%KEYWORD%'
  AND m.date_sent > strftime('%s', '$START_DATE')
ORDER BY m.date_sent DESC
LIMIT 10;
"
```

## Search by amount

The `summaries` table contains indexed message text:

```bash
sqlite3 "$ENVELOPE_INDEX" "
SELECT m.ROWID, s.subject, su.summary
FROM messages m
JOIN subjects s ON m.subject = s.ROWID
JOIN summaries su ON m.summary = su.ROWID
WHERE su.summary LIKE '%¥1,234%'
  AND m.date_sent > strftime('%s', '$START_DATE')
ORDER BY m.date_sent;
"
```

Some messages have a NULL `m.summary`. Locate the matching `.emlx` file under `$HOME/Library/Mail/$MAIL_VERSION` and read it directly when indexed text is unavailable. Apple Mail shards message files by digits from the message row ID, so search by filename instead of assuming a fixed shard path.

## Amazon email patterns

- Use order-confirmation emails to identify item names, individual prices, and the order total.
- Use shipping-confirmation emails to match `合計 {amount} JPY`, the amount charged after discounts.
- Handle separate shipments as separate charges even when they belong to one order.
