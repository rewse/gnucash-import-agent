#!/usr/bin/env python3
"""
V Point Statement Importer

Usage:
1. Copy raw data into RAW_DATA (tab-separated: date, description, points, tags)
2. Run: python3 scripts/v_point_import.py review    # Review transactions
3. Run: python3 scripts/v_point_import.py sql       # Generate SQL
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

SOURCE_REGULAR = get_guid('Assets:JPY - Current Assets:Reward Programs:V Point')
SOURCE_ANA = get_guid('Assets:JPY - Current Assets:Reward Programs:V Point - ANA Mileage Transferable Points')
INCOME_POINT_CHARGE = get_guid('Income:Point Charge')
EXPENSE_POINT_LAPSE = get_guid('Expenses:Point Lapse')
PREPAID_VPOINTPAY = get_guid('Assets:JPY - Current Assets:Prepaid:V Point Pay')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

# ============================================================
# EDIT BELOW: Paste raw data (tab-separated)
# Format: date\tdescription\tpoints\ttags
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
        if len(parts) < 3:
            continue
        date_str = parts[0]
        desc = parts[1] if parts[1] else None
        points = int(parts[2].replace(',', '').replace('+', ''))
        tags = parts[3].split(',') if len(parts) > 3 and parts[3] else []
        date = datetime.strptime(date_str, '%Y/%m/%d')
        transactions.append({
            'date': date,
            'desc': desc,
            'points': points,
            'tags': tags,
        })
    transactions.sort(key=lambda x: x['date'], reverse=True)
    return transactions


def is_store_limited(tx):
    return 'ストア限定' in tx['tags']


def get_source_account(tx):
    return SOURCE_ANA if is_store_limited(tx) else SOURCE_REGULAR


def get_transaction_info(idx, tx):
    """Return (transfer_account_guid, description) for a transaction."""
    if idx in MANUAL_OVERRIDES:
        guid, desc = MANUAL_OVERRIDES[idx]
        return get_guid(guid) if len(guid) != 32 else guid, desc
    if '失効' in tx['tags']:
        return EXPENSE_POINT_LAPSE, None
    if tx['points'] >= 0:
        return INCOME_POINT_CHARGE, tx['desc']
    # Negative points without 失効: check for VポイントPay pattern
    if tx['desc'] is None:
        return PREPAID_VPOINTPAY, None
    return None, tx['desc']


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Desc':<35} {'Account':<20} {'Transfer':<35} {'Increase':>10} {'Decrease':>10}")
    print("-" * 130)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = tx['date'].strftime('%Y-%m-%d')
        date_display = f"{date_str} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 130)
        prev_date = date_str

        source = 'ANA Transferable' if is_store_limited(tx) else 'V Point'
        transfer_guid, desc = get_transaction_info(idx, tx)
        transfer = next((k for k, v in ACCOUNTS.items() if v == transfer_guid), transfer_guid or '???')
        increase = f"{tx['points']:,}" if tx['points'] > 0 else ""
        decrease = f"{abs(tx['points']):,}" if tx['points'] < 0 else ""

        print(f"{idx:<4} {date_display:<14} {(desc or ''):<35} {source:<20} {transfer:<35} {increase:>10} {decrease:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total_count = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        transfer_guid, description = get_transaction_info(idx, tx)
        if not transfer_guid:
            print(f"-- ERROR: No account for transaction {idx}: {tx['desc']} {tx['points']:+,}", file=sys.stderr)
            sys.exit(1)

        source_guid = get_source_account(tx)
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
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{source_guid}', '', '', 'n', NULL, {tx['points']}, 1, {tx['points']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{transfer_guid}', '', '', 'n', NULL, {-tx['points']}, 1, {-tx['points']}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 v_point_import.py [review|sql]", file=sys.stderr)
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
