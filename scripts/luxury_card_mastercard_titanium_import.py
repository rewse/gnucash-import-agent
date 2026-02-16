#!/usr/bin/env python3
"""Luxury Card Mastercard Titanium Statement Importer

Usage:
1. Copy raw data from browser snapshot into RAW_DATA (card) or RAW_DATA_POINTS (points)
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py review
4. Run: python3 tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py sql
5. Run: python3 tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py points-review
6. Run: python3 tmp/luxury_card_mastercard_titanium_import_YYYYMMDD.py points-sql
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


SOURCE_ACCOUNT = get_guid('Liabilities:Credit Card:Luxury Card Mastercard Titanium')
POINTS_ACCOUNT = get_guid('Assets:JPY - Current Assets:Reward Programs:Luxury Reward')
POINT_INCOME = get_guid('Income:Point Charge')
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'

# Transaction type mappings
DINING = get_guid('Expenses:Foods:Dining')
FOODSTUFFS = get_guid('Expenses:Foods:Foodstuffs')
BIKE = get_guid('Expenses:Bike')
HOUSE_MAINT = get_guid('Expenses:House:Maintenance')
CLOTHES = get_guid('Expenses:Clothes')
SPORTS = get_guid('Expenses:Entertainment:Sports')
BOOKS = get_guid('Expenses:Entertainment:Books')
PHONE_MOBILE = get_guid('Expenses:Utilities:Phone:Mobile')
FURUSATO = get_guid('Expenses:Tax:Furusato Tax')
INSURANCES = get_guid('Expenses:Insurances')
SUPPLIES = get_guid('Expenses:Supplies')
INTERNET = get_guid('Expenses:Utilities:Internet')
PHONE_LANDLINE = get_guid('Expenses:Utilities:Phone:Landline')
MOVIES = get_guid('Expenses:Entertainment:Movies')
INSURANCES_HEALTH = get_guid('Expenses:Insurances:Health Insurances')

ACCOUNT_NAMES = {
    DINING: 'Expenses:Foods:Dining',
    FOODSTUFFS: 'Expenses:Foods:Foodstuffs',
    BIKE: 'Expenses:Bike',
    HOUSE_MAINT: 'Expenses:House:Maintenance',
    CLOTHES: 'Expenses:Clothes',
    SPORTS: 'Expenses:Entertainment:Sports',
    BOOKS: 'Expenses:Entertainment:Books',
    PHONE_MOBILE: 'Expenses:Utilities:Phone:Mobile',
    FURUSATO: 'Expenses:Tax:Furusato Tax',
    INSURANCES: 'Expenses:Insurances',
    SUPPLIES: 'Expenses:Supplies',
    INTERNET: 'Expenses:Utilities:Internet',
    PHONE_LANDLINE: 'Expenses:Utilities:Phone:Landline',
    MOVIES: 'Expenses:Entertainment:Movies',
    INSURANCES_HEALTH: 'Expenses:Insurances:Health Insurances',
    POINTS_ACCOUNT: 'Luxury Reward',
    POINT_INCOME: 'Income:Point Charge',
}

# ============================================================
# EDIT BELOW: Paste raw data from browser snapshot
# ============================================================
RAW_DATA = """
"""

RAW_DATA_POINTS = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# For KDDI split: ID: 'KDDI'
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
        line = line.strip()
        if not line:
            continue
        m = re.match(r'(.+?)(\d{2})\.(\d{2})\.(\d{2})\s*\d+回払い\s*(?:お支払い方法変更可能\s*)?([\d,]+)円', line)
        if not m:
            continue
        merchant = m.group(1).strip()
        yy, mm, dd = int(m.group(2)), int(m.group(3)), int(m.group(4))
        amount = int(m.group(5).replace(',', ''))
        transactions.append({
            'date': date(2000 + yy, mm, dd),
            'amount': -amount,
            'merchant': merchant,
            'merchant_norm': normalize(merchant),
        })
    return transactions


def parse_points(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        ym = parts[0].strip()
        points = int(parts[1].strip())
        y, m = ym.split('-')
        transactions.append({
            'date': date(int(y), int(m), 15),
            'amount': points,
        })
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        v = MANUAL_OVERRIDES[idx]
        if v == 'KDDI':
            return 'KDDI', 'KDDI'
        return v
    m = tx['merchant']
    mn = tx['merchant_norm']
    if 'カブシキガイシヤループ' in m:
        return BIKE, 'Loop'
    if 'SQ*' in mn and 'マラドウ' in m:
        return DINING, 'Mala Do'
    if 'ロイヤルホスト' in m:
        return DINING, 'Royal Host'
    if 'マクドナルド' in m:
        return DINING, "McDonald's"
    if 'サブウエイ' in m:
        return DINING, 'Subway'
    if 'ヨ－クフ－ズ' in m:
        return FOODSTUFFS, 'York Foods'
    if 'シヤトレーゼ' in m:
        return FOODSTUFFS, 'Chateraise'
    if 'パルシステム' in m:
        return INSURANCES_HEALTH, 'Palsystem'
    if 'ココカラフアイン' in m:
        return SUPPLIES, 'Cocokara Fine'
    if 'カジ－' in m:
        return HOUSE_MAINT, 'CaSy'
    if 'ユニクロ' in m:
        return CLOTHES, 'UNIQLO'
    if 'パ－ソナルジムアスピ' in m:
        return SPORTS, 'ASPI'
    if 'ラクテンマガジン' in m:
        return BOOKS, 'Rakuten Magazine'
    if 'ノート' == m:
        return BOOKS, 'note'
    if 'ＵＱｍｏｂｉｌｅ' in m:
        return PHONE_MOBILE, 'UQ Mobile'
    if 'ニホンツウシンカブシキガイシヤ' in m:
        return PHONE_MOBILE, 'Nihon Tsushin'
    if 'フルナビマネー' in m:
        return FURUSATO, 'Furunavi'
    if 'ミカタシヨウガクタンキホケン' in m:
        return INSURANCES, 'MIKATA Small Amount Short Term Insurance'
    if 'ＫＤＤＩ' in m:
        return 'KDDI', 'KDDI'
    raise ValueError(f"Unknown transaction at ID {idx}: {tx['merchant']}")


# KDDI fixed split amounts
KDDI_SPLITS = [
    (INTERNET, 4454, 'KDDI Internet'),
    (PHONE_LANDLINE, 1214, 'KDDI Phone'),
    (MOVIES, 2290, 'KDDI Streaming'),
]


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Merchant':<30} {'Desc':<25} {'Transfer':<40} {'Amount':>10}")
    print('-' * 127)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if prev_date and prev_date != tx['date']:
            print('-' * 127)
        prev_date = tx['date']
        account, description = get_transaction_info(idx, tx)
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        date_str = f"{tx['date']} {weekday[tx['date'].weekday()]}"
        if account == 'KDDI':
            for acct, amt, desc in KDDI_SPLITS:
                transfer = ACCOUNT_NAMES.get(acct, acct or '')
                print(f"{idx:<4} {date_str:<14} {'KDDI':<30} {desc:<25} {transfer:<40} {f'¥{amt:,}':>10}")
        else:
            transfer = ACCOUNT_NAMES.get(account, account or '')
            amt = f"¥{abs(tx['amount']):,}"
            merchant_display = tx['merchant_norm'][:28]
            print(f"{idx:<4} {date_str:<14} {merchant_display:<30} {description or '':<25} {transfer:<40} {amt:>10}")


def output_sql(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account, description = get_transaction_info(idx, tx)
        tx_date = tx['date']
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx_date} 00:{minutes:02d}:{seconds:02d}"

        if account == 'KDDI':
            # Multi-split transaction
            tx_guid = uuid.uuid4().hex
            s_source_guid = uuid.uuid4().hex
            desc_sql = "'KDDI'"
            print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
            print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s_source_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
            for acct, amt, _ in KDDI_SPLITS:
                s_guid = uuid.uuid4().hex
                print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
                print(f"VALUES ('{s_guid}', '{tx_guid}', '{acct}', '', '', 'n', NULL, {amt}, 1, {amt}, 1, NULL);")
            print()
        else:
            tx_guid = uuid.uuid4().hex
            s1_guid = uuid.uuid4().hex
            s2_guid = uuid.uuid4().hex
            desc_sql = f"'{description}'" if description else 'NULL'
            print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
            print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s1_guid}', '{tx_guid}', '{SOURCE_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s2_guid}', '{tx_guid}', '{account}', '', '', 'n', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);")
            print()
    print('COMMIT;')


def output_points_review(transactions):
    print(f"{'ID':<4} {'Date':<12} {'Points':>10} {'Transfer':<30}")
    print('-' * 60)
    for idx, tx in enumerate(transactions, 1):
        pts = f"{tx['amount']:+,}"
        print(f"{idx:<4} {tx['date'].strftime('%Y-%m'):<12} {pts:>10} {'Income:Point Charge':<30}")


def output_points_sql(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        tx_guid = uuid.uuid4().hex
        s1_guid = uuid.uuid4().hex
        s2_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date']} 00:{minutes:02d}:{seconds:02d}"
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), 'Luxury Reward');")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s1_guid}', '{tx_guid}', '{POINTS_ACCOUNT}', '', '', 'n', NULL, {tx['amount']}, 1, {tx['amount']}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s2_guid}', '{tx_guid}', '{POINT_INCOME}', '', '', 'n', NULL, {-tx['amount']}, 1, {-tx['amount']}, 1, NULL);")
        print()
    print('COMMIT;')


def main():
    cmds = ('review', 'sql', 'points-review', 'points-sql')
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(f'Usage: python3 luxury_card_mastercard_titanium_import.py [{"|".join(cmds)}]', file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd.startswith('points'):
        if not RAW_DATA_POINTS.strip():
            print('Error: RAW_DATA_POINTS is empty.', file=sys.stderr)
            sys.exit(1)
        transactions = parse_points(RAW_DATA_POINTS)
        if cmd == 'points-review':
            output_points_review(transactions)
        else:
            output_points_sql(transactions)
    else:
        if not RAW_DATA.strip():
            print('Error: RAW_DATA is empty.', file=sys.stderr)
            sys.exit(1)
        transactions = parse_transactions(RAW_DATA)
        if cmd == 'review':
            output_review(transactions)
        else:
            output_sql(transactions)


if __name__ == '__main__':
    main()
