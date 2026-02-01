# Tech Stack

## Language

- Python 3

## Database

- PostgreSQL (GnuCash backend)
- Credentials managed via 1Password CLI (`op`)

## Dependencies

- Python standard library only (no external packages)
- 1Password CLI for credential management
- `agent-browser` for web automation

## Common Commands

### Run Suica Import (Review Mode)

```bash
python3 scripts/suica_import.py review
```

### Run Suica Import (SQL Generation)

```bash
python3 scripts/suica_import.py sql
```

### Connect to Database

```bash
op run --env-file=<(cat <<EOF
DB_HOST=op://gnucash/gnucash-db/server
DB_PORT=op://gnucash/gnucash-db/port
DB_NAME=op://gnucash/gnucash-db/database
DB_USER=op://gnucash/gnucash-db/username
PGPASSWORD=op://gnucash/gnucash-db/password
EOF
) -- psql -h "\$DB_HOST" -p "\$DB_PORT" -U "\$DB_USER" -d "\$DB_NAME"
```
