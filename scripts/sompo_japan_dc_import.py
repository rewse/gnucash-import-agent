#!/usr/bin/env python3
"""Sompo Japan DC Securities Statement Importer

Usage:
1. Copy raw data from browser eval into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/sompo_japan_dc_import_YYYYMMDD.py review    # Review transactions
4. Run: python3 tmp/sompo_japan_dc_import_YYYYMMDD.py sql       # Generate SQL
"""
import json
import uuid
import sys
import re
from datetime import datetime
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-guid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

DC = 'Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities'
SOURCE_ACCOUNT = get_guid(DC)

FUND_MAP = {
    'ＤＩＡＭ国内株式インデックス': f'{DC}:DIAM Japan Stock Index Fund <DC Pension>',
    'インデックス海外株式ヘッジなし': f'{DC}:Index Fund Global Stock NoHedge (DC)',
}

CURRENCIES = {'JPY': 'a77d4ee821e04f02bb7429e437c645e4'}
CURRENCY_DENOM = {'JPY': 1}

ACCOUNT_NAMES = {get_guid(v): v.split(':')[-1] for v in FUND_MAP.values()}
ACCOUNT_NAMES[SOURCE_ACCOUNT] = 'Sompo Japan DC Securities'

# ============================================================
# EDIT BELOW: Paste raw data from browser eval
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
        if not re.match(r'\d{4}/\d{2}/\d{2}\t', line):
            continue
        parts = line.split('\t')
        if len(parts) < 7:
            continue
        trade_date, settle_date, fund_name, qty, unit_price, amount, tx_type = parts[:7]
        transactions.append({
            'date': datetime.strptime(settle_date, '%Y/%m/%d').date(),
            'trade_date': datetime.strptime(trade_date, '%Y/%m/%d').date(),
            'fund_name': fund_name.strip(),
            'quantity': int(qty.replace(',', '')),
            'unit_price': float(unit_price.replace(',', '')),
            'amount': int(amount.replace(',', '')),
            'tx_type': tx_type.strip(),
        })
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    for key, path in FUND_MAP.items():
        if key in tx['fund_name']:
            return get_guid(path), None
    raise ValueError(f"Unknown fund: {tx['fund_name']}")


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Fund':<30} {'Qty':>8} {'Price':>10} {'Amount':>10} {'Fund Account':<40}")
    print("-" * 120)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"
        if prev_date and prev_date != date_str:
            print("-" * 120)
        prev_date = date_str
        fund_account, _ = get_transaction_info(idx, tx)
        transfer = ACCOUNT_NAMES.get(fund_account, fund_account or '')
        amt = f"¥{tx['amount']:,}"
        print(f"{idx:<4} {date_str:<14} {tx['fund_name'][:30]:<30} {tx['quantity']:>8} {tx['unit_price']:>10.4f} {amt:>10} {transfer:<40}")


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
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description}'" if description else 'NULL'
        amount = tx['amount']

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{CURRENCIES['JPY']}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{fund_account}', '', '', 'n', NULL, {amount}, 1, {amount}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {-amount}, 1, {-amount}, 1, NULL);")
        print()
    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 sompo_japan_dc_import.py [review|sql]", file=sys.stderr)
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
