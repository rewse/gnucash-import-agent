#!/usr/bin/env python3
"""
Revolut Statement Importer

Usage:
1. Copy raw data from browser snapshot into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 scripts/revolut_import.py review    # Review transactions
4. Run: python3 scripts/revolut_import.py sql       # Generate SQL
"""
import json
import uuid
import sys
import re
from datetime import datetime
from pathlib import Path

# Load accounts from JSON
ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/accounts.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    """Get GUID for account path."""
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

# Account GUIDs
REVOLUT_ACCOUNT = get_guid('Assets:JPY - Current Assets:Prepaid:Revolut')
LUXURY_CARD_ACCOUNT = get_guid('Liabilities:Credit Card:Luxury Card Mastercard Titanium')
GROCERIES_ACCOUNT = get_guid('Expenses:Groceries')
FEES_ACCOUNT = get_guid('Expenses:Fees')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    LUXURY_CARD_ACCOUNT: 'Liabilities:Credit Card:Luxury Card',
    GROCERIES_ACCOUNT: 'Expenses:Groceries',
    FEES_ACCOUNT: 'Expenses:Fees',
}

# ============================================================
# EDIT BELOW: Paste raw data from browser snapshot
# Format: Month header (YYYY年M月 or M月), then transactions
# ============================================================
RAW_DATA = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# ============================================================
MANUAL_OVERRIDES = {
    # Example:
    # 1: (GROCERIES_ACCOUNT, 'AliExpress'),
}


def parse_amount(amount_str):
    """Parse amount (+￥N or -￥N)."""
    amount_str = amount_str.replace(',', '').replace('￥', '').replace('+', '')
    return int(float(amount_str))


def parse_transactions(raw_data):
    """Parse RAW_DATA into transactions."""
    transactions = []
    current_year = datetime.now().year
    current_month = datetime.now().month

    for line in raw_data.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip failed/cancelled transactions
        if '失敗しました' in line or '取り消されました' in line:
            continue

        # Skip month headers
        if re.match(r'^(?:\d{4}年)?\d{1,2}月$', line):
            continue

        # Extract JPY amount
        jpy_match = re.search(r'([+-]?￥[\d,]+(?:\.\d+)?)', line)
        if not jpy_match:
            continue

        amount = parse_amount(jpy_match.group(1))
        if amount == 0:
            continue

        # Extract date: "YYYY年M月D日" or "M月D日"
        date = None
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', line)
        if date_match:
            date = datetime(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
            merchant = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '', line).strip()
        else:
            short_date_match = re.search(r'(\d{1,2})月(\d{1,2})日', line)
            if short_date_match:
                month = int(short_date_match.group(1))
                day = int(short_date_match.group(2))
                year = current_year if month <= current_month else current_year - 1
                date = datetime(year, month, day)
                merchant = re.sub(r'\d{1,2}月\d{1,2}日', '', line).strip()
            else:
                continue

        # Extract time and clean merchant name
        time_match = re.search(r'(\d{1,2}):(\d{2})', merchant)
        if time_match:
            merchant = merchant[:time_match.start()].strip()

        # Remove amount parts from merchant
        merchant = re.sub(r'[+-]?￥[\d,]+(?:\.\d+)?', '', merchant).strip()
        merchant = re.sub(r'-?\$[\d,]+(?:\.\d+)?', '', merchant).strip()

        transactions.append({
            'date': date,
            'merchant': merchant,
            'amount': amount,
        })

    return transactions


def get_transaction_info(idx, tx):
    """Get account and description for a transaction."""
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]

    merchant = tx['merchant']

    # Charge from Apple Pay / credit card
    if '経由でチャージされました' in merchant or '経由でお金が追加されました' in merchant:
        return LUXURY_CARD_ACCOUNT, None

    # Card delivery fee
    if 'カード配送料' in merchant:
        return FEES_ACCOUNT, 'Revolut'

    # AliExpress
    if 'AliExpress' in merchant:
        return GROCERIES_ACCOUNT, 'AliExpress'

    # Default: Groceries with merchant name
    return GROCERIES_ACCOUNT, merchant


def output_review(transactions):
    """Output review table."""
    print(f"{'ID':<4} {'Date':<14} {'Merchant':<30} {'Desc':<20} {'Transfer':<40} {'Increase':>12} {'Decrease':>12}")
    print("-" * 136)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 136)
        prev_date = date_str

        expense_account, description = get_transaction_info(idx, tx)
        transfer = ACCOUNT_NAMES.get(expense_account, expense_account[:40] if expense_account else '')
        increase = f"￥{tx['amount']:,}" if tx['amount'] > 0 else ""
        decrease = f"￥{abs(tx['amount']):,}" if tx['amount'] < 0 else ""

        print(f"{idx:<4} {date_str:<14} {tx['merchant']:<30} {description or '':<20} {transfer:<40} {increase:>12} {decrease:>12}")


def output_sql(transactions):
    """Output SQL statements."""
    print("BEGIN;")
    print()

    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        expense_account, description = get_transaction_info(idx, tx)

        tx_guid = str(uuid.uuid4()).replace('-', '')
        split1_guid = str(uuid.uuid4()).replace('-', '')
        split2_guid = str(uuid.uuid4()).replace('-', '')
        # Reverse order: ID 1 (newest) gets highest time
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"-- {idx}: {tx['date'].strftime('%Y-%m-%d')} {tx['merchant']} ￥{tx['amount']:,}")
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{REVOLUT_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{expense_account}', '', '', 'n', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 revolut_import.py [review|sql]", file=sys.stderr)
        sys.exit(1)

    if not RAW_DATA.strip():
        print("Error: RAW_DATA is empty. Paste data from browser snapshot.", file=sys.stderr)
        sys.exit(1)

    transactions = parse_transactions(RAW_DATA)

    if sys.argv[1] == 'review':
        output_review(transactions)
    else:
        output_sql(transactions)


if __name__ == '__main__':
    main()
