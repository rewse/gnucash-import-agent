#!/usr/bin/env python3
"""Sompo Japan DC Securities Statement Importer

Usage:
1. Copy raw data from browser eval into raw.txt
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 scripts/sompo_japan_dc_import.py review    # Review transactions
4. Run: python3 scripts/sompo_japan_dc_import.py sql       # Generate SQL
"""

import json
import os
import re
import sys
import unicodedata
import uuid
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
        raise ValueError("Malformed account GUID cache.")  # noqa: TRY004 a malformed cache file is bad data, and tests expect ValueError
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
    return ACCOUNTS.get(path) or ACCOUNTS.get("Root Account:" + path)


DC = "Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities"
SOURCE_ACCOUNT = get_guid(DC)

FUND_MAP = {
    "ＤＩＡＭ国内株式インデックス": f"{DC}:One Japan Stock Index Fund <DC Pension>",
    "Ｏｎｅ国内株式インデックス": f"{DC}:One Japan Stock Index Fund <DC Pension>",
    "インデックス海外株式ヘッジなし": f"{DC}:Index Fund Global Stock NoHedge (DC)",
}

CURRENCIES = {"JPY": "a77d4ee821e04f02bb7429e437c645e4"}
CURRENCY_DENOM = {"JPY": 1}

# Fund units are stored as 口 * 10000 in GnuCash (quantity_denom=10000)
FUND_QTY_DENOM = 10000

ACCOUNT_NAMES = {get_guid(v): v.split(":")[-1] for v in FUND_MAP.values()}
ACCOUNT_NAMES[SOURCE_ACCOUNT] = "Sompo Japan DC Securities"

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
        if not re.match(r"\d{4}/\d{2}/\d{2}\t", line):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        trade_date, settle_date, fund_name, qty, unit_price, amount, tx_type = parts[:7]
        transactions.append(
            {
                "date": datetime.strptime(settle_date, "%Y/%m/%d").date(),
                "trade_date": datetime.strptime(trade_date, "%Y/%m/%d").date(),
                "fund_name": fund_name.strip(),
                "quantity": int(qty.replace(",", "")),
                "unit_price": float(unit_price.replace(",", "")),
                "amount": int(amount.replace(",", "")),
                "tx_type": tx_type.strip(),
            }
        )
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    for key, path in FUND_MAP.items():
        if key in tx["fund_name"]:
            return get_guid(path), None
    raise ValueError(f"Unknown fund: {tx['fund_name']}")


def output_review(transactions):
    print(
        f"{'ID':<4} {'Date':<14} {'Fund':<30} {'Qty':>8} {'Price':>10} {'Amount':>10} {'Fund Account':<40}"
    )
    print("-" * 120)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
            tx["date"].weekday()
        ]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"
        if prev_date and prev_date != date_str:
            print("-" * 120)
        prev_date = date_str
        fund_account, _ = get_transaction_info(idx, tx)
        transfer = ACCOUNT_NAMES.get(fund_account, fund_account or "")
        amt = f"¥{tx['amount']:,}"
        print(
            f"{idx:<4} {date_str:<14} {tx['fund_name'][:30]:<30} {tx['quantity']:>8} {tx['unit_price']:>10.4f} {amt:>10} {transfer:<40}"
        )


def output_sql(transactions):
    print("BEGIN;")
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        fund_account, description = get_transaction_info(idx, tx)
        tx_guid = uuid.uuid4().hex
        split1_guid = uuid.uuid4().hex
        split2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx["date"].strftime(f"%Y-%m-%d 00:{minutes:02d}:{seconds:02d}")
        desc_sql = (
            f"'{description.replace(chr(39), chr(39) * 2)}'" if description else "NULL"
        )
        amount = tx["amount"]
        qty_num = tx["quantity"] * FUND_QTY_DENOM

        print(
            "INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)"
        )
        print(
            f"VALUES ('{tx_guid}', '{CURRENCIES['JPY']}', '', '{date_str}', NOW(), {desc_sql});"
        )
        # Fund split: value=amount (denom=1), quantity=口*10000 (denom=10000)
        print(
            "INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
        )
        print(
            f"VALUES ('{split1_guid}', '{tx_guid}', '{fund_account}', '', '', 'c', NULL, {amount}, 1, {qty_num}, {FUND_QTY_DENOM}, NULL);"
        )
        # Source (cash) split: 1:1
        print(
            "INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
        )
        print(
            f"VALUES ('{split2_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'c', NULL, {-amount}, 1, {-amount}, 1, NULL);"
        )
        print()
    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ["review", "sql"]:
        print("Usage: python3 sompo_japan_dc_import.py [review|sql]", file=sys.stderr)
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
