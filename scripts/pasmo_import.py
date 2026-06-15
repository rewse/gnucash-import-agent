#!/usr/bin/env python3
"""
PASMO Statement Importer

Usage:
1. Copy raw data from Mobile PASMO browser snapshot into RAW_DATA
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 scripts/pasmo_import.py review    # Review transactions
4. Run: python3 scripts/pasmo_import.py sql       # Generate SQL

PASMO never uses Expenses:Business Expenses. Transit defaults to
Expenses:Transit; override leisure trips to Expenses:Entertainment:Travel by ID.
"""
import json
import uuid
import sys
from datetime import datetime
from pathlib import Path

ACCOUNTS_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/account-guid-cache.json'
with open(ACCOUNTS_FILE) as f:
    _data = json.load(f)
    ACCOUNTS = {k.replace('Root Account:', ''): v for k, v in _data['accounts'].items()}

def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)

PASMO_ACCOUNT = get_guid('Assets:JPY - Current Assets:Prepaid:PASMO Child')
TRANSIT_ACCOUNT = get_guid('Expenses:Transit')
DINING_ACCOUNT = get_guid('Expenses:Foods:Dining')
TOKYU_CARD_ACCOUNT = get_guid('Liabilities:Credit Card:TOKYU CARD ClubQ JMB')
REIMBURSEMENT_CHILD = get_guid('Assets:JPY - Current Assets:Reimbursement:Child')
TRAVEL_ACCOUNT = get_guid('Expenses:Entertainment:Travel')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

ACCOUNT_NAMES = {
    TRANSIT_ACCOUNT: 'Expenses:Transit',
    DINING_ACCOUNT: 'Expenses:Foods:Dining',
    TOKYU_CARD_ACCOUNT: 'Liabilities:Credit Card:TOKYU CARD ClubQ JMB',
    REIMBURSEMENT_CHILD: 'Assets:Reimbursement:Child',
    TRAVEL_ACCOUNT: 'Expenses:Entertainment:Travel',
}

# Stations without a prefix that are NOT JR
TOKYO_METRO_STATIONS = ['溜池山王', '赤坂見附', '後楽園']
KEIO_STATIONS = ['南大沢']
ENODEN_STATIONS = ['江電鎌倉', '長谷', '稲村ケ崎', '江ノ島']

# Bus location name -> company
BUS_COMPANIES = {
    '江ノ電Ｂ': 'Enoden Bus',
}

PERSONAL_FILE = Path(__file__).parent.parent / '.kiro/skills/gnucash-import/references/personal.json'
with open(PERSONAL_FILE) as f:
    _personal = json.load(f)
NEAREST_STATION = _personal.get('nearest_station', '')

# ============================================================
# EDIT BELOW: Paste raw data from browser snapshot
# (without header row and 残額 column)
# ============================================================
RAW_DATA = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# ============================================================
MANUAL_OVERRIDES = {
    # Example (leisure trip -> Travel, keep auto-detected description):
    # 27: (TRAVEL_ACCOUNT, None),
}


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split()
        date_str = parts[0]
        type1 = parts[1]
        if type1 == '繰':
            continue
        if type1 == '物販':
            transactions.append({'date_str': date_str, 'type': type1, 'station1': '', 'station2': '', 'amount': int(parts[2])})
        elif type1 in ('ｵｰﾄ', 'ﾊﾞｽ等'):
            # Amount is always last; location is everything between type and amount
            station = ' '.join(parts[2:-1])
            transactions.append({'date_str': date_str, 'type': type1, 'station1': station, 'station2': '', 'amount': int(parts[-1])})
        else:
            # 入/出, ＊入, or 定 (commuter pass): type station1 出 station2 amount
            station1 = parts[2]
            idx = 3
            if parts[idx] != '出':
                station1 += ' ' + parts[idx]
                idx += 1
            idx += 1  # skip '出'
            station2 = parts[idx]
            if idx + 1 < len(parts) and not parts[idx + 1].lstrip('-+').replace(',', '').isdigit():
                station2 += ' ' + parts[idx + 1]
            transactions.append({'date_str': date_str, 'type': type1, 'station1': station1, 'station2': station2, 'amount': int(parts[-1])})
    return transactions


def get_railway_company(station1, station2):
    if station1 in ENODEN_STATIONS or station2 in ENODEN_STATIONS:
        return 'Enoshima Electric Railway'
    if station1 == NEAREST_STATION or station1 in TOKYO_METRO_STATIONS:
        return 'Tokyo Metro'
    if station1 in KEIO_STATIONS:
        return 'Keio'
    if station1.startswith('地') or station2.startswith('地'):
        return 'Tokyo Metro'
    if station1.startswith('都') or station2.startswith('都'):
        return 'Toei Subway'
    if station1.startswith('ゆ') or station2.startswith('ゆ'):
        return 'Yurikamome'
    return 'JR'


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        expense_account, override_desc = MANUAL_OVERRIDES[idx]
        if override_desc is not None:
            return expense_account, override_desc
        return expense_account, _auto_description(tx)
    if tx['type'] == 'ｵｰﾄ':
        return TOKYU_CARD_ACCOUNT, None
    if tx['type'] == '物販':
        return REIMBURSEMENT_CHILD, None
    if tx['type'] == 'ﾊﾞｽ等':
        return TRANSIT_ACCOUNT, _auto_description(tx)
    if tx['type'] in ('入', '＊入', '定'):
        return TRANSIT_ACCOUNT, _auto_description(tx)
    return None, None


def _auto_description(tx):
    if tx['type'] in ('入', '＊入', '定'):
        return get_railway_company(tx['station1'], tx['station2'])
    if tx['type'] == 'ﾊﾞｽ等':
        return BUS_COMPANIES.get(tx['station1'])
    return None


def get_purpose(tx):
    if tx['type'] in ('入', '＊入', '定'):
        return f"{tx['station1']} → {tx['station2']}"
    if tx['type'] == 'ｵｰﾄ':
        return 'オート'
    if tx['type'] == '物販':
        return '物販'
    if tx['type'] == 'ﾊﾞｽ等':
        return f"バス {tx['station1']}"
    return ''


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<17} {'Purpose':<25} {'Desc':<25} {'Transfer':<45} {'Increase':>10} {'Decrease':>10}")
    print("-" * 140)

    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if tx['amount'] == 0:
            continue
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][tx['date'].weekday()]
        date_str = f"{tx['date'].strftime('%Y-%m-%d')} {weekday}"

        if prev_date and prev_date != date_str:
            print("-" * 140)
        prev_date = date_str

        expense_account, description = get_transaction_info(idx, tx)
        if expense_account is None:
            continue

        purpose = get_purpose(tx)
        transfer = ACCOUNT_NAMES.get(expense_account, expense_account)
        increase = f"¥{tx['amount']:,}" if tx['amount'] > 0 else ""
        decrease = f"¥{abs(tx['amount']):,}" if tx['amount'] < 0 else ""

        print(f"{idx:<4} {date_str:<17} {purpose:<25} {description or '':<25} {transfer:<45} {increase:>10} {decrease:>10}")


def output_sql(transactions):
    print("BEGIN;")
    print()

    total = len([tx for tx in transactions if tx['amount'] != 0])
    count = 0
    for idx, tx in enumerate(transactions, 1):
        if tx['amount'] == 0:
            continue
        count += 1
        expense_account, description = get_transaction_info(idx, tx)
        if expense_account is None:
            continue

        tx_guid = str(uuid.uuid4()).replace('-', '')
        split1_guid = str(uuid.uuid4()).replace('-', '')
        split2_guid = str(uuid.uuid4()).replace('-', '')
        # Reverse order: ID 1 (newest) gets highest time, oldest gets 00:00:01
        reverse_idx = total - count + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = tx['date'].strftime(f'%Y-%m-%d 00:{minutes:02d}:{seconds:02d}')
        desc_sql = f"'{description.replace(chr(39), chr(39)*2)}'" if description else 'NULL'

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split1_guid}', '{tx_guid}', '{PASMO_ACCOUNT}', '', '', 'c', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{split2_guid}', '{tx_guid}', '{expense_account}', '', '', 'c', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);")
        print()

    print("COMMIT;")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('review', 'sql'):
        print("Usage: python3 scripts/pasmo_import.py [review|sql]", file=sys.stderr)
        sys.exit(1)

    if not RAW_DATA.strip():
        print("Error: RAW_DATA is empty. Paste data from browser snapshot.", file=sys.stderr)
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
