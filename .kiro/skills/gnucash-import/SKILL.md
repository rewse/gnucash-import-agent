---
name: gnucash-import
description: Import online statement data into GnuCash PostgreSQL database. Use when inserting transactions from Mobile Suica, credit cards, or bank statements into GnuCash. Also use when adding a new financial source (bank, credit card, prepaid card, etc.) to the import system. Triggers on "add a new account", "set up import for X card", or "create a new source".
---

# GnuCash statement importer

Import online financial statements into a GnuCash PostgreSQL database.

## Workflow

Follow this sequence for every import:

1. Select the matching source reference from [`references/accounts/`](references/accounts/).
2. Create a unique `work_dir`.
3. Refresh the account GUID cache if needed.
4. Retrieve the statement as described by the source reference.
5. Compare statement rows with existing GnuCash transactions.
6. Copy the source script into `$work_dir` and prepare its statement data there.
7. Run the script's `review` command and review every proposed transaction with the user.
8. Run the script's `sql` command and save the generated SQL in `$work_dir`.
9. Inspect the SQL for mappings, signs, GUIDs, balance, descriptions, and reconciliation states.
10. Execute the inspected SQL against GnuCash.

Use `agent-browser --auto-connect` for web automation. Run `agent-browser --help` before its first use in each session. If a page never finishes loading or reports an unusual automation error, retry with `--args "--disable-blink-features=AutomationControlled"`.

When attaching to the user's Chrome, keep one named agent-browser session and one dedicated tab for the entire import run. Process sources sequentially; do not start parallel `--auto-connect` sessions. If manual authentication closes the dedicated tab, create a new tab in the same session instead of creating another session.

Scope snapshots of authenticated pages to the statement container. Do not save or print populated login forms or full account pages that contain names, addresses, member identifiers, balances, or other unrelated personal data. Delete an accidentally captured artifact immediately.

Before asking for approval, make the complete review output visible to the user. For a long review, save it inside the owner-only `work_dir` and open it in a local viewer. Confirm that the user can see the output before accepting approval.

## Safety Rules

- Import each statement row at its original granularity. Do not aggregate, summarize, or combine rows by date or category.
- Ask the user when an account, description, split, or other mapping is ambiguous. Do not guess.
- Require English only for non-NULL transaction descriptions. Preserve NULL descriptions when the source script uses them.
- Set `reconcile_state` to `c` for every split in a transaction verified against a statement, unless the selected source reference explicitly requires `n` for verified counterparty splits.
- Use `reconcile_state = 'n'` only for generic or unverified transactions, or for counterparty splits covered by an explicit source-specific rule.
- Do not delete or modify transactions whose `reconcile_state` is `y` or `c`.
- Add separators between dates in review output.
- Inspect generated SQL before execution. Confirm that every transaction balances and that `value` and `quantity` use the correct signs and denominators.

Use these shared mappings unless a source reference defines a more specific rule:

- Map consumables such as cleaning sheets, contact lens solution, batteries, and toiletries to `Expenses:Supplies`.
- Map non-consumed sundries such as kitchenware, storage cases, cables, and small tools to `Expenses:Groceries`.
- Map only items eligible for the Japanese medical expense deduction to `Expenses:Medical Expenses:Medicines`. Map supplements, contact lens solution, and other daily-care quasi-drugs to `Expenses:Supplies`.

## Workspace

From the repository root, create one OS-managed workspace per run:

```bash
work_dir=$(mktemp -d "/tmp/gnucash-import.XXXXXX")
```

Store downloaded statements, statement data, temporary scripts, intermediate data, and generated SQL only in the exact directory returned by `mktemp`. Do not create import artifacts in the repository or a shared `tmp` directory.

Copy the selected script into the workspace, then run the copy from the repository root so it can resolve the account cache and personal settings:

```bash
cp scripts/{source_slug}_import.py "$work_dir/import.py"
python3 "$work_dir/import.py" review
python3 "$work_dir/import.py" sql > "$work_dir/import.sql"
```

When running from another directory, set the repository root explicitly:

```bash
GNUCASH_IMPORT_ROOT=/path/to/gnucash-import-agent python3 "$work_dir/import.py" review
```

### SQL validation and execution

Run the shared static validator after generating and manually inspecting SQL. Pass the exact source account path from the selected source reference and the expected currency GUID verified against the live database:

```bash
python3 .kiro/skills/gnucash-import/scripts/validate_sql.py \
  --source-account 'Assets:JPY - Current Assets:Prepaid:Example' \
  --currency-guid 'a77d4ee821e04f02bb7429e437c645e4' \
  "$work_dir/import.sql"
```

Do not execute SQL when validation fails. The validator permits only a `BEGIN`/`COMMIT` boundary and generated inserts into `transactions` and `splits`; it also checks GUIDs, the expected currency, cached accounts, one source split per transaction, balance, valid timestamps, positive denominators, nonzero quantities, value/quantity sign agreement, cleared states, printable ASCII-or-NULL descriptions without backslashes, and stable same-day order. Continue to inspect source-specific mappings and exact quantity semantics manually because static SQL structure cannot establish their business meaning.

When a source reference explicitly requires verified counterparty splits to remain `n`, pass `--allow-counterparty-unreconciled`. This opt-in still requires every source-account split to be `c`, permits only `c` or `n` on non-source splits, and leaves the default all-`c` policy unchanged.

Immediately before execution, rerun row-level duplicate detection against the live database. Confirm that every referenced account exists and that the expected currency GUID has the source reference's namespace and mnemonic. Query both `transactions` and `splits` to confirm that every generated GUID has zero matches. A prior check or a matching statement total is not sufficient.

Test the exact inspected SQL against the target database with only its terminal `COMMIT;` changed to `ROLLBACK;`. Create the rollback copy inside `work_dir` and require psql to stop on the first error:

```bash
python3 - "$work_dir/import.sql" "$work_dir/rollback.sql" <<'PY'
from pathlib import Path
import sys

source, destination = map(Path, sys.argv[1:])
sql = source.read_text().rstrip()
if not sql.endswith("COMMIT;"):
    raise SystemExit("generated SQL does not end with COMMIT;")
destination.write_text(sql[:-len("COMMIT;")] + "ROLLBACK;\n")
PY

PGOPTIONS='-c standard_conforming_strings=on' \
  PGPASSWORD="$DB_PASSWORD" psql -X -v ON_ERROR_STOP=1 \
  -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  -f "$work_dir/rollback.sql"
```

Execute the inspected `import.sql` with the same `PGOPTIONS`, `ON_ERROR_STOP=1`, and `standard_conforming_strings=on` only after the rollback trial succeeds. When one approved import run has multiple SQL files, execute their inspected bodies inside one outer `BEGIN`/`COMMIT` transaction so a failure cannot leave a partial multi-source import.

After commit, query by the generated transaction GUIDs and verify the exact expected transaction and split counts, every imported split has its expected `reconcile_state` (`c` by default, with only documented source-specific counterparty exceptions), every transaction balances using rational `value_num / value_denom`, and all expected source and transfer account mappings are present. Keep the SQL and logs in the owner-only `work_dir` until post-checks pass. Then delete them, or move required audit artifacts to an owner-only location. Never write database passwords to an artifact or log.

### Account GUID cache

Use [`references/account-guid-cache.json`](references/account-guid-cache.json) to resolve account paths. Regenerate this ignored file when it is missing or its `updated_at` value is more than one month old:

```bash
set -euo pipefail

cache_path=.kiro/skills/gnucash-import/references/account-guid-cache.json
cache_dir=$(dirname "$cache_path")
cache_tmp=$(mktemp "$cache_dir/.account-guid-cache.json.XXXXXX")
trap 'rm -f "$cache_tmp"' EXIT

DB_HOST=$(op read "op://gnucash/gnucash-db/server")
DB_PORT=$(op read "op://gnucash/gnucash-db/port")
DB_NAME=$(op read "op://gnucash/gnucash-db/database")
DB_USER=$(op read "op://gnucash/gnucash-db/username")
PGPASSWORD=$(op read "op://gnucash/gnucash-db/password") psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -c "
WITH RECURSIVE path_list AS (
   SELECT guid, parent_guid, name, name::text AS path, hidden, placeholder FROM accounts WHERE parent_guid IS NULL
   UNION ALL
   SELECT c.guid, c.parent_guid, c.name, path || ':' || c.name, c.hidden, c.placeholder
   FROM accounts c JOIN path_list p ON p.guid = c.parent_guid
)
SELECT json_build_object(
  'updated_at', NOW(),
  'accounts', (SELECT json_object_agg(path, guid) FROM path_list WHERE path NOT LIKE 'Template Root%' AND hidden = 0 AND placeholder = 0)
);
" | python3 -c "import json,sys; d=json.load(sys.stdin); d['accounts']=dict(sorted(d['accounts'].items())); json.dump(d,sys.stdout,indent=4)" > "$cache_tmp"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); a=d.get('accounts'); assert isinstance(a,dict) and all(isinstance(k,str) and isinstance(v,str) and len(v)==32 and all(c in '0123456789abcdef' for c in v) for k,v in a.items()), 'malformed account GUID cache'" "$cache_tmp"
mv "$cache_tmp" "$cache_path"
trap - EXIT
```

## Duplicate Detection

Before duplicate detection, read the optional `import_not_before` date for the selected source stream from `personal.json`. Use source-stream keys such as `jre_bank`, `mufg_bank`, `sony_bank_jpy`, and `sony_bank_usd`. Treat the configured ISO date as inclusive: discard statement rows before it from duplicate detection, review, mapping, and SQL generation, while processing rows on or after it normally. Use only an explicitly configured date after the user has confirmed the earlier history is complete; never infer a cutoff from the current year, the latest transaction, a matching total, or a prior run. When the source-stream key is absent, apply no hard cutoff.

Query the source account over the statement date range. Treat equal dates and amounts as candidates, then compare descriptions, transaction types, occurrence counts, and other statement details. Import the excess occurrence when the statement contains the same date and amount more times than GnuCash.

When strict date-and-amount matching conflicts with a user-confirmed prior import, expand duplicate detection to a bounded nearby-date window and compare source identifiers, account paths, transaction types, rational values, and quantities. If one statement row was previously split across multiple GnuCash transactions, or multiple source rows were represented by one transaction, compare occurrence counts and aggregate values and quantities only for the matching source and security. A nearby or aggregate match is a duplicate only when all available statement details reconcile exactly. Use aggregation only for duplicate detection; import every genuinely new statement row at its original granularity.

Use the latest reconciled transaction as a retrieval cutoff only when the source reference permits it. Cleared rows may belong to a partially imported statement, so include them when checking duplicates. If no reconciled row exists, inspect the latest transaction without relying on it as proof of completeness.

```sql
SELECT t.post_date::date, t.description, s.value_num, s.value_denom, s.reconcile_state
FROM transactions t
JOIN splits s ON t.guid = s.tx_guid
JOIN accounts a ON s.account_guid = a.guid
WHERE a.name = '{account_name}'
  AND t.post_date::date BETWEEN '{start_date}' AND '{end_date}'
ORDER BY t.post_date, t.guid;
```

## Credit Cards

Import each confirmed statement row and register its payment transaction from the payment account to the credit card account. Also import unconfirmed rows from the current billing cycle, and recheck them during the next import because amounts and status may change.

A payment matching the billing total is a duplicate candidate, not proof that every statement row was imported. Compare the statement line count, occurrence counts, dates, amounts, descriptions, and transaction details before declaring the billing cycle complete. Continue row-level duplicate detection even when the total matches.

Use this query only to find billing-total candidates:

```sql
SELECT t.post_date::date, t.description, s.value_num, s.value_denom
FROM transactions t
JOIN splits s ON t.guid = s.tx_guid
JOIN accounts a ON s.account_guid = a.guid
WHERE a.name = '{account_name}'
  AND s.value_num > 0
  AND to_char(t.post_date, 'YYYY-MM') = '{YYYY-MM}'
  AND s.value_num = {total_amount};
```

## Personal Settings

Create the ignored settings file from the tracked example with owner-only permissions:

```bash
install -m 600 .kiro/skills/gnucash-import/references/personal.example.json \
  .kiro/skills/gnucash-import/references/personal.json
```

Edit `.kiro/skills/gnucash-import/references/personal.json` with local personal settings. Keep its mode at `0600`; verify the mode on macOS without printing the file:

```bash
stat -f '%Lp' .kiro/skills/gnucash-import/references/personal.json
```

Use `import_not_before` for user-confirmed inclusive source-stream cutoffs, `nearest_station` for source-specific transit classification, `accounts.pasmo` for PASMO source and shopping account paths, and `transfer_rules` for source-specific personal transfer mappings. Read only the source key required by the selected script. Validate each configured cutoff as an ISO `YYYY-MM-DD` date and fail with a clear value-free error when it is malformed. Fail with a clear value-free error when a required setting or mapping is absent; do not infer a default account or cutoff. Resolve account paths through `account-guid-cache.json`.

## Adding a Source

1. Collect the source name, GnuCash account paths, currency, login URL, authentication method, statement extraction format, script input format, mapping rules, and source-specific exceptions. Ask incrementally when details are missing.
2. Create `references/accounts/{source-slug}.md` from [`references/templates/reference-template.md`](references/templates/reference-template.md).
3. Ask the user to review the source reference.
4. Create `scripts/{source_slug}_import.py` from [`references/templates/script-template.py`](references/templates/script-template.py).
5. Support both `review` and `sql` commands.
6. Replace amounts and personal details in examples with dummy values. Mask card numbers except an optional six-digit BIN.
7. Keep generic workflow, duplicate checks, review columns, and SQL execution in this file. Keep authentication, extraction, input format, mappings, and exceptions in the source reference.

The source catalog is the set of files in [`references/accounts/`](references/accounts/) paired with scripts in the repository-root [`scripts/`](../../../scripts/). Do not maintain a separate handwritten catalog.

## References

- Read [`references/gnucash-schema.md`](references/gnucash-schema.md) when generating or reviewing SQL.
- Read [`references/fixed-assets.md`](references/fixed-assets.md) when a transaction may acquire, revalue, or dispose of a fixed asset.
- Read [`references/email-lookup.md`](references/email-lookup.md) only when a source reference requires email details.
- Read [`references/personal.example.json`](references/personal.example.json) for the tracked personal-settings schema. Store real values only in ignored `references/personal.json`.
- Treat [`references/accounts/`](references/accounts/) and repository-root [`scripts/`](../../../scripts/) as the authoritative source list.
