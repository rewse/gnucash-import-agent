#!/usr/bin/env python3
"""
LUMINE CARD Statement Importer

Usage:
1. Copy raw data from CSV (confirmed) or browser eval (unconfirmed) into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/lumine_card_import_YYYYMMDD.py review    # Review transactions
4. Run: python3 tmp/lumine_card_import_YYYYMMDD.py sql       # Generate SQL
"""
import csv
import io
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-guid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

SOURCE_ACCOUNT = get_guid('Liabilities:Credit Card:LUMINE CARD')
SUICA_ACCOUNT = get_guid('Assets:JPY - Current Assets:Prepaid:Suica iPhone')

CURRENCIES = {'JPY': 'a77d4ee821e04f02bb7429e437c645e4'}

ACCOUNT_NAMES = {
    SUICA_ACCOUNT: 'Suica iPhone',
}

# ============================================================
# EDIT BELOW: Paste raw data (CSV confirmed or eval unconfirmed)
# ============================================================
RAW_DATA = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# ============================================================
MANUAL_OVERRIDES = {
}


def parse_confirmed(raw_data):
    """Parse confirmed CSV format."""
    transactions = []
    reader = csv.reader(io.StringIO(raw_data))
    for row in reader:
        if not row or not re.match(r'\d{4}/\d{2}/\d{2}', row[0]):
            continue
        date = datetime.strptime(row[0], '%Y/%m/%d')
        merchant = row[1].strip()
        # Use billed amount (index 4), not usage amount (index 2)
        amount_str = row[4].replace(',', '').replace('"', '').strip()
        if not amount_str:
            continue
        amount = -int(amount_str)
        transactions.append({'date': date, 'merchant': merchant, 'amount': amount})
    return transactions


def parse_unconfirmed(raw_data):
    """Parse unconfirmed HTML table eval format."""
    transactions = []
    # Normalize: replace literal \n and \t
    text = raw_data.replace('\\n', '\n').replace('\\t', '\t')
    lines = text.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Look for year line (4 digits)
        if re.match(r'^\d{4}$', line) and i + 1 < len(lines):
            year = line
            next_line = lines[i + 1]
            parts = next_line.split('\t')
            if parts and re.match(r'\d{2}/\d{2}', parts[0]):
                date = datetime.strptime(f'{year}/{parts[0]}', '%Y/%m/%d')
                # Find merchant - skip card number fields
                merchant = None
                amount_field = None
                for p in parts[1:]:
                    p = p.strip()
                    if re.match(r'\*{4}-', p):
                        continue
                    if merchant is None and p and not re.match(r'^[\d,]+$', p):
                        merchant = p
                    elif merchant and re.match(r'^[\d,]+', p):
                        amount_field = p
                        break

                if amount_field:
                    # Extract discounted amount from parentheses if present
                    m = re.search(r'\(([0-9,]+)\)', amount_field)
                    if m:
                        amount = -int(m.group(1).replace(',', ''))
                    else:
                        amount = -int(amount_field.replace(',', ''))
                    transactions.append({'date': date, 'merchant': merchant or '', 'amount': amount})
                i += 2
                continue
        i += 1
    return transactions


def parse_transactions(raw_data):
    """Auto-detect format and parse."""
    stripped = raw_data.strip()
    if re.search(r'^\d{4}/\d{2}/\d{2},', stripped, re.MULTILINE):
        return parse_confirmed(stripped)
    return parse_unconfirmed(stripped)


def get_transaction_info(idx, tx):
    """Return (account_guid, description) for a transaction."""
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    merchant = tx['merchant']
    if 'オートチャージ' in merchant:
        return SUICA_ACCOUNT, 'Auto-charge (Mobile Suica)'
    raise NotImplementedError(f'ID {idx}: Unknown merchant "{merchant}" — add to MANUAL_OVERRIDES')


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Merchant':<35} {'Desc':<30} {'Transfer':<25} {'Amount':>10}")
    print("-" * 125)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 125)
        prev_date = date_str

        try:
            account, description = get_transaction_info(idx, tx)
        except NotImplementedError:
            account, description = None, '???'
        transfer = ACCOUNT_NAMES.get(account, account or '???')

        amt = f'¥{abs(tx["amount"]):,}'
        print(f"{idx:<4} {date_str:<14} {tx['merchant']:<35} {description or '':<30} {transfer:<25} {amt:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account, description = get_transaction_info(idx, tx)
        value_num = tx['amount']
        tx_guid = uuid.uuid4().hex
        split1_guid = uuid.uuid4().hex
        split2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{CURRENCIES['JPY']}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {value_num}, 1, {value_num}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{account}', '', '', 'n', NULL, {-value_num}, 1, {-value_num}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 lumine_card_import.py [review|sql]", file=sys.stderr)
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
