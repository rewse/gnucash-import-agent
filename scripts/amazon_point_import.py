#!/usr/bin/env python3
"""
Amazon Point Statement Importer

Usage:
1. Copy raw data into RAW_DATA (tab-separated: date, description, type, points, account)
2. Run: python3 scripts/amazon_point_import.py review    # Review transactions
3. Run: python3 scripts/amazon_point_import.py sql       # Generate SQL
"""
import json
import uuid
import sys
import re
from datetime import datetime
from pathlib import Path

# Load accounts from JSON
ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-uuid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

SOURCE_ACCOUNT = get_guid('Assets:JPY - Current Assets:Reward Programs:Amazon Point')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

# ============================================================
# EDIT BELOW: Paste raw data (tab-separated)
# Format: date\tdescription\ttype\tpoints\taccount
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
    """Parse RAW_DATA into transactions, grouping by date+description for multi-split."""
    lines = [l for l in raw_data.strip().split('\n') if l.strip()]

    groups = {}
    for line in lines:
        parts = line.split('\t')
        if len(parts) < 5:
            continue
        date_str, desc, tx_type, points_str, account = parts[:5]
        date = datetime.strptime(date_str, '%Y/%m/%d')
        points = int(points_str.replace(',', '').replace('+', ''))
        key = (date_str, desc)
        if key not in groups:
            groups[key] = []
        groups[key].append({
            'date': date,
            'desc': desc,
            'type': tx_type,
            'points': points,
            'account': account,
        })

    transactions = []
    for key, splits in sorted(groups.items(), key=lambda x: x[1][0]['date'], reverse=True):
        total = sum(s['points'] for s in splits)
        transactions.append({
            'date': splits[0]['date'],
            'desc': splits[0]['desc'],
            'type': splits[0]['type'],
            'total': total,
            'splits': splits,
        })
    return transactions


def output_review(transactions):
    print(f"{'ID':<6} {'Date':<14} {'Type':<5} {'Desc':<50} {'Transfer':<45} {'Increase':>10} {'Decrease':>10}")
    print("-" * 145)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if idx in MANUAL_OVERRIDES:
            override = MANUAL_OVERRIDES[idx]
            # Apply override to first split
            tx['splits'][0]['account'] = override[0] if isinstance(override[0], str) and not override[0].startswith('{') else tx['splits'][0]['account']

        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = tx['date'].strftime('%Y-%m-%d')
        date_display = f"{date_str} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 145)
        prev_date = date_str

        if len(tx['splits']) == 1:
            split = tx['splits'][0]
            increase = f"{split['points']:,}" if split['points'] > 0 else ""
            decrease = f"{abs(split['points']):,}" if split['points'] < 0 else ""
            print(f"{idx:<6} {date_display:<14} {tx['type']:<5} {tx['desc']:<50} {split['account']:<45} {increase:>10} {decrease:>10}")
        else:
            increase = f"{tx['total']:,}" if tx['total'] > 0 else ""
            decrease = f"{abs(tx['total']):,}" if tx['total'] < 0 else ""
            print(f"{idx:<6} {date_display:<14} {tx['type']:<5} {tx['desc']:<50} {'':<45} {increase:>10} {decrease:>10}")
            for sub_idx, split in enumerate(tx['splits'], 1):
                s_inc = f"{split['points']:,}" if split['points'] > 0 else ""
                s_dec = f"{abs(split['points']):,}" if split['points'] < 0 else ""
                print(f"{idx}-{sub_idx:<4} {'':<14} {'':<5} {'':<50} {split['account']:<45} {s_inc:>10} {s_dec:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total_count = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        tx_guid = uuid.uuid4().hex
        reverse_idx = total_count - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')

        desc = 'Amazon'
        desc_sql = f"'{desc}'"

        print(f"-- Transaction {idx}: {tx['date'].strftime('%Y-%m-%d')} {desc} {tx['total']:+,}")
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")

        # Source account split (Amazon Point)
        split_guid = uuid.uuid4().hex
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {tx['total']}, 1, {tx['total']}, 1, NULL);")

        # Transfer splits
        for split in tx['splits']:
            split_guid = uuid.uuid4().hex
            account_guid = get_guid(split['account'])
            amount = -split['points']
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{split_guid}', '{tx_guid}', '{account_guid}', '', '', 'n', NULL, {amount}, 1, {amount}, 1, NULL);")

        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 amazon_point_import.py [review|sql]", file=sys.stderr)
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
