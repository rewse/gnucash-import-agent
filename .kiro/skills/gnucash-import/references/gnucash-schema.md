# GnuCash PostgreSQL schema reference

Use these fields when import scripts query accounts and generate transactions. GnuCash defines its string columns as `varchar`, while recursive path concatenation produces PostgreSQL `text`.

## Fields used by import scripts

### transactions

| Field | Type | Use |
|---|---|---|
| `guid` | `char(32)` | Transaction identifier |
| `currency_guid` | `char(32)` | Transaction currency |
| `num` | `varchar(2048)` | Transaction number, usually empty |
| `post_date` | `timestamp` | Statement date and sort time |
| `enter_date` | `timestamp` | Insert time |
| `description` | `varchar(2048)` | English description or NULL |

### splits

| Field | Type | Use |
|---|---|---|
| `guid` | `char(32)` | Split identifier |
| `tx_guid` | `char(32)` | Parent transaction |
| `account_guid` | `char(32)` | GnuCash account |
| `memo` | `varchar(2048)` | Split memo, usually empty |
| `action` | `varchar(2048)` | Split action, usually empty |
| `reconcile_state` | `varchar(1)` | `c` for statement-cleared, `n` for unverified, `y` for reconciled |
| `reconcile_date` | `timestamp` | NULL until reconciliation supplies a date |
| `value_num`, `value_denom` | `bigint` | Amount in transaction currency |
| `quantity_num`, `quantity_denom` | `bigint` | Amount or quantity in the account commodity |
| `lot_guid` | `char(32)` | Lot identifier when used, otherwise NULL |

### accounts

| Field | Type | Use |
|---|---|---|
| `guid` | `char(32)` | Account identifier |
| `name` | `varchar(2048)` | Account name |
| `parent_guid` | `char(32)` | Parent used to build a full path |
| `commodity_guid` | `char(32)` | Account commodity |
| `hidden`, `placeholder` | `integer` | Exclude non-posting accounts from the cache |

### commodities and prices

| Table | Fields used |
|---|---|
| `commodities` | `guid`, `namespace`, `mnemonic`, `fraction` |
| `prices` | `guid`, `commodity_guid`, `currency_guid`, `date`, `source`, `type`, `value_num`, `value_denom` |

## GUIDs

Generate a 32-character lowercase hexadecimal GUID without hyphens:

```python
import uuid

guid = uuid.uuid4().hex
```

## Values and quantities

Store each rational number as `num / denom`. JPY normally uses denominator `1`; USD normally uses denominator `100`. `value` is in the transaction currency, while `quantity` is in the account commodity. They differ when a foreign-currency transaction touches an account in another commodity.

Sum account balances with `quantity`, preserving each denominator:

```sql
SELECT SUM(s.quantity_num::numeric / s.quantity_denom)
FROM splits s
JOIN accounts a ON s.account_guid = a.guid
WHERE a.name = '{account_name}';
```

Do not sum raw `value_num` values across transactions with different currencies or denominators.

## Transactions

Create one transaction and at least two balancing splits. Use `c` on every split when the imported row has been verified against a statement:

```sql
INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)
VALUES ('tx_guid', 'a77d4ee821e04f02bb7429e437c645e4', '', '2026-02-01 00:00:01', NOW(), 'Train fare');

INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)
VALUES
  ('split1_guid', 'tx_guid', 'suica_guid', '', '', 'c', NULL, -500, 1, -500, 1, NULL),
  ('split2_guid', 'tx_guid', 'transport_guid', '', '', 'c', NULL, 500, 1, 500, 1, NULL);
```

Use `n` for a generic transaction that has not been checked against a statement:

```sql
INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)
VALUES
  ('split1_guid', 'tx_guid', 'asset_guid', '', '', 'n', NULL, -1000, 1, -1000, 1, NULL),
  ('split2_guid', 'tx_guid', 'expense_guid', '', '', 'n', NULL, 1000, 1, 1000, 1, NULL);
```

Include a time in `post_date`. When statement rows lack times, assign stable row-index times so same-day rows retain their source order.

## Account and commodity queries

Cast the recursive seed path to `text` because `accounts.name` is `varchar(2048)` and concatenation returns `text`:

```sql
WITH RECURSIVE path_list AS (
  SELECT guid, parent_guid, name, name::text AS path
  FROM accounts
  WHERE parent_guid IS NULL
  UNION ALL
  SELECT child.guid, child.parent_guid, child.name, parent.path || ':' || child.name
  FROM accounts child
  JOIN path_list parent ON parent.guid = child.parent_guid
)
SELECT guid
FROM path_list
WHERE path = 'Root Account:Assets:JPY - Current Assets:Prepaid:Suica iPhone';
```

Resolve a currency GUID from the database or cache instead of embedding an unverified value:

```sql
SELECT guid
FROM commodities
WHERE namespace = 'CURRENCY' AND mnemonic = 'JPY';
```

## References

- <https://wiki.gnucash.org/wiki/GnuCash_SQL_Examples>
- <https://wiki.gnucash.org/wiki/SQL>
