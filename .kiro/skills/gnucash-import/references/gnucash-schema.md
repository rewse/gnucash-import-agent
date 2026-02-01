# GnuCash PostgreSQL Schema Reference

## Core Transaction Tables

### transactions

```sql
CREATE TABLE transactions (
    guid            CHAR(32) PRIMARY KEY NOT NULL,
    currency_guid   CHAR(32) NOT NULL,
    num             text(2048) NOT NULL,
    post_date       timestamp NOT NULL,
    enter_date      timestamp NOT NULL,
    description     text(2048)
);
```

### splits

```sql
CREATE TABLE splits (
    guid            CHAR(32) PRIMARY KEY NOT NULL,
    tx_guid         CHAR(32) NOT NULL,
    account_guid    CHAR(32) NOT NULL,
    memo            text(2048) NOT NULL,
    action          text(2048) NOT NULL,
    reconcile_state text(1) NOT NULL,
    reconcile_date  timestamp NOT NULL,
    value_num       integer NOT NULL,
    value_denom     integer NOT NULL,
    quantity_num    integer NOT NULL,
    quantity_denom  integer NOT NULL,
    lot_guid        CHAR(32)
);
```

### accounts

```sql
CREATE TABLE accounts (
    guid            CHAR(32) PRIMARY KEY NOT NULL,
    name            text(2048) NOT NULL,
    account_type    text(2048) NOT NULL,
    commodity_guid  CHAR(32) NOT NULL,
    commodity_scu   integer NOT NULL,
    non_std_scu     integer NOT NULL,
    parent_guid     CHAR(32),
    code            text(2048),
    description     text(2048),
    hidden          integer NOT NULL,
    placeholder     integer NOT NULL
);
```

### commodities

```sql
CREATE TABLE commodities (
    guid            CHAR(32) PRIMARY KEY NOT NULL,
    namespace       text(2048) NOT NULL,
    mnemonic        text(2048) NOT NULL,
    fullname        text(2048),
    cusip           text(2048),
    fraction        integer NOT NULL,
    quote_flag      integer NOT NULL,
    quote_source    text(2048),
    quote_tz        text(2048)
);
```

### prices

```sql
CREATE TABLE prices (
    guid            CHAR(32) PRIMARY KEY NOT NULL,
    commodity_guid  CHAR(32) NOT NULL,
    currency_guid   CHAR(32) NOT NULL,
    date            timestamp NOT NULL,
    source          text(2048),
    type            text(2048),
    value_num       integer NOT NULL,
    value_denom     integer NOT NULL
);
```

## GUID Generation

32-character hex string without hyphens:
```python
import uuid
guid = uuid.uuid4().hex
```

## Numeric Values

Amounts stored as `value_num / value_denom`:
- JPY: `denom = 1` (¥1,234 → num=1234, denom=1)
- USD: `denom = 100` ($12.34 → num=1234, denom=100)

## Transaction Structure

One transaction + two or more splits (must balance):

```sql
INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)
VALUES ('tx_guid', 'a77d4ee821e04f02bb7429e437c645e4', '', '2026-02-01 00:01:23', NOW(), 'Train fare');

INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom)
VALUES 
  ('split1_guid', 'tx_guid', 'suica_guid', '', '', 'n', NULL, -500, 1, -500, 1),
  ('split2_guid', 'tx_guid', 'transport_guid', '', '', 'n', NULL, 500, 1, 500, 1);
```

Important:
- `currency_guid` MUST be the correct currency GUID from commodities table (see Currency GUIDs below)
- `post_date` MUST include time. Use row index as time for sorting (oldest=00:00:01, newest=00:00:N)
- `reconcile_date` SHOULD be NULL for unreconciled splits

## Common Queries

### Find account GUID by path

```sql
WITH RECURSIVE path_list AS (
   SELECT guid, parent_guid, name, name::text AS path FROM accounts WHERE parent_guid IS NULL
   UNION ALL
   SELECT c.guid, c.parent_guid, c.name, path || ':' || c.name
   FROM accounts c JOIN path_list p ON p.guid = c.parent_guid
)
SELECT guid FROM path_list WHERE path = 'Root Account:Assets:JPY - Current Assets:Prepaid:Suica iPhone';
```

Note: `name::text` cast is required. Without it, PostgreSQL raises a type mismatch error because `name` is `varchar(2048)` but concatenation produces `text`.

### Find JPY currency GUID

```sql
SELECT guid FROM commodities WHERE namespace = 'CURRENCY' AND mnemonic = 'JPY';
```

### Currency GUIDs (Cache)

| Currency | GUID |
|----------|------|
| CAD | f99a2253eb074ecc9cdf1d9e045d80a4 |
| EUR | 12acd461abfd4f3abc3035fadee5a376 |
| HKD | fe612fdac8294a05a11469ccc2e2637d |
| JPY | a77d4ee821e04f02bb7429e437c645e4 |
| KRW | 11e24d99cb3047d8a6e7bd89f7289fc5 |
| MOP | 5baf61e3637342d78e2df019598c4426 |
| SGD | b5f7dd0afe724e799dd2f62106f920ab |
| THB | 7484252199024c678cd3252dbaec76f5 |
| TRY | cdde4a47486d4033927156ffdc8e9a87 |
| USD | 327c5a1bcfb147ceba2370ee17093159 |

## References

- https://wiki.gnucash.org/wiki/SQL
- https://wiki.gnucash.org/wiki/GnuCash_SQL_Examples
