#!/usr/bin/env python3
"""
Bic Point Statement Importer

Usage:
1. Copy raw data into RAW_DATA (tab-separated: date, type, description, points, account)
2. Run: python3 scripts/bic_point_import.py review    # Review transactions
3. Run: python3 scripts/bic_point_import.py sql       # Generate SQL
"""
import json
import uuid
import sys
from datetime import datetime
from pathlib import Path

# Load accounts from JSON
ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-guid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

SOURCE_ACCOUNT = get_guid('Assets:JPY - Current Assets:Reward Programs:Bic Point')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

# ============================================================
# EDIT BELOW: Paste raw data (tab-separated)
# Format: date\ttype\tdescription\tpoints\taccount
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
    """Parse RAW_DATA into list of transactions."""
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 5:
            continue
        date_str, tx_type, desc, points_str, account = parts[:5]
        date = datetime.strptime(date_str, '%Y/%m/%d')
        points = int(points_str.replace(',', '').replace('+', ''))
        transactions.append({
            'date': date,
            'type': tx_type,
            'desc': desc,
            'points': points,
            'account': account,
        })
    transactions.sort(key=lambda x: x['date'], reverse=True)
    return transactions


def get_transaction_info(idx, tx):
    """Return (account_guid, description) for a transaction."""
    if idx in MANUAL_OVERRIDES:
        guid, desc = MANUAL_OVERRIDES[idx]
        return get_guid(guid) if not guid.startswith('{') and len(guid) != 32 else guid, desc
    return get_guid(tx['account']), 'Bic Camera'


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Type':<5} {'Desc':<50} {'Transfer':<45} {'Increase':>10} {'Decrease':>10}")
    print("-" * 140)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = tx['date'].strftime('%Y-%m-%d')
        date_display = f"{date_str} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 140)
        prev_date = date_str

        account_guid, _ = get_transaction_info(idx, tx)
        transfer = tx['account']
        increase = f"{tx['points']:,}" if tx['points'] > 0 else ""
        decrease = f"{abs(tx['points']):,}" if tx['points'] < 0 else ""

        print(f"{idx:<4} {date_display:<14} {tx['type']:<5} {tx['desc']:<50} {transfer:<45} {increase:>10} {decrease:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total_count = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account_guid, description = get_transaction_info(idx, tx)

        tx_guid = uuid.uuid4().hex
        split1_guid = uuid.uuid4().hex
        split2_guid = uuid.uuid4().hex
        reverse_idx = total_count - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"-- Transaction {idx}: {tx['date'].strftime('%Y-%m-%d')} {description} {tx['points']:+,}")
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {tx['points']}, 1, {tx['points']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{account_guid}', '', '', 'n', NULL, {-tx['points']}, 1, {-tx['points']}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 bic_point_import.py [review|sql]", file=sys.stderr)
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
