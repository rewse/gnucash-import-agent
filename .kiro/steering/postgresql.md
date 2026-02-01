# PostgreSQL Connection

## Retrieve Credentials

```bash
op read "op://gnucash/gnucash-db/server"
op read "op://gnucash/gnucash-db/port"
op read "op://gnucash/gnucash-db/database"
op read "op://gnucash/gnucash-db/username"
op read "op://gnucash/gnucash-db/password"
```

## psql Command

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
