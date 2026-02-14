#!/usr/bin/env python3
"""
ANA Mileage Club Statement Importer

Usage:
1. Copy raw data into RAW_DATA (tab-separated: date, description, amount, account)
2. Run: python3 scripts/ana_mileage_club_import.py review    # Review transactions
3. Run: python3 scripts/ana_mileage_club_import.py sql       # Generate SQL
"""
import json
import uuid
import sys
from datetime import datetime
from pathlib import Path

# Load accounts from JSON
ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-uuid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

SOURCE_ACCOUNT = get_guid('Assets:JPY - Current Assets:Reward Programs:ANA Mileage Club')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

# ============================================================
# EDIT BELOW: Paste raw data (tab-separated)
# Format: date\tdescription\tamount\taccount
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
    """Parse RAW_DATA into list of transaction dicts."""
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 4:
            continue
        date_str, desc, amount_str, account = parts[:4]
        transactions.append({
            'date': datetime.strptime(date_str, '%Y/%m/%d'),
            'desc': desc,
            'amount': int(amount_str.replace(',', '').replace('+', '')),
            'account': account,
        })
    transactions.sort(key=lambda x: x['date'], reverse=True)
    return transactions


def get_transaction_info(idx, tx):
    """Return (account_guid, description) for a transaction."""
    if idx in MANUAL_OVERRIDES:
        guid, desc = MANUAL_OVERRIDES[idx]
        return guid, desc if desc is not None else tx['desc']
    return get_guid(tx['account']), tx['desc']


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Desc':<30} {'Transfer':<50} {'Increase':>10} {'Decrease':>10}")
    print("-" * 125)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 125)
        prev_date = date_str

        _, description = get_transaction_info(idx, tx)
        increase = f"{tx['amount']:,}" if tx['amount'] > 0 else ""
        decrease = f"{abs(tx['amount']):,}" if tx['amount'] < 0 else ""

        print(f"{idx:<4} {date_str:<14} {description or '':<30} {tx['account']:<50} {increase:>10} {decrease:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        expense_account, description = get_transaction_info(idx, tx)

        tx_guid = uuid.uuid4().hex
        split1_guid = uuid.uuid4().hex
        split2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"-- Transaction {idx}: {tx['date'].strftime('%Y-%m-%d')} {description or '(no desc)'} {tx['amount']:+,}")
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{expense_account}', '', '', 'n', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 ana_mileage_club_import.py [review|sql]", file=sys.stderr)
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
