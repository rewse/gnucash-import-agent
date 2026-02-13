# {SOURCE_NAME} Statement Import

## GnuCash Account

`{ACCOUNT_PATH}`

## Credentials

{CREDENTIAL_INSTRUCTIONS}

## Import Workflow

1. Check if `accounts.json` exists and `updated_at` is within 1 month; regenerate if needed (see SKILL.md)
2. Check DB for last imported transaction date to determine how far back to fetch
3. `agent-browser --headed open {LOGIN_URL}`
4. {LOGIN_STEPS}
5. {NAVIGATE_TO_STATEMENT}
6. `agent-browser snapshot` to get transaction data
7. Prepare RAW_DATA
8. Copy RAW_DATA into `tmp/{source_slug}_import_YYYYMMDD.py`
9. Run `python3 tmp/{source_slug}_import_YYYYMMDD.py review` to show review table
10. User reviews and specifies manual overrides by ID
11. Run `python3 tmp/{source_slug}_import_YYYYMMDD.py sql > tmp/import_{source_slug}.sql` to generate SQL
12. Execute SQL to insert transactions

## Script Template

- `scripts/{source_slug}_import.py`

## Browser Data Format

{FORMAT_DESCRIPTION}

Example (from snapshot):
```
{EXAMPLE_DATA}
```

Notes:
{BROWSER_NOTES}

## Conversion Rules

### Transaction Types

| Pattern | GnuCash Account | Description |
|---------|-----------------|-------------|
| {PATTERN_1} | {ACCOUNT_1} | {DESC_1} |
| {PATTERN_2} | {ACCOUNT_2} | {DESC_2} |

### Email Lookup for Missing Information

If you don't know the account or the merchant, search emails with the amount. See [email-lookup.md](email-lookup.md).

## Script Input Format

{INPUT_FORMAT_DESCRIPTION}

```
{INPUT_EXAMPLE}
```

Parsing rules:
{PARSING_RULES}

## Review Table Structure

Display transactions sorted by date descending (newest first) with:
- ID: Sequential number for user to reference
- Date: YYYY-MM-DD with weekday (Mon, Tue, etc.)
{REVIEW_COLUMNS}

## Notes

{ADDITIONAL_NOTES}
