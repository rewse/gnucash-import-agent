#!/usr/bin/env python3
"""Amazon MasterCard Gold Statement Importer

Usage:
1. Copy raw data from browser eval into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/amazon_mastercard_gold_import_YYYYMMDD.py review
4. Run: python3 tmp/amazon_mastercard_gold_import_YYYYMMDD.py sql
"""
import json
import re
import sys
import uuid
from datetime import date
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-guid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}


def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)


SOURCE_ACCOUNT = get_guid('Liabilities:Credit Card:Amazon MasterCard Gold')
DINING = get_guid('Expenses:Foods:Dining')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    DINING: 'Expenses:Foods:Dining',
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


def normalize(s):
    """Convert full-width ASCII to half-width."""
    return s.translate(str.maketrans(
        'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９．＊　',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.* '))


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        line = line.rstrip()
        if not line or 'ご利用分' in line or 'お支払金額総合計' in line:
            continue
        m = re.match(r'\t?(\d{2})/(\d{2})/(\d{2})\t', line)
        if not m:
            continue
        parts = line.lstrip('\t').split('\t')
        yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year = 2000 + yy
        merchant = parts[1].strip()
        # Auto-detect format: confirmed has amount at index 2, unconfirmed at index 6
        if re.match(r'[\d,]+$', parts[2].strip()):
            amount = int(parts[2].replace(',', ''))
            remarks = ''
            if len(parts) > 7 and parts[7].strip() in ('USD', 'EUR', 'GBP', 'SGD', 'AUD', 'CAD', 'HKD', 'THB', 'TRY'):
                remarks = f"{parts[6].strip()} {parts[7].strip()}"
            elif len(parts) > 6 and parts[6].strip():
                remarks = parts[6].strip()
        else:
            amount = int(parts[6].replace(',', ''))
            remarks = ''
        transactions.append({
            'date': date(year, mm, dd),
            'amount': -amount,
            'merchant': merchant,
            'merchant_norm': normalize(merchant),
            'remarks': remarks,
            'remarks_norm': normalize(remarks),
        })
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    m = tx['merchant_norm']
    r = tx['remarks_norm']
    if 'AMZ*' in r and 'アマゾン社員食堂' in tx['remarks']:
        return DINING, 'AMZ Employee Cafe'
    if m in ('SEVEN-ELEVEN', 'セブン－イレブン'):
        return DINING, 'SEVEN-ELEVEN'
    if 'ファミリーマート' in tx['merchant']:
        return DINING, 'Family Mart'
    if 'ローソン' in tx['merchant']:
        return DINING, 'LAWSON'
    raise ValueError(f"Unknown transaction at ID {idx}: {tx['merchant']} / {tx['remarks']}")


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Merchant':<30} {'Desc':<25} {'Transfer':<35} {'Amount':>10}")
    print('-' * 122)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if prev_date and prev_date != tx['date']:
            print('-' * 122)
        prev_date = tx['date']
        account, description = get_transaction_info(idx, tx)
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        date_str = f"{tx['date']} {weekday[tx['date'].weekday()]}"
        transfer = ACCOUNT_NAMES.get(account, account or '')
        amt = f"¥{abs(tx['amount']):,}"
        merchant_display = tx['merchant_norm'][:28]
        print(f"{idx:<4} {date_str:<14} {merchant_display:<30} {description or '':<25} {transfer:<35} {amt:>10}")


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
        print('Usage: python3 amazon_mastercard_gold_import.py [review|sql]', file=sys.stderr)
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
