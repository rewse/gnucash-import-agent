#!/usr/bin/env python3
"""Sony Bank Statement Importer

Usage:
1. Download CSV from Sony Bank, convert: iconv -f SHIFT_JIS -t UTF-8 FutsuRireki.csv
2. Paste converted CSV rows (without header) into RAW_DATA
3. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
4. Run: python3 tmp/sony_bank_import_YYYYMMDD.py review
5. Run: python3 tmp/sony_bank_import_YYYYMMDD.py sql
6. Repeat for each currency (JPY, USD) separately
"""
import csv
import io
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


SOURCE_ACCOUNTS = {
    'JPY': get_guid('Assets:JPY - Current Assets:Banks:Sony Bank'),
    'USD': get_guid('Assets:USD - Current Assets:Banks:Sony Bank'),
}
INTEREST = get_guid('Income:Interest Income')
CASHBACK = get_guid('Income:Cash Back')
MUFG = get_guid('Assets:JPY - Current Assets:Banks:MUFG Bank')
SONY_JPY = SOURCE_ACCOUNTS['JPY']
SONY_USD = SOURCE_ACCOUNTS['USD']

CURRENCIES = {
    'JPY': 'a77d4ee821e04f02bb7429e437c645e4',
    'USD': '327c5a1bcfb147ceba2370ee17093159',
}
CURRENCY_DENOM = {'JPY': 1, 'USD': 100}

ACCOUNT_NAMES = {
    INTEREST: 'Income:Interest Income',
    CASHBACK: 'Income:Cash Back',
    MUFG: 'Assets:Banks:MUFG Bank',
    SONY_JPY: 'Assets:Banks:Sony Bank (JPY)',
    SONY_USD: 'Assets:Banks:Sony Bank (USD)',
}

# ============================================================
# EDIT BELOW: Paste UTF-8 converted CSV rows (without header)
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
    s = s.strip()
    return float(s) if s else 0.0


def parse_transactions(raw_data):
    transactions = []
    reader = csv.reader(io.StringIO(raw_data.strip()))
    for row in reader:
        if not row or row[0] == '取引日':
            continue
        m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', row[0])
        if not m:
            continue
        currency = row[3].strip()
        deposit = parse_amount(row[4])
        withdrawal = parse_amount(row[5])
        amount = deposit - withdrawal
        transactions.append({
            'date': date(int(m.group(1)), int(m.group(2)), int(m.group(3))),
            'desc': row[1].strip(),
            'currency': currency,
            'amount': amount,
        })
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    desc = tx['desc']
    currency = tx['currency']

    if '利息' in desc:
        return INTEREST, None

    if currency == 'JPY':
        if '振込' in desc and 'シバタ' in desc:
            return MUFG, None
        if '外貨普通預金' in desc and '米ドル' in desc:
            return SONY_USD, None
        if 'キヤツシユバツク' in desc:
            return CASHBACK, None

    if currency == 'USD':
        if '円普通預金' in desc:
            return SONY_JPY, None

    raise ValueError(f"Unknown transaction type at ID {idx}: {desc}")


def output_review(transactions):
    currency = transactions[0]['currency'] if transactions else 'JPY'
    sym = '$' if currency == 'USD' else '¥'
    print(f"{'ID':<4} {'Date':<14} {'Desc':<55} {'Transfer':<40} {'Increase':>12} {'Decrease':>12}")
    print('-' * 140)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if prev_date and prev_date != tx['date']:
            print('-' * 140)
        prev_date = tx['date']
        account, description = get_transaction_info(idx, tx)
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        date_str = f"{tx['date']} {weekday[tx['date'].weekday()]}"
        transfer = ACCOUNT_NAMES.get(account, account or '')
        if currency == 'USD':
            inc = f"${tx['amount']:,.2f}" if tx['amount'] > 0 else ''
            dec = f"${abs(tx['amount']):,.2f}" if tx['amount'] < 0 else ''
        else:
            inc = f"¥{int(tx['amount']):,}" if tx['amount'] > 0 else ''
            dec = f"¥{int(abs(tx['amount'])):,}" if tx['amount'] < 0 else ''
        print(f"{idx:<4} {date_str:<14} {tx['desc']:<55} {transfer:<40} {inc:>12} {dec:>12}")


def output_sql(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account, description = get_transaction_info(idx, tx)
        currency = tx['currency']
        currency_guid = CURRENCIES[currency]
        denom = CURRENCY_DENOM[currency]
        source = SOURCE_ACCOUNTS[currency]
        value_num = round(tx['amount'] * denom)

        tx_guid = uuid.uuid4().hex
        s1_guid = uuid.uuid4().hex
        s2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date']} 00:{minutes:02d}:{seconds:02d}"
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{currency_guid}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s1_guid}', '{tx_guid}', '{source}', '', '', 'n', NULL, {value_num}, {denom}, {value_num}, {denom}, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s2_guid}', '{tx_guid}', '{account}', '', '', 'n', NULL, {-value_num}, {denom}, {-value_num}, {denom}, NULL);")
        print()
    print('COMMIT;')


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('review', 'sql'):
        print('Usage: python3 sony_bank_import.py [review|sql]', file=sys.stderr)
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
