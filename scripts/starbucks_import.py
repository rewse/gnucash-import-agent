#!/usr/bin/env python3
"""
Starbucks Card Statement Importer

Usage:
1. Copy raw data from Starbucks browser snapshot into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/starbucks_import_20260202.py review    # Review transactions
4. Run: python3 tmp/starbucks_import_20260202.py sql       # Generate SQL
"""
import json
import uuid
import sys
import re
from datetime import datetime
from pathlib import Path

# Load accounts from JSON
ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-guid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

# Account GUIDs
STARBUCKS_ACCOUNT = get_guid('Assets:JPY - Current Assets:Prepaid:Starbucks')
DINING_ACCOUNT = get_guid('Expenses:Foods:Dining')
ANA_CARD_ACCOUNT = get_guid('Liabilities:Credit Card:ANA Super Flyers Gold Card')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    DINING_ACCOUNT: 'Expenses:Foods:Dining',
    ANA_CARD_ACCOUNT: 'Liabilities:Credit Card:ANA Super Flyers Gold Card',
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
        parts = line.split('\t')
        desc = parts[0].strip()
        amount_str = parts[1].strip().replace('¥', '').replace(',', '').replace(' ', '')
        amount = int(amount_str)
        date_str = parts[2].strip()
        date = datetime.strptime(date_str, '%Y/%m/%d')
        transactions.append({'desc': desc, 'amount': amount, 'date': date})
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    if tx['desc'] == 'オートチャージ':
        return ANA_CARD_ACCOUNT, None
    return DINING_ACCOUNT, 'Starbucks'


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<17} {'Type':<10} {'Desc':<30} {'Transfer':<45} {'Increase':>10} {'Decrease':>10}")
    print("-" * 130)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 130)
        prev_date = date_str

        expense_account, description = get_transaction_info(idx, tx)
        tx_type = 'Charge' if tx['amount'] > 0 else 'Payment'
        transfer = ACCOUNT_NAMES.get(expense_account, expense_account)
        increase = f"¥{tx['amount']:,}" if tx['amount'] > 0 else ""
        decrease = f"¥{abs(tx['amount']):,}" if tx['amount'] < 0 else ""

        print(f"{idx:<4} {date_str:<17} {tx_type:<10} {description or '':<30} {transfer:<45} {increase:>10} {decrease:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        expense_account, description = get_transaction_info(idx, tx)

        tx_guid = str(uuid.uuid4()).replace('-', '')
        split1_guid = str(uuid.uuid4()).replace('-', '')
        split2_guid = str(uuid.uuid4()).replace('-', '')
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{STARBUCKS_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{expense_account}', '', '', 'n', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 starbucks_import_20260202.py [review|sql]", file=sys.stderr)
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
