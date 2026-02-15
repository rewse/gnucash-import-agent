#!/usr/bin/env python3
"""PayPay Card JCB Statement Importer

Usage:
1. Copy raw data from browser snapshot into RAW_DATA (tab-separated: merchant, date, amount)
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/paypay_card_jcb_import_YYYYMMDD.py review
4. Run: python3 tmp/paypay_card_jcb_import_YYYYMMDD.py sql
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


SOURCE_ACCOUNT = get_guid('Liabilities:Credit Card:PayPay Card JCB')
PAYPAY = get_guid('Assets:JPY - Current Assets:Prepaid:PayPay')
DINING = get_guid('Expenses:Foods:Dining')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    PAYPAY: 'Assets:Prepaid:PayPay',
    DINING: 'Expenses:Foods:Dining',
}

# ============================================================
# EDIT BELOW: Paste raw data (tab-separated: merchant, date, amount)
# ============================================================
RAW_DATA = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Simple: ID: (ACCOUNT_GUID, 'Description')
# Split:  ID: [(ACCOUNT_GUID, amount, 'Description'), ...]
# ============================================================
MANUAL_OVERRIDES = {
}


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) == 3:
            merchant, date_str, amount_str = parts
        else:
            # Fallback: parse "merchant YYYY年M月D日 amount円" format
            m = re.match(r'(.+?)\s+(\d{4}年\d{1,2}月\d{1,2}日)\s+([\d,]+)円?$', line)
            if not m:
                continue
            merchant, date_str, amount_str = m.group(1), m.group(2), m.group(3)
        dm = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if not dm:
            continue
        transactions.append({
            'date': date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3))),
            'amount': -int(amount_str.replace(',', '')),
            'merchant': merchant.strip(),
        })
    return transactions


def get_transaction_info(idx, tx):
    """Return (account_guid, description) or list of (account_guid, amount, description) for splits."""
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    m = tx['merchant']
    if m == 'チャージ':
        return PAYPAY, None
    if 'ヤフージャパン' in m or 'Yahoo' in m:
        raise ValueError(f"ID {idx}: Yahoo! transaction requires split amounts (ask user)")
    if '請求書払い' in m:
        raise ValueError(f"ID {idx}: Invoice payment requires account and description (ask user)")
    # Check for dining patterns
    dining_keywords = ['オリジン', 'キッチンオリジン', 'マーラータン', 'セブン', 'ファミリーマート', 'ローソン', 
                      'マクドナルド', 'すき家', '吉野家', '松屋', 'ガスト', 'サイゼリヤ', 'RESTAURANT']
    if any(k in m for k in dining_keywords):
        return DINING, m
    raise ValueError(f"Unknown transaction at ID {idx}: {m} (check past GnuCash transactions or ask user)")


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Merchant':<30} {'Desc':<25} {'Transfer':<40} {'Amount':>10}")
    print('-' * 127)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if prev_date and prev_date != tx['date']:
            print('-' * 127)
        prev_date = tx['date']
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        date_str = f"{tx['date']} {weekday[tx['date'].weekday()]}"
        try:
            info = get_transaction_info(idx, tx)
            if isinstance(info, list):
                # Split transaction
                for i, (acct, amt, desc) in enumerate(info):
                    transfer = ACCOUNT_NAMES.get(acct, acct or '')
                    prefix = tx['merchant'][:28] if i == 0 else ''
                    desc_display = desc or ''
                    print(f"{idx if i == 0 else '':<4} {date_str if i == 0 else '':<14} {prefix:<30} {desc_display:<25} {transfer:<40} {f'¥{abs(amt):,}':>10}")
            else:
                account, description = info
                transfer = ACCOUNT_NAMES.get(account, account or '')
                print(f"{idx:<4} {date_str:<14} {tx['merchant'][:28]:<30} {description or '':<25} {transfer:<40} {f'¥{abs(tx['amount']):,}':>10}")
        except ValueError as e:
            print(f"{idx:<4} {date_str:<14} {tx['merchant'][:28]:<30} {'ERROR':<25} {str(e):<40} {f'¥{abs(tx['amount']):,}':>10}")


def output_sql(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        info = get_transaction_info(idx, tx)
        tx_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date']} 00:{minutes:02d}:{seconds:02d}"

        if isinstance(info, list):
            # Split transaction: one debit from credit card, multiple credits
            description = info[0][2] if info[0][2] else ''
            desc_sql = f"'{description}'" if description else 'NULL'
            print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
            print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
            s_guid = uuid.uuid4().hex
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
            for acct, amt, _ in info:
                s_guid = uuid.uuid4().hex
                print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
                print(f"VALUES ('{s_guid}', '{tx_guid}', '{acct}', '', '', 'n', NULL, {amt}, 1, {amt}, 1, NULL);")
        else:
            account, description = info
            desc_sql = f"'{description}'" if description else 'NULL'
            s1_guid = uuid.uuid4().hex
            s2_guid = uuid.uuid4().hex
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
        print('Usage: python3 paypay_card_jcb_import.py [review|sql]', file=sys.stderr)
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
