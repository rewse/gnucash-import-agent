#!/usr/bin/env python3
"""
GOLD POINT CARD + Statement Importer

Usage:
1. Copy raw data from browser snapshot into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 scripts/gold_point_card_plus_import.py review    # Review transactions
4. Run: python3 scripts/gold_point_card_plus_import.py sql       # Generate SQL
"""
import json
import os
import uuid
import sys
import re
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
ACCOUNTS_FILE = PROJECT_ROOT / ".kiro/skills/gnucash-import/references/account-guid-cache.json"


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
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

SOURCE_ACCOUNT = get_guid('Liabilities:Credit Card:GOLD POINT CARD +')

CURRENCIES = {
    'JPY': 'a77d4ee821e04f02bb7429e437c645e4',
}
CURRENCY_DENOM = {'JPY': 1}

ACCOUNT_NAMES = {
    # Add accounts used in MANUAL_OVERRIDES here.
}

# ============================================================
# EDIT BELOW: Paste raw data from browser snapshot
# ============================================================
RAW_DATA = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# ============================================================
MANUAL_OVERRIDES = {
}


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        if 'ご利用分' in line or '＜お支払金額総合計＞' in line:
            continue

        # Confirmed format: starts with \tYY/MM/DD
        # Unconfirmed format: starts with YY/MM/DD
        m = re.match(r'\t?(\d{2}/\d{2}/\d{2})\t', line)
        if not m:
            continue

        fields = line.lstrip('\t').split('\t')
        date = datetime.strptime(fields[0], '%y/%m/%d')

        if line.startswith('\t'):
            # Confirmed: date, merchant, amount, pay_type, installment, pay_amount, ...
            merchant = fields[1]
            amount = -int(fields[2].replace(',', ''))
        else:
            # Unconfirmed: date, merchant, card_holder, pay_type, installment_count, pay_month, amount, ...
            merchant = fields[1]
            amount = -int(fields[6].replace(',', ''))

        transactions.append({'date': date, 'merchant': merchant, 'amount': amount})
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    raise NotImplementedError(f"No mapping for ID {idx}: {tx['merchant']} ¥{abs(tx['amount']):,}")


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Merchant':<20} {'Desc':<30} {'Transfer':<45} {'Amount':>10}")
    print("-" * 130)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 130)
        prev_date = date_str

        try:
            expense_account, description = get_transaction_info(idx, tx)
            transfer = ACCOUNT_NAMES.get(expense_account, expense_account or '')
        except NotImplementedError:
            description = '???'
            transfer = '???'

        amt_str = f"¥{abs(tx['amount']):,}"
        print(f"{idx:<4} {date_str:<14} {tx['merchant']:<20} {description or '':<30} {transfer:<45} {amt_str:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        expense_account, description = get_transaction_info(idx, tx)

        currency_guid = CURRENCIES['JPY']
        value_num = tx['amount']

        tx_guid = uuid.uuid4().hex
        split1_guid = uuid.uuid4().hex
        split2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description.replace(chr(39), chr(39)*2)}'" if description else 'NULL'

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{currency_guid}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'c', NULL, {value_num}, 1, {value_num}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{expense_account}', '', '', 'c', NULL, {-value_num}, 1, {-value_num}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 gold_point_card_plus_import.py [review|sql]", file=sys.stderr)
        sys.exit(1)

    if not RAW_DATA.strip():
        print("Error: RAW_DATA is empty.", file=sys.stderr)
        sys.exit(1)

    transactions = parse_transactions(RAW_DATA)

    if sys.argv[1] == 'review':
        output_review(transactions)
    else:
        output_sql(transactions)


if __name__ == '__main__':
    main()
