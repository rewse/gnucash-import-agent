#!/usr/bin/env python3
"""JRE Bank Statement Importer

Usage:
1. Copy raw data from browser eval into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/jre_bank_import_YYYYMMDD.py review
4. Run: python3 tmp/jre_bank_import_YYYYMMDD.py sql
"""
import json
import re
import sys
import uuid
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-uuid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}


def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)


SOURCE_ACCOUNT = get_guid('Assets:JPY - Current Assets:Banks:JRE Bank')
LUMINE_CARD = get_guid('Liabilities:Credit Card:LUMINE CARD')
SALARY = get_guid('Income:Salary')
NEOBANK = get_guid('Assets:JPY - Current Assets:Banks:d NEOBANK')
INTEREST = get_guid('Income:Interest Income')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    LUMINE_CARD: 'Liabilities:Credit Card:LUMINE CARD',
    SALARY: 'Income:Salary',
    NEOBANK: 'Assets:Banks:d NEOBANK',
    INTEREST: 'Income:Interest Income',
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


def parse_transactions(raw_data):
    transactions = []
    year = None
    lines = raw_data.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Year-month header
        m = re.match(r'(\d{4})年\d{2}月', line)
        if m:
            year = int(m.group(1))
            i += 1
            continue
        # Transaction date
        m = re.match(r'(\d{2})/(\d{2})$', line)
        if m and year and i + 3 < len(lines):
            month, day = int(m.group(1)), int(m.group(2))
            amount = int(lines[i + 1].strip().replace(',', ''))
            # Skip balance line (i + 2)
            desc = lines[i + 3].strip()
            transactions.append({
                'date': f'{year}-{month:02d}-{day:02d}',
                'amount': amount,
                'desc': desc,
            })
            i += 4
            continue
        i += 1
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    desc = tx['desc']
    if 'ヒ゛ユ－カ－ト゛' in desc:
        return LUMINE_CARD, None
    if desc.startswith('給与'):
        return SALARY, None
    if '住信ＳＢＩ' in desc:
        return NEOBANK, None
    if desc == '預金利息':
        return INTEREST, None
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
        from datetime import date
        d = date.fromisoformat(tx['date'])
        date_str = f"{tx['date']} {weekday[d.weekday()]}"
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
        print('Usage: python3 jre_bank_import.py [review|sql]', file=sys.stderr)
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
