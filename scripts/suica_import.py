#!/usr/bin/env python3
"""
Suica Statement Importer

Usage:
1. Copy raw data from Mobile Suica browser snapshot into RAW_DATA
2. Set NEAREST_STATION to your nearest station
3. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
4. Run: python3 scripts/suica_import.py review    # Review transactions
5. Run: python3 scripts/suica_import.py sql       # Generate SQL
"""
import uuid
import sys
from datetime import datetime

# Account GUIDs
SUICA_ACCOUNT = '877c55f020af4dda978b451cd88865d4'
TRANSIT_ACCOUNT = '283560543bf6c05b9a9788983cf0f8fc'
BUSINESS_ACCOUNT = 'be3d3970b18b6264fa9e696b94536538'
DINING_ACCOUNT = '4410b4bef21aefd154d0a33935a42e27'
LUMINE_CARD_ACCOUNT = '7b5ddf7803f60445299f056fff86536c'
MEDICAL_TRANSIT_ACCOUNT = '7d61e3435a19574989a9a1064314a4e6'
AWS_REIMBURSEMENT_ACCOUNT = '413bf1fcef1c0b36cef7986ea743603d'
GROCERIES_ACCOUNT = 'e37db4ce483a749c27d9a3e5bee12981'
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    TRANSIT_ACCOUNT: 'Expenses:Transit',
    BUSINESS_ACCOUNT: 'Expenses:Business Expenses',
    DINING_ACCOUNT: 'Expenses:Foods:Dining',
    GROCERIES_ACCOUNT: 'Expenses:Groceries',
    LUMINE_CARD_ACCOUNT: 'Liabilities:Credit Card:LUMINE CARD',
    MEDICAL_TRANSIT_ACCOUNT: 'Expenses:Medical Expenses:Transit',
    AWS_REIMBURSEMENT_ACCOUNT: 'Assets:Reimbursement:AWS Japan',
}

# Tokyo Metro stations (no prefix, excluding NEAREST_STATION which is added dynamically)
TOKYO_METRO_STATIONS = ['溜池山王', '赤坂見附']

# Keio stations
KEIO_STATIONS = ['南大沢']

# ============================================================
# EDIT BELOW: Set your nearest station for business expense detection
# ============================================================
NEAREST_STATION = ""

# ============================================================
# EDIT BELOW: Paste raw data from browser snapshot
# ============================================================
RAW_DATA = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# ============================================================
MANUAL_OVERRIDES = {
    # Example:
    # 9: (DINING_ACCOUNT, 'Kiraku'),
    # 14: (MEDICAL_TRANSIT_ACCOUNT, None),
}


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split()
        date_str = parts[0]
        type1 = parts[1]
        if type1 == '物販':
            transactions.append({'date_str': date_str, 'type': type1, 'station1': '', 'station2': '', 'amount': int(parts[2])})
        elif type1 == 'ｵｰﾄ':
            transactions.append({'date_str': date_str, 'type': type1, 'station1': parts[2], 'station2': '', 'amount': int(parts[3])})
        elif type1 == '繰':
            continue
        else:
            station1 = parts[2]
            if parts[3] != '出':
                station1 += ' ' + parts[3]
                idx = 4
            else:
                idx = 3
            idx += 1
            station2 = parts[idx]
            if idx + 1 < len(parts) and not parts[idx + 1].lstrip('-+').isdigit():
                station2 += ' ' + parts[idx + 1]
            transactions.append({'date_str': date_str, 'type': type1, 'station1': station1, 'station2': station2, 'amount': int(parts[-1])})
    return transactions


def get_railway_company(station1, station2):
    if station1 == NEAREST_STATION or station1 in TOKYO_METRO_STATIONS:
        return 'Tokyo Metro'
    if station1 in KEIO_STATIONS:
        return 'Keio'
    if station1.startswith('地') or station2.startswith('地'):
        return 'Tokyo Metro'
    if station1.startswith('都') or station2.startswith('都'):
        return 'Toei Subway'
    return 'JR'


def is_weekday(date):
    return date.weekday() < 5


def detect_business_expense(txs, date):
    if not is_weekday(date):
        return False
    pattern = [(t['station1'], t['station2']) for t in txs if t['date'] == date and t['type'] in ['入', '＊入']]
    has_to_office = any(s1 == NEAREST_STATION and s2 in ['新宿', '地 新宿'] for s1, s2 in pattern)
    has_to_meguro = any(s1 in ['新宿', '地 新宿'] and s2 == '目黒' for s1, s2 in pattern)
    has_from_meguro = any(s1 == '目黒' and s2 in ['新宿', '地 新宿'] for s1, s2 in pattern)
    return has_to_office and has_to_meguro and has_from_meguro


def get_transaction_info(transactions, idx, tx):
    """Get account and description for a transaction."""
    if idx in MANUAL_OVERRIDES:
        expense_account, override_desc = MANUAL_OVERRIDES[idx]
        if override_desc is not None:
            description = override_desc
        elif tx['type'] in ['入', '＊入']:
            description = get_railway_company(tx['station1'], tx['station2'])
        else:
            description = None
    elif tx['type'] == 'ｵｰﾄ':
        expense_account = LUMINE_CARD_ACCOUNT
        description = None
    elif tx['type'] == '物販':
        expense_account = DINING_ACCOUNT
        description = None
    elif tx['type'] in ['入', '＊入']:
        is_business = detect_business_expense(transactions, tx['date'])
        expense_account = BUSINESS_ACCOUNT if is_business else TRANSIT_ACCOUNT
        description = get_railway_company(tx['station1'], tx['station2'])
    else:
        return None, None
    return expense_account, description


def get_purpose(tx):
    """Get purpose string for display."""
    if tx['type'] in ['入', '＊入']:
        return f"{tx['station1']} → {tx['station2']}"
    elif tx['type'] == 'ｵｰﾄ':
        return 'オート'
    elif tx['type'] == '物販':
        return '物販'
    return ''


def output_review(transactions):
    """Output review table."""
    print(f"{'ID':<4} {'Date':<17} {'Purpose':<25} {'Desc':<15} {'Transfer':<40} {'Increase':>10} {'Decrease':>10}")
    print("-" * 124)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 124)
        prev_date = date_str

        expense_account, description = get_transaction_info(transactions, idx, tx)
        if expense_account is None:
            continue

        purpose = get_purpose(tx)
        transfer = ACCOUNT_NAMES.get(expense_account, expense_account)
        increase = f"¥{tx['amount']:,}" if tx['amount'] > 0 else ""
        decrease = f"¥{abs(tx['amount']):,}" if tx['amount'] < 0 else ""

        print(f"{idx:<4} {date_str:<17} {purpose:<25} {description or '':<15} {transfer:<40} {increase:>10} {decrease:>10}")


def output_sql(transactions):
    """Output SQL statements."""
    print("BEGIN;")
    print()

    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        expense_account, description = get_transaction_info(transactions, idx, tx)
        if expense_account is None:
            continue

        tx_guid = str(uuid.uuid4()).replace('-', '')
        split1_guid = str(uuid.uuid4()).replace('-', '')
        split2_guid = str(uuid.uuid4()).replace('-', '')
        # Reverse order: ID 1 (newest) gets highest time, ID N (oldest) gets 00:00:01
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description}'" if description else 'NULL'

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{SUICA_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{expense_account}', '', '', 'n', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['review', 'sql']:
        print("Usage: python3 suica_import.py [review|sql]", file=sys.stderr)
        sys.exit(1)

    if not RAW_DATA.strip():
        print("Error: RAW_DATA is empty. Paste data from browser snapshot.", file=sys.stderr)
        sys.exit(1)

    if not NEAREST_STATION:
        print("Error: NEAREST_STATION is empty. Set your nearest station.", file=sys.stderr)
        sys.exit(1)

    transactions = parse_transactions(RAW_DATA)

    now = datetime.now()
    for tx in transactions:
        month, day = map(int, tx['date_str'].split('/'))
        year = now.year if month <= now.month else now.year - 1
        tx['date'] = datetime(year, month, day)

    if sys.argv[1] == 'review':
        output_review(transactions)
    else:
        output_sql(transactions)


if __name__ == '__main__':
    main()
