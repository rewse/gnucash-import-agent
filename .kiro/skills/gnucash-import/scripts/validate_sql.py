#!/usr/bin/env python3
"""Validate generated GnuCash import SQL before database execution."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import NamedTuple

if not __debug__:
    print(
        "Error: SQL validation must run without Python optimization.",
        file=sys.stderr,
    )
    sys.exit(2)

_GUID = r"[0-9a-f]{32}"
_TIMESTAMP = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
_DESCRIPTION = r"NULL|'(?:''|[^'])*'"
_TRANSACTION_RE = re.compile(
    rf"INSERT\s+INTO\s+transactions\s*"
    rf"\(guid,\s*currency_guid,\s*num,\s*post_date,\s*enter_date,\s*description\)\s*"
    rf"VALUES\s*\('({_GUID})',\s*'({_GUID})',\s*'',\s*'({_TIMESTAMP})',\s*"
    rf"NOW\(\),\s*({_DESCRIPTION})\)\Z",
    re.IGNORECASE,
)
_SPLIT_RE = re.compile(
    rf"INSERT\s+INTO\s+splits\s*"
    rf"\(guid,\s*tx_guid,\s*account_guid,\s*memo,\s*action,\s*reconcile_state,\s*"
    rf"reconcile_date,\s*value_num,\s*value_denom,\s*quantity_num,\s*"
    rf"quantity_denom,\s*lot_guid\)\s*"
    rf"VALUES\s*\('({_GUID})',\s*'({_GUID})',\s*'({_GUID})',\s*'',\s*'',\s*"
    rf"'([^']*)',\s*NULL,\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*"
    rf"NULL\)\Z",
    re.IGNORECASE,
)


class ValidationError(ValueError):
    """Raised when generated SQL violates an import safety rule."""


class ValidationResult(NamedTuple):
    transaction_count: int
    split_count: int


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def split_sql_statements(sql: str) -> list[str]:
    """Split SQL on semicolons outside strings and remove line comments."""
    sql = sql.replace("\r\n", "\n").replace("\r", "\n")
    statements: list[str] = []
    current: list[str] = []
    index = 0
    in_string = False
    while index < len(sql):
        character = sql[index]
        if in_string:
            current.append(character)
            if character == "'":
                if index + 1 < len(sql) and sql[index + 1] == "'":
                    current.append("'")
                    index += 1
                else:
                    in_string = False
        elif character == "'":
            in_string = True
            current.append(character)
        elif sql.startswith("--", index):
            newline = sql.find("\n", index)
            if newline == -1:
                index = len(sql)
                continue
            current.append("\n")
            index = newline
        elif character == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(character)
        index += 1
    _require(not in_string, "SQL contains an unterminated string literal")
    trailing = "".join(current).strip()
    _require(not trailing, "SQL contains an unterminated statement")
    return statements


def _decode_description(raw_description: str) -> str | None:
    if raw_description.upper() == "NULL":
        return None
    return raw_description[1:-1].replace("''", "'")


def validate_sql(
    sql: str,
    source_account_guid: str,
    account_guids: set[str],
    expected_currency_guid: str,
    allow_counterparty_unreconciled: bool = False,
) -> ValidationResult:
    """Validate one generated SQL file and return its row counts."""
    _require(re.fullmatch(_GUID, source_account_guid) is not None, "invalid source GUID")
    _require(
        re.fullmatch(_GUID, expected_currency_guid) is not None,
        "invalid expected currency GUID",
    )
    _require(source_account_guid in account_guids, "source account is absent from cache")
    statements = split_sql_statements(sql)
    _require(len(statements) >= 4, "SQL contains no complete transaction")
    _require(statements[0].upper() == "BEGIN", "SQL must start with BEGIN")
    _require(statements[-1].upper() == "COMMIT", "SQL must end with COMMIT")

    transaction_order: list[str] = []
    timestamps: list[str] = []
    splits_by_transaction: dict[str, list[tuple[str, Fraction, int, int]]] = defaultdict(list)
    known_guids: set[str] = set()
    current_transaction: str | None = None
    split_count = 0

    for statement in statements[1:-1]:
        transaction_match = _TRANSACTION_RE.fullmatch(statement)
        if transaction_match:
            guid, currency_guid, timestamp, raw_description = transaction_match.groups()
            _require(guid not in known_guids, "duplicate generated GUID")
            _require(
                currency_guid == expected_currency_guid,
                "transaction currency does not match expected currency",
            )
            try:
                datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            except ValueError as error:
                raise ValidationError("transaction has an invalid timestamp") from error
            known_guids.add(guid)
            description = _decode_description(raw_description)
            _require(
                description is None
                or all(32 <= ord(character) <= 126 for character in description),
                "description must contain only printable ASCII or be NULL",
            )
            _require(
                description is None or "\\" not in description,
                "description must not contain a backslash",
            )
            transaction_order.append(guid)
            timestamps.append(timestamp)
            current_transaction = guid
            continue

        split_match = _SPLIT_RE.fullmatch(statement)
        _require(split_match is not None, "SQL contains a forbidden or malformed statement")
        (
            guid,
            tx_guid,
            account_guid,
            reconcile_state,
            value_num,
            value_denom,
            quantity_num,
            quantity_denom,
        ) = split_match.groups()
        _require(current_transaction is not None, "split appears before its transaction")
        _require(tx_guid == current_transaction, "split is not adjacent to its transaction")
        _require(guid not in known_guids, "duplicate generated GUID")
        known_guids.add(guid)
        _require(account_guid in account_guids, "split account is absent from cache")
        if allow_counterparty_unreconciled:
            if account_guid == source_account_guid:
                _require(reconcile_state == "c", "source split must be cleared")
            else:
                _require(
                    reconcile_state in {"c", "n"},
                    "counterparty split must be cleared or unreconciled",
                )
        else:
            _require(reconcile_state == "c", "every imported split must be cleared")
        value_denominator = int(value_denom)
        quantity_denominator = int(quantity_denom)
        _require(value_denominator > 0, "value denominator must be positive")
        _require(quantity_denominator > 0, "quantity denominator must be positive")
        value_numerator = int(value_num)
        quantity_numerator = int(quantity_num)
        _require(value_numerator != 0, "zero-value splits are not allowed")
        _require(quantity_numerator != 0, "zero-quantity splits are not allowed")
        _require(
            value_numerator * quantity_numerator > 0,
            "value and quantity signs must agree",
        )
        splits_by_transaction[tx_guid].append(
            (
                account_guid,
                Fraction(value_numerator, value_denominator),
                quantity_numerator,
                quantity_denominator,
            )
        )
        split_count += 1

    _require(transaction_order, "SQL contains no transactions")
    for guid in transaction_order:
        splits = splits_by_transaction.get(guid, [])
        _require(len(splits) >= 2, "each transaction needs at least two splits")
        _require(
            sum((split[1] for split in splits), start=Fraction()) == 0,
            "transaction does not balance",
        )
        source_splits = [split for split in splits if split[0] == source_account_guid]
        _require(len(source_splits) == 1, "transaction must have one source split")

    by_date: dict[str, list[str]] = defaultdict(list)
    for timestamp in timestamps:
        by_date[timestamp[:10]].append(timestamp)
    for date, values in by_date.items():
        _require(len(values) == len(set(values)), f"duplicate post_date time on {date}")
        _require(values == sorted(values, reverse=True), f"unstable same-day order on {date}")

    return ValidationResult(len(transaction_order), split_count)


def find_project_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".kiro/skills/gnucash-import").is_dir():
            return candidate
    raise ValidationError("cannot locate repository root")


def load_account_cache(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError("cannot read account GUID cache") from error
    raw_accounts = data.get("accounts") if isinstance(data, dict) else None
    _require(isinstance(raw_accounts, dict), "malformed account GUID cache")
    accounts: dict[str, str] = {}
    for account_path, guid in raw_accounts.items():
        _require(isinstance(account_path, str), "malformed account GUID cache")
        _require(isinstance(guid, str), "malformed account GUID cache")
        _require(re.fullmatch(_GUID, guid) is not None, "malformed account GUID cache")
        accounts[account_path.removeprefix("Root Account:")] = guid
    return accounts


def main() -> int:
    root = find_project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql_file", type=Path)
    parser.add_argument("--source-account", required=True)
    parser.add_argument("--currency-guid", required=True)
    parser.add_argument(
        "--allow-counterparty-unreconciled",
        action="store_true",
        help="Allow non-source splits to use reconcile_state n; source splits still require c.",
    )
    parser.add_argument(
        "--account-cache",
        type=Path,
        default=root / ".kiro/skills/gnucash-import/references/account-guid-cache.json",
    )
    arguments = parser.parse_args()
    try:
        accounts = load_account_cache(arguments.account_cache)
        source_guid = accounts.get(arguments.source_account)
        _require(source_guid is not None, "source account is absent from cache")
        result = validate_sql(
            arguments.sql_file.read_text(),
            source_guid,
            set(accounts.values()),
            arguments.currency_guid,
            allow_counterparty_unreconciled=(
                arguments.allow_counterparty_unreconciled
            ),
        )
    except (OSError, ValidationError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(
        f"Validated {result.transaction_count} transactions and "
        f"{result.split_count} splits."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
