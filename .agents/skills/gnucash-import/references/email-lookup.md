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

## Search the index

Never interpolate a search term into a shell string or SQL text, because subjects and product names can contain quotes, `$(`, and SQL syntax. Write the search term, such as a product name or `¥1,234`, to `$work_dir/mail-term.txt` with a file-writing tool. Then run this read-only query, which binds the term and date as parameters. Pass `subject` to search subjects, or `summary` to search the indexed message text in the `summaries` table:

```bash
python3 -I - "$ENVELOPE_INDEX" "$work_dir/mail-term.txt" "$START_DATE" subject <<'PY'
import sqlite3
import sys
from pathlib import Path

index, term_file, start_date, field = sys.argv[1:]
term = Path(term_file).read_text(encoding="utf-8").strip()
pattern = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
queries = {
    "subject": """
        SELECT m.ROWID, s.subject, datetime(m.date_sent, 'unixepoch', 'localtime')
        FROM messages m
        JOIN subjects s ON m.subject = s.ROWID
        WHERE s.subject LIKE ? ESCAPE '\\'
          AND m.date_sent > strftime('%s', ?)
        ORDER BY m.date_sent DESC
        LIMIT 10
    """,
    "summary": """
        SELECT m.ROWID, s.subject, su.summary
        FROM messages m
        JOIN subjects s ON m.subject = s.ROWID
        JOIN summaries su ON m.summary = su.ROWID
        WHERE su.summary LIKE ? ESCAPE '\\'
          AND m.date_sent > strftime('%s', ?)
        ORDER BY m.date_sent
    """,
}
connection = sqlite3.connect(Path(index).as_uri() + "?mode=ro", uri=True)
try:
    for row in connection.execute(queries[field], (pattern, start_date)):
        print(*row, sep="\t")
finally:
    connection.close()
PY
```

`START_DATE` is a `YYYY-MM-DD` date chosen by the agent, not statement text. Opening the index with `mode=ro` keeps the lookup from writing to Mail's database.

Some messages have a NULL `m.summary`. Locate the matching `.emlx` file under `$HOME/Library/Mail/$MAIL_VERSION` and read it directly when indexed text is unavailable. Apple Mail shards message files by digits from the message row ID, so search by filename instead of assuming a fixed shard path.

## Amazon email patterns

- Use order-confirmation emails to identify item names, individual prices, and the order total.
- Use shipping-confirmation emails to match `合計 {amount} JPY`, the amount charged after discounts.
- Handle separate shipments as separate charges even when they belong to one order.
