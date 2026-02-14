#!/usr/bin/env python3
"""
Amazon Gift Certificate Statement Importer

Usage:
1. Copy raw data into RAW_DATA (tab-separated: date, description, amount, balance, account, item)
2. Run: python3 scripts/amazon_gc_import.py review    # Review transactions
3. Run: python3 scripts/amazon_gc_import.py sql       # Generate SQL
"""
import json
import uuid
import sys
import re
from datetime import datetime
from pathlib import Path

# Load accounts from JSON
ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-guid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    """Get GUID for account path."""
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

AMAZON_GC_ACCOUNT = get_guid('Assets:JPY - Current Assets:Prepaid:Amazon Gift Certificate')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

# ============================================================
# EDIT BELOW: Paste raw data (tab-separated)
# Format: date\tdescription\tamount\tbalance\taccount\titem
# ============================================================
RAW_DATA = """
"""


def parse_date(date_str):
    """Parse Japanese date format (YYYY年M月D日)."""
    match = re.match(r'(\d+)年(\d+)月(\d+)日', date_str)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def parse_amount(amount_str):
    """Parse amount (￥N or -￥N)."""
    amount_str = amount_str.replace(',', '').replace('￥', '')
    return int(amount_str)


def parse_transactions(raw_data):
    """Parse RAW_DATA into transactions, grouping by description+balance."""
    lines = [l for l in raw_data.strip().split('\n') if l.strip()]
    
    # Group lines by (description, balance) for multi-split transactions
    groups = {}
    for line in lines:
        parts = line.split('\t')
        if len(parts) < 5:
            continue
        date_str, desc, amount_str, balance, account = parts[:5]
        item = parts[5] if len(parts) > 5 else ''
        key = (date_str, desc, balance)
        if key not in groups:
            groups[key] = []
        groups[key].append({
            'date': parse_date(date_str),
            'desc': desc,
            'amount': parse_amount(amount_str),
            'balance': balance,
            'account': account,
            'item': item.strip(),
        })
    
    # Convert to transaction list
    transactions = []
    for key, splits in sorted(groups.items(), key=lambda x: x[1][0]['date'], reverse=True):
        total_amount = sum(s['amount'] for s in splits)
        transactions.append({
            'date': splits[0]['date'],
            'desc': splits[0]['desc'],
            'total_amount': total_amount,
            'splits': splits,
        })
    return transactions


def get_description(tx):
    """Extract description from transaction."""
    desc = tx['desc']
    if 'Amazon Pay' in desc and 'からのギフトカード' in desc:
        return 'Amazon Pay'
    if 'Amazon Payの注文に適用' in desc:
        return 'Amazon Pay'
    if 'Amazon.co.jpの注文に適用' in desc:
        return 'Amazon'
    if 'ギフトカードが追加されました' in desc:
        # Use item field as description if available
        if tx['splits'][0]['item']:
            return tx['splits'][0]['item']
        return None
    if '解除' in desc:
        return 'Amazon'
    return None


def output_review(transactions):
    """Output review table."""
    print(f"{'ID':<6} {'Date':<14} {'Type':<8} {'Item':<25} {'Desc':<20} {'Transfer':<45} {'Increase':>10} {'Decrease':>10}")
    print("-" * 145)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')}"
        date_display = f"{date_str} ({weekday})"

        if prev_date and prev_date != date_str:
            print("-" * 145)
        prev_date = date_str

        # Determine type
        if tx['total_amount'] > 0:
            tx_type = 'Charge'
        elif tx['total_amount'] < 0:
            tx_type = 'Payment'
        else:
            tx_type = 'Refund'

        description = get_description(tx)
        
        if len(tx['splits']) == 1:
            split = tx['splits'][0]
            increase = f"￥{tx['total_amount']:,}" if tx['total_amount'] > 0 else ""
            decrease = f"￥{abs(tx['total_amount']):,}" if tx['total_amount'] < 0 else ""
            print(f"{idx:<6} {date_display:<14} {tx_type:<8} {split['item']:<25} {description or '':<20} {split['account']:<45} {increase:>10} {decrease:>10}")
        else:
            # Multi-split: show header then splits
            increase = f"￥{tx['total_amount']:,}" if tx['total_amount'] > 0 else ""
            decrease = f"￥{abs(tx['total_amount']):,}" if tx['total_amount'] < 0 else ""
            print(f"{idx:<6} {date_display:<14} {tx_type:<8} {'':<25} {description or '':<20} {'':<45} {increase:>10} {decrease:>10}")
            for sub_idx, split in enumerate(tx['splits'], 1):
                sub_increase = f"￥{split['amount']:,}" if split['amount'] > 0 else ""
                sub_decrease = f"￥{abs(split['amount']):,}" if split['amount'] < 0 else ""
                print(f"{idx}-{sub_idx:<4} {'':<14} {'':<8} {split['item']:<25} {'':<20} {split['account']:<45} {sub_increase:>10} {sub_decrease:>10}")


def output_sql(transactions):
    """Output SQL statements."""
    print("BEGIN;")
    print()

    for idx, tx in enumerate(transactions, 1):
        tx_guid = str(uuid.uuid4()).replace('-', '')
        date_str = tx['date'].strftime('%Y-%m-%d 12:00:00')
        description = get_description(tx)
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"-- Transaction {idx}: {tx['date'].strftime('%Y-%m-%d')} {description or 'N/A'} ￥{tx['total_amount']:,}")
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")

        # Amazon GC split (asset side)
        split_guid = str(uuid.uuid4()).replace('-', '')
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split_guid}', '{tx_guid}', '{AMAZON_GC_ACCOUNT}', '', '', 'n', NULL, {tx['total_amount']}, 1, {tx['total_amount']}, 1, NULL);")

        # Expense/Income splits
        for split in tx['splits']:
            split_guid = str(uuid.uuid4()).replace('-', '')
            account_guid = get_guid(split['account'])
            amount = -split['amount']  # Reverse for double-entry
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{split_guid}', '{tx_guid}', '{account_guid}', '', '', 'n', NULL, {amount}, 1, {amount}, 1, NULL);")

        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 amazon_gc_import.py [review|sql]", file=sys.stderr)
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
