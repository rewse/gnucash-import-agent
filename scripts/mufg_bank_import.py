#!/usr/bin/env python3
"""MUFG Bank Statement Importer

Usage:
1. Copy raw data from browser eval into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/mufg_bank_import_YYYYMMDD.py review
4. Run: python3 tmp/mufg_bank_import_YYYYMMDD.py sql
"""
import json
import re
import sys
import uuid
from datetime import date
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-uuid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}


def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)


SOURCE_ACCOUNT = get_guid('Assets:JPY - Current Assets:Banks:MUFG Bank')
INTEREST = get_guid('Income:Interest Income')
PROPERTY_INS = get_guid('Expenses:Insurances:Property Insurances')
NEOBANK = get_guid('Assets:JPY - Current Assets:Banks:d NEOBANK')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    INTEREST: 'Income:Interest Income',
    PROPERTY_INS: 'Expenses:Insurances:Property Insurances',
    NEOBANK: 'Assets:Banks:d NEOBANK',
}

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


def parse_amount(s):
    """Parse amount string like '129,052 円' to int."""
    s = s.strip()
    if not s:
        return 0
    return int(re.sub(r'[,\s円]', '', s))


def parse_transactions(raw_data):
    transactions = []
    year = None
    for line in raw_data.strip().split('\n'):
        line = line.rstrip()
        if not line or line == 'メモ内容':
            continue
        m = re.match(r'(\d{4})年', line)
        if m:
            year = int(m.group(1))
            continue
        m = re.match(r'(\d{1,2})/(\d{1,2})\t', line)
        if m and year:
            parts = line.split('\t')
            month, day = int(m.group(1)), int(m.group(2))
            withdrawal = parse_amount(parts[1]) if len(parts) > 1 else 0
            deposit = parse_amount(parts[2]) if len(parts) > 2 else 0
            desc = parts[3].strip() if len(parts) > 3 else ''
            amount = deposit - withdrawal
            transactions.append({
                'date': date(year, month, day),
                'amount': amount,
                'desc': desc,
            })
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    desc = tx['desc']
    if '利息' in desc:
        return INTEREST, None
    if 'メイジヤスダセイメイ' in desc:
        return PROPERTY_INS, None
    if 'ラクテンソンガイホケン' in desc:
        return PROPERTY_INS, None
    if ('振込' in desc or 'ことら送金' in desc) and 'シバタ' in desc:
        return NEOBANK, None
    raise ValueError(f"Unknown transaction type at ID {idx}: {desc}")


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Desc':<55} {'Transfer':<40} {'Increase':>10} {'Decrease':>10}")
    print('-' * 136)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if prev_date and prev_date != tx['date']:
            print('-' * 136)
        prev_date = tx['date']
        account, description = get_transaction_info(idx, tx)
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        date_str = f"{tx['date']} {weekday[tx['date'].weekday()]}"
        transfer = ACCOUNT_NAMES.get(account, account or '')
        inc = f"¥{tx['amount']:,}" if tx['amount'] > 0 else ''
        dec = f"¥{abs(tx['amount']):,}" if tx['amount'] < 0 else ''
        print(f"{idx:<4} {date_str:<14} {tx['desc']:<55} {transfer:<40} {inc:>10} {dec:>10}")


def output_sql(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account, description = get_transaction_info(idx, tx)
        tx_guid = uuid.uuid4().hex
        s1_guid = uuid.uuid4().hex
        s2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date']} 00:{minutes:02d}:{seconds:02d}"
        desc_sql = f"'{description}'" if description else 'NULL'
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s1_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s2_guid}', '{tx_guid}', '{account}', '', '', 'n', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);")
        print()
    print('COMMIT;')


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('review', 'sql'):
        print('Usage: python3 mufg_bank_import.py [review|sql]', file=sys.stderr)
        sys.exit(1)
    if not RAW_DATA.strip():
        print('Error: RAW_DATA is empty.', file=sys.stderr)
        sys.exit(1)
    transactions = parse_transactions(RAW_DATA)
    if sys.argv[1] == 'review':
        output_review(transactions)
    else:
        output_sql(transactions)


if __name__ == '__main__':
    main()
