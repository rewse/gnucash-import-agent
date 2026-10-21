#!/usr/bin/env python3
"""Luxury Card Mastercard Titanium Statement Importer

Usage:
1. Copy raw data from browser snapshot into raw.txt (card) or raw-points.txt (points)
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 scripts/luxury_card_mastercard_titanium_import.py review
4. Run: python3 scripts/luxury_card_mastercard_titanium_import.py sql
5. Run: python3 scripts/luxury_card_mastercard_titanium_import.py points-review
6. Run: python3 scripts/luxury_card_mastercard_titanium_import.py points-sql
"""

import json
import os
import re
import sys
import unicodedata
import uuid
from datetime import date
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


SOURCE_ACCOUNT = get_guid("Liabilities:Credit Card:Luxury Card Mastercard Titanium")
POINTS_ACCOUNT = get_guid("Assets:JPY - Current Assets:Reward Programs:Luxury Reward")
POINT_INCOME = get_guid("Income:Point Charge")
JPY_CURRENCY = "a77d4ee821e04f02bb7429e437c645e4"

# Transaction type mappings
DINING = get_guid("Expenses:Foods:Dining")
FOODSTUFFS = get_guid("Expenses:Foods:Foodstuffs")
BIKE = get_guid("Expenses:Bike")
HOUSE_MAINT = get_guid("Expenses:House:Maintenance")
CLOTHES = get_guid("Expenses:Clothes")
SPORTS = get_guid("Expenses:Entertainment:Sports")
BOOKS = get_guid("Expenses:Entertainment:Books")
PHONE_MOBILE = get_guid("Expenses:Utilities:Phone:Mobile")
FURUSATO = get_guid("Expenses:Tax:Furusato Tax")
INSURANCES = get_guid("Expenses:Insurances")
SUPPLIES = get_guid("Expenses:Supplies")
INTERNET = get_guid("Expenses:Utilities:Internet")
PHONE_LANDLINE = get_guid("Expenses:Utilities:Phone:Landline")
INSURANCES_HEALTH = get_guid("Expenses:Insurances:Health Insurances")

ACCOUNT_NAMES = {
    DINING: "Expenses:Foods:Dining",
    FOODSTUFFS: "Expenses:Foods:Foodstuffs",
    BIKE: "Expenses:Bike",
    HOUSE_MAINT: "Expenses:House:Maintenance",
    CLOTHES: "Expenses:Clothes",
    SPORTS: "Expenses:Entertainment:Sports",
    BOOKS: "Expenses:Entertainment:Books",
    PHONE_MOBILE: "Expenses:Utilities:Phone:Mobile",
    FURUSATO: "Expenses:Tax:Furusato Tax",
    INSURANCES: "Expenses:Insurances",
    SUPPLIES: "Expenses:Supplies",
    INTERNET: "Expenses:Utilities:Internet",
    PHONE_LANDLINE: "Expenses:Utilities:Phone:Landline",
    INSURANCES_HEALTH: "Expenses:Insurances:Health Insurances",
    POINTS_ACCOUNT: "Luxury Reward",
    POINT_INCOME: "Income:Point Charge",
}

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
# Statement data: write card rows to raw.txt and point rows to raw-points.txt
# next to this script, or set GNUCASH_RAW_DATA and GNUCASH_RAW_DATA_POINTS to
# the file paths. Never paste statement text here.
# ============================================================
RAW_DATA = load_raw_data()

RAW_DATA_POINTS = load_raw_data("raw-points.txt", "GNUCASH_RAW_DATA_POINTS")

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# For KDDI split: ID: 'KDDI'
# ============================================================
MANUAL_OVERRIDES = {}


def normalize(s):
    """Convert full-width ASCII to half-width."""
    return s.translate(
        str.maketrans(
            "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９．＊　",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.* ",
        )
    )


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(
            r"(.+?)(\d{2})\.(\d{2})\.(\d{2})\s*\d+回払い\s*(?:お支払い方法変更可能\s*)?([\d,]+)円",
            line,
        )
        if not m:
            continue
        merchant = m.group(1).strip()
        yy, mm, dd = int(m.group(2)), int(m.group(3)), int(m.group(4))
        amount = int(m.group(5).replace(",", ""))
        transactions.append(
            {
                "date": date(2000 + yy, mm, dd),
                "amount": -amount,
                "merchant": merchant,
                "merchant_norm": normalize(merchant),
            }
        )
    return transactions


def parse_points(raw_data):
    transactions = []
    for line in raw_data.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        ym = parts[0].strip()
        points = int(parts[1].strip())
        y, m = ym.split("-")
        transactions.append(
            {
                "date": date(int(y), int(m), 15),
                "amount": points,
            }
        )
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        v = MANUAL_OVERRIDES[idx]
        if v == "KDDI":
            return "KDDI", "KDDI"
        return v
    m = tx["merchant"]
    mn = tx["merchant_norm"]
    if "カブシキガイシヤループ" in m:
        return BIKE, "LUUP"
    if "SQ*" in mn and "マラドウ" in m:
        return DINING, "Mala Do"
    if "ロイヤルホスト" in m:
        return DINING, "Royal Host"
    if "マクドナルド" in m:
        return DINING, "McDonald's"
    if "サブウエイ" in m:
        return DINING, "Subway"
    if "ヨ－クフ－ズ" in m:
        return FOODSTUFFS, "York Foods"
    if "シヤトレーゼ" in m:
        return FOODSTUFFS, "Chateraise"
    if "パルシステム" in m:
        return INSURANCES_HEALTH, "Palsystem"
    if "ココカラフアイン" in m:
        return SUPPLIES, "Cocokara Fine"
    if "カジ－" in m:
        return HOUSE_MAINT, "CaSy"
    if "ユニクロ" in m:
        return CLOTHES, "UNIQLO"
    if "パ－ソナルジムアスピ" in m:
        return SPORTS, "ASPI"
    if "ラクテンマガジン" in m:
        return BOOKS, "Rakuten Magazine"
    if "ノート" == m:
        return BOOKS, "note"
    if "ＵＱｍｏｂｉｌｅ" in m:
        return PHONE_MOBILE, "UQ Mobile"
    if "ニホンツウシンカブシキガイシヤ" in m:
        return PHONE_MOBILE, "Nihon Tsushin"
    if "フルナビマネー" in m:
        return FURUSATO, "Furunavi"
    if "ミカタシヨウガクタンキホケン" in m:
        return INSURANCES, "MIKATA Small Amount Short Term Insurance"
    if "ＫＤＤＩ" in m:
        return "KDDI", "KDDI"
    raise ValueError(f"Unknown transaction at ID {idx}: {tx['merchant']}")


# KDDI bills a fixed internet fee; the landline split absorbs the variable remainder.
KDDI_INTERNET_AMOUNT = 4454


def kddi_splits(charge):
    landline = charge - KDDI_INTERNET_AMOUNT
    if landline <= 0:
        raise ValueError(f"KDDI charge {charge} does not exceed the fixed internet fee")
    return [
        (INTERNET, KDDI_INTERNET_AMOUNT, "KDDI Internet"),
        (PHONE_LANDLINE, landline, "KDDI Phone"),
    ]


def output_review(transactions):
    print(
        f"{'ID':<4} {'Date':<14} {'Merchant':<30} {'Desc':<25} {'Transfer':<40} {'Amount':>10}"
    )
    print("-" * 127)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if prev_date and prev_date != tx["date"]:
            print("-" * 127)
        prev_date = tx["date"]
        account, description = get_transaction_info(idx, tx)
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        date_str = f"{tx['date']} {weekday[tx['date'].weekday()]}"
        if account == "KDDI":
            for acct, amt, desc in kddi_splits(abs(tx["amount"])):
                transfer = ACCOUNT_NAMES.get(acct, acct or "")
                print(
                    f"{idx:<4} {date_str:<14} {'KDDI':<30} {desc:<25} {transfer:<40} {f'¥{amt:,}':>10}"
                )
        else:
            transfer = ACCOUNT_NAMES.get(account, account or "")
            amt = f"¥{abs(tx['amount']):,}"
            merchant_display = tx["merchant_norm"][:28]
            print(
                f"{idx:<4} {date_str:<14} {merchant_display:<30} {description or '':<25} {transfer:<40} {amt:>10}"
            )


def output_sql(transactions):
    print("BEGIN;")
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account, description = get_transaction_info(idx, tx)
        tx_date = tx["date"]
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx_date} 00:{minutes:02d}:{seconds:02d}"

        if account == "KDDI":
            # Multi-split transaction
            tx_guid = uuid.uuid4().hex
            s_source_guid = uuid.uuid4().hex
            desc_sql = "'KDDI'"
            print(
                "INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)"
            )
            print(
                f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});"
            )
            print(
                "INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
            )
            print(
                f"VALUES ('{s_source_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'c', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);"
            )
            for acct, amt, _ in kddi_splits(abs(tx["amount"])):
                s_guid = uuid.uuid4().hex
                print(
                    "INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
                )
                print(
                    f"VALUES ('{s_guid}', '{tx_guid}', '{acct}', '', '', 'c', NULL, {amt}, 1, {amt}, 1, NULL);"
                )
            print()
        else:
            tx_guid = uuid.uuid4().hex
            s1_guid = uuid.uuid4().hex
            s2_guid = uuid.uuid4().hex
            desc_sql = (
                f"'{description.replace(chr(39), chr(39) * 2)}'"
                if description
                else "NULL"
            )
            print(
                "INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)"
            )
            print(
                f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});"
            )
            print(
                "INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
            )
            print(
                f"VALUES ('{s1_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'c', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);"
            )
            print(
                "INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
            )
            print(
                f"VALUES ('{s2_guid}', '{tx_guid}', '{account}', '', '', 'c', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);"
            )
            print()
    print("COMMIT;")


def output_points_review(transactions):
    print(f"{'ID':<4} {'Date':<12} {'Points':>10} {'Transfer':<30}")
    print("-" * 60)
    for idx, tx in enumerate(transactions, 1):
        pts = f"{tx['amount']:+,}"
        print(
            f"{idx:<4} {tx['date'].strftime('%Y-%m'):<12} {pts:>10} {'Income:Point Charge':<30}"
        )


def output_points_sql(transactions):
    print("BEGIN;")
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        tx_guid = uuid.uuid4().hex
        s1_guid = uuid.uuid4().hex
        s2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date']} 00:{minutes:02d}:{seconds:02d}"
        print(
            "INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)"
        )
        print(
            f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), 'Luxury Reward');"
        )
        print(
            "INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
        )
        print(
            f"VALUES ('{s1_guid}', '{tx_guid}', '{POINTS_ACCOUNT}', '', '', 'c', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);"
        )
        print(
            "INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)"
        )
        print(
            f"VALUES ('{s2_guid}', '{tx_guid}', '{POINT_INCOME}', '', '', 'c', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);"
        )
        print()
    print("COMMIT;")


def main():
    cmds = ("review", "sql", "points-review", "points-sql")
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(
            f"Usage: python3 luxury_card_mastercard_titanium_import.py [{'|'.join(cmds)}]",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd.startswith("points"):
        if not RAW_DATA_POINTS.strip():
            print(
                "Error: statement data is empty. Write it to raw-points.txt next to this script or set GNUCASH_RAW_DATA_POINTS.",
                file=sys.stderr,
            )
            sys.exit(1)
        transactions = parse_points(RAW_DATA_POINTS)
        if cmd == "points-review":
            output_points_review(transactions)
        else:
            output_points_sql(transactions)
    else:
        if not RAW_DATA.strip():
            print(
                "Error: statement data is empty. Write it to raw.txt next to this script or set GNUCASH_RAW_DATA.",
                file=sys.stderr,
            )
            sys.exit(1)
        transactions = parse_transactions(RAW_DATA)
        if cmd == "review":
            output_review(transactions)
        else:
            output_sql(transactions)


if __name__ == "__main__":
    main()
