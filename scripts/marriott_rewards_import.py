#!/usr/bin/env python3
"""
Marriott Rewards Statement Importer

Usage:
1. Copy raw data into raw.txt (tab-separated: date, description, amount, account)
2. Run: python3 scripts/marriott_rewards_import.py review    # Review transactions
3. Run: python3 scripts/marriott_rewards_import.py sql       # Generate SQL
"""

import json
import os
import uuid
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


def find_project_root():
    configured_root = os.environ.get("GNUCASH_IMPORT_ROOT")
    candidates = [Path(configured_root)] if configured_root else []
    candidates.extend([Path.cwd(), Path(__file__).resolve().parent.parent])
    for candidate in candidates:
        if (candidate / ".kiro/skills/gnucash-import").is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot find the repository root. Run from the repository root or set GNUCASH_IMPORT_ROOT."
    )


PROJECT_ROOT = find_project_root()
ACCOUNTS_FILE = (
    PROJECT_ROOT / ".kiro/skills/gnucash-import/references/account-guid-cache.json"
)


def load_accounts():
    with open(ACCOUNTS_FILE) as account_file:
        data = json.load(account_file)
    raw_accounts = data.get("accounts") if isinstance(data, dict) else None
    if not isinstance(raw_accounts, dict):
        raise ValueError("Malformed account GUID cache.")
    accounts = {}
    for path, value in raw_accounts.items():
        if (
            not isinstance(path, str)
            or not isinstance(value, str)
            or len(value) != 32
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("Malformed account GUID cache.")
        accounts[path.replace("Root Account:", "")] = value
    return accounts


ACCOUNTS = load_accounts()


def get_guid(path):
    """Return the cached GUID for an account path, or exit when it is missing.

    An unresolved path would otherwise be written as account_guid 'None'.
    The error omits the path because it can come from statement data.
    """
    guid = ACCOUNTS.get(path) or ACCOUNTS.get("Root Account:" + path)
    if guid is None:
        print(
            "Error: an account path is missing from account-guid-cache.json. "
            "Refresh the cache or correct the mapping.",
            file=sys.stderr,
        )
        sys.exit(1)
    return guid


SOURCE_ACCOUNT = get_guid(
    "Assets:JPY - Current Assets:Reward Programs:Marriott Rewards"
)
POINT_CHARGE = get_guid("Income:Point Charge")
RAKUTEN_POINT = get_guid(
    "Assets:JPY - Current Assets:Reward Programs:Rakuten Super Point"
)
CHARITY = get_guid("Expenses:Social Expenses:Charity")
JPY_CURRENCY = "a77d4ee821e04f02bb7429e437c645e4"

ACCOUNT_NAMES = {
    POINT_CHARGE: "Income:Point Charge",
    RAKUTEN_POINT: "Rakuten Super Point",
    CHARITY: "Expenses:Social Expenses:Charity",
}

# 1 point = 0.33 JPY
POINT_TO_JPY_NUM = 33
POINT_TO_JPY_DENOM = 100


def points_to_jpy(points):
    """Convert points to JPY (1 pt = 0.33 JPY)."""
    return points * POINT_TO_JPY_NUM // POINT_TO_JPY_DENOM


# ============================================================
# Statement data loading
# ============================================================
RAW_DATA_FILE = "raw.txt"


# Bidirectional formatting characters can reorder review table columns.
BIDI_CONTROLS = frozenset(
    "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
)


def strip_control_characters(text):
    """Remove control characters other than tab and newline.

    Statement text is echoed into SQL comments, where PostgreSQL ends a
    comment at a carriage return, and into the review table, where terminal
    escapes can rewrite rows. Stripping at load time keeps both identical.
    """
    return "".join(
        character
        for character in text
        if character in "\t\n"
        or (unicodedata.category(character) != "Cc" and character not in BIDI_CONTROLS)
    )


def load_raw_data(file_name=RAW_DATA_FILE, environment_variable="GNUCASH_RAW_DATA"):
    """Read statement data from a UTF-8 file next to this script.

    Keep statement text out of Python source: a triple quote or escape
    sequence in a merchant name would otherwise run as code or change bytes.
    The environment variable, when set, names the file to read instead.
    """
    configured = os.environ.get(environment_variable)
    path = (
        Path(configured)
        if configured
        else Path(__file__).resolve().with_name(file_name)
    )
    try:
        # newline="" keeps a carriage return inside a field from splitting a row.
        with open(path, encoding="utf-8-sig", newline="") as raw_file:
            text = raw_file.read()
    except FileNotFoundError:
        return ""
    return strip_control_characters(text.replace("\r\n", "\n"))


# ============================================================
# Statement data: write it to raw.txt next to this script, or set
# GNUCASH_RAW_DATA to the file path. Never paste statement text here.
# Format: date\tdescription\tamount\taccount
# ============================================================
RAW_DATA = load_raw_data()

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# ============================================================
MANUAL_OVERRIDES = {}


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        date_str, desc, amount_str, account_path = parts[:4]
        transactions.append(
            {
                "date": datetime.strptime(date_str, "%Y/%m/%d"),
                "desc": desc,
                "amount": int(amount_str.replace(",", "")),
                "account": get_guid(account_path),
            }
        )
    transactions.sort(key=lambda x: x["date"], reverse=True)
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    return tx["account"], tx["desc"]


def output_review(transactions):
    print(
        f"{'ID':<4} {'Date':<14} {'Desc':<40} {'Transfer':<30} {'Increase':>10} {'Decrease':>10}"
    )
    print("-" * 115)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
            tx["date"].weekday()
        ]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 115)
        prev_date = date_str

        account_guid, description = get_transaction_info(idx, tx)
        transfer = ACCOUNT_NAMES.get(account_guid, account_guid or "")
        increase = (
            f"{tx['amount']:,} pt (¥{points_to_jpy(tx['amount']):,})"
            if tx["amount"] > 0
            else ""
        )
        decrease = (
            f"{abs(tx['amount']):,} pt (¥{points_to_jpy(abs(tx['amount'])):,})"
            if tx["amount"] < 0
            else ""
        )

        print(
            f"{idx:<4} {date_str:<14} {description or '':<40} {transfer:<30} {increase:>10} {decrease:>10}"
        )


def output_sql(transactions):
    print("BEGIN;")
    print()

    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account_guid, description = get_transaction_info(idx, tx)
        jpy_value = points_to_jpy(tx["amount"])

        tx_guid = uuid.uuid4().hex
        split1_guid = uuid.uuid4().hex
        split2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx["date"].strftime(f"%Y-%m-%d 00:{minutes:02d}:{seconds:02d}")
        desc_sql = (
            f"'{description.replace(chr(39), chr(39) * 2)}'" if description else "NULL"
        )
        sign = "+" if tx["amount"] > 0 else ""

        print(
            f"-- {idx}: {tx['date'].strftime('%Y-%m-%d')} {description} {sign}{tx['amount']:,} pt (¥{jpy_value:,})"
        )
        print(
            f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)"
        )
        print(
            f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});"
        )
        print(
            f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
        )
        print(
            f"VALUES ('{split1_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'c', NULL, {jpy_value}, 1, {jpy_value}, 1, NULL);"
        )
        print(
            f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
        )
        print(
            f"VALUES ('{split2_guid}', '{tx_guid}', '{account_guid}', '', '', 'c', NULL, {-jpy_value}, 1, {-jpy_value}, 1, NULL);"
        )
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ["review", "sql"]:
        print("Usage: python3 marriott_rewards_import.py [review|sql]", file=sys.stderr)
        sys.exit(1)

    if not RAW_DATA.strip():
        print(
            "Error: statement data is empty. Write it to raw.txt next to this script or set GNUCASH_RAW_DATA.",
            file=sys.stderr,
        )
        sys.exit(1)

    transactions = parse_transactions(RAW_DATA)

    if sys.argv[1] == "review":
        output_review(transactions)
    else:
        output_sql(transactions)


if __name__ == "__main__":
    main()
