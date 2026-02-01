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

### Run Import Script (Review Mode)

```bash
python3 tmp/*_import_*.py review
```

### Run Import Script (SQL Generation)

```bash
python3 tmp/*_import_*.py sql
```

## Connect to Database

```bash
DB_HOST=$(op read "op://gnucash/gnucash-db/server")
DB_PORT=$(op read "op://gnucash/gnucash-db/port")
DB_NAME=$(op read "op://gnucash/gnucash-db/database")
DB_USER=$(op read "op://gnucash/gnucash-db/username")
PGPASSWORD=$(op read "op://gnucash/gnucash-db/password") psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
```
