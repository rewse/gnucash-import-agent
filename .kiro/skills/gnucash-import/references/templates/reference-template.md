# {SOURCE_NAME} statement import

Script: `scripts/{source_slug}_import.py`

## Accounts

- Source account: `{ACCOUNT_PATH}`
- Transfer account: `{TRANSFER_ACCOUNT_PATH}`
- Currency or commodity: `{CURRENCY_OR_COMMODITY}`

## Access

- Login URL: `{LOGIN_URL}`
- Authentication: `{AUTHENTICATION_METHOD}`
- Statement navigation: `{STATEMENT_NAVIGATION}`
- History or paging limit: `{HISTORY_LIMIT}`

Extract statement rows with `agent-browser --auto-connect`:

```text
{BROWSER_EXTRACTION_STEPS}
```

## Statement Data

Browser or download format:

```text
{EXACT_SOURCE_COLUMNS_AND_EXAMPLE}
```

Script input format, including exact column order, delimiters, empty fields, line breaks, and full-width characters:

```text
{EXACT_SCRIPT_INPUT_FORMAT_AND_EXAMPLE}
```

Parsing notes:

- `{PARSING_RULE_1}`
- `{PARSING_RULE_2}`

## Mapping

| Statement pattern | GnuCash account | Description | Split or amount rule |
|---|---|---|---|
| `{PATTERN_1}` | `{ACCOUNT_1}` | `{DESCRIPTION_1}` | `{RULE_1}` |
| `{PATTERN_2}` | `{ACCOUNT_2}` | `{DESCRIPTION_2}` | `{RULE_2}` |

Ask the user to resolve any row that does not match a documented rule.

## Source-specific Rules

- `{AUTHORIZATION_OR_PENDING_RULE}`
- `{DISCOUNT_OR_MULTICURRENCY_RULE}`
- `{MIRROR_SKIP_OR_QUANTITY_RULE}`
- `{SOURCE_EXCEPTION}`
