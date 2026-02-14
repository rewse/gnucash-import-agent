#!/usr/bin/env python3
"""
Rakuten Super Point Statement Importer

Usage:
1. Copy raw data into RAW_DATA (tab-separated: date, service, detail, type, points, desc)
2. Run: python3 scripts/rakuten_super_point_import.py review    # Review transactions
3. Run: python3 scripts/rakuten_super_point_import.py sql       # Generate SQL
"""
import json
import uuid
import sys
from datetime import datetime
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-guid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

SOURCE_ACCOUNT = get_guid('Assets:JPY - Current Assets:Reward Programs:Rakuten Super Point')
RAKUTEN_CASH = get_guid('Assets:JPY - Current Assets:Prepaid:Rakuten Cash')
POINT_CHARGE = get_guid('Income:Point Charge')
BOOKS = get_guid('Expenses:Entertainment:Books')
PART_TIME = get_guid('Income:Part-Time')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    POINT_CHARGE: 'Income:Point Charge',
    BOOKS: 'Expenses:Entertainment:Books',
    RAKUTEN_CASH: 'Assets:JPY - Current Assets:Prepaid:Rakuten Cash',
    PART_TIME: 'Income:Part-Time',
}

# ============================================================
# EDIT BELOW: Paste raw data (tab-separated)
# Format: date\tservice\tdetail\ttype\tpoints\tdesc
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
        if len(parts) < 6:
            continue
        date_str, service, detail, tx_type, points_str, desc = parts[:6]
        date = datetime.strptime(date_str, '%Y/%m/%d')
        points = int(points_str.replace(',', ''))
        transactions.append({
            'date': date,
            'service': service,
            'detail': detail,
            'type': tx_type,
            'points': points,
            'desc': desc,
        })
    transactions.sort(key=lambda x: x['date'], reverse=True)
    return transactions


def get_transaction_info(idx, tx):
    """Return (source_account, transfer_account, description, signed_amount)."""
    if idx in MANUAL_OVERRIDES:
        guid, desc = MANUAL_OVERRIDES[idx]
        guid = get_guid(guid) if len(guid) != 32 else guid
        if tx['type'] == 'チャージ':
            return RAKUTEN_CASH, guid, desc or tx['desc'], tx['points']
        elif tx['type'] == '利用':
            return SOURCE_ACCOUNT, guid, desc or tx['desc'], -tx['points']
        else:
            return SOURCE_ACCOUNT, guid, desc or tx['desc'], tx['points']

    if tx['type'] == 'チャージ':
        return RAKUTEN_CASH, PART_TIME, tx['desc'], tx['points']

    if tx['type'] == '利用':
        if '楽天マガジン' in tx['service']:
            return SOURCE_ACCOUNT, BOOKS, tx['desc'], -tx['points']
        raise ValueError(f"Unknown use transaction at ID {idx}: {tx['service']} / {tx['detail']} — add to MANUAL_OVERRIDES")

    # 獲得
    return SOURCE_ACCOUNT, POINT_CHARGE, tx['desc'], tx['points']


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Service':<16} {'Desc':<25} {'Transfer':<45} {'Increase':>10} {'Decrease':>10}")
    print("-" * 130)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = tx['date'].strftime('%Y-%m-%d')
        date_display = f"{date_str} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 130)
        prev_date = date_str

        try:
            source, transfer_guid, description, amount = get_transaction_info(idx, tx)
            transfer = ACCOUNT_NAMES.get(transfer_guid, '???')
        except ValueError:
            description = '???'
            transfer = '??? (needs MANUAL_OVERRIDES)'
            amount = -tx['points'] if tx['type'] == '利用' else tx['points']

        increase = f"{amount:,}" if amount > 0 else ""
        decrease = f"{abs(amount):,}" if amount < 0 else ""

        print(f"{idx:<4} {date_display:<14} {tx['service']:<16} {str(description or ''):<25} {transfer:<45} {increase:>10} {decrease:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        source, transfer_guid, description, amount = get_transaction_info(idx, tx)

        tx_guid = uuid.uuid4().hex
        split1_guid = uuid.uuid4().hex
        split2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"-- Transaction {idx}: {tx['date'].strftime('%Y-%m-%d')} {description} {amount:+,}")
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{source}', '', '', 'n', NULL, {amount}, 1, {amount}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{transfer_guid}', '', '', 'n', NULL, {-amount}, 1, {-amount}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 rakuten_super_point_import.py [review|sql]", file=sys.stderr)
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
