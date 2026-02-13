#!/usr/bin/env python3
"""SBI Securities Statement Importer

Usage:
  python3 sbi_securities_import.py review            # Review JPY mutual fund transactions
  python3 sbi_securities_import.py sql               # Generate SQL for JPY
  python3 sbi_securities_import.py review-usd-stock   # Review USD stock transactions
  python3 sbi_securities_import.py sql-usd-stock      # Generate SQL for USD stocks
  python3 sbi_securities_import.py review-usd-cash    # Review USD cash transactions
  python3 sbi_securities_import.py sql-usd-cash       # Generate SQL for USD cash
"""
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


# Currencies
JPY_CURRENCY = 'a77d4ee821e04f02bb7429e437c645e4'
USD_CURRENCY = '327c5a1bcfb147ceba2370ee17093159'

# JPY accounts
TRANSFER_JPY = get_guid('Liabilities:A/Payable:SBI Securities')
SBI = 'Assets:JPY - Current Assets:Securities:SBI Securities'
FUND_MAP_JPY = {
    ('全世界株式', 'NISA(つ)'): f'{SBI}:NISA (Periodic Investment):eMAXIS Slim All Countries',
    ('ＮＡＳＤＡＱ１００', 'NISA(つ)'): f'{SBI}:NISA (Periodic Investment):iFreeNEXT NASDAQ100 Index',
    ('全世界株式', 'NISA(成)'): f'{SBI}:NISA (Growth Investment):Entertainment Account:eMAXIS Slim All Countries',
    ('ＮＡＳＤＡＱ１００', 'NISA(成)'): f'{SBI}:NISA (Growth Investment):Entertainment Account:eMAXIS NASDAQ100 Index',
    ('全世界株式', '特定'): f'{SBI}:Entertainment Account:eMAXIS Slim All Countries',
    ('ＮＡＳＤＡＱ１００', '特定'): f'{SBI}:Entertainment Account:eMAXIS NASDAQ100 Index',
}

# USD accounts
SBI_USD = 'Assets:USD - Current Assets:Securities:SBI Securities'
USD_CASH = get_guid(SBI_USD)
FEES = get_guid('Expenses:Fees')
TAX = get_guid('Expenses:Tax:Income Tax')
DIVIDEND = get_guid('Income:Dividend')
NEOBANK_USD = get_guid('Assets:USD - Current Assets:Banks:d NEOBANK:Entertainment Account')
FUND_MAP_USD = {
    'QQQ': f'{SBI_USD}:Entertainment Account:Invesco QQQ Trust Series 1',
    'VGT': f'{SBI_USD}:Entertainment Account:Vanguard Information Technology Index Fund ETF',
}

ACCOUNT_NAMES = {get_guid(v): v.split(':')[-1] for v in FUND_MAP_JPY.values()}
ACCOUNT_NAMES.update({get_guid(v): v.split(':')[-1] for v in FUND_MAP_USD.values()})
ACCOUNT_NAMES[TRANSFER_JPY] = 'A/Payable:SBI Securities'
ACCOUNT_NAMES[USD_CASH] = 'SBI Securities (USD)'
ACCOUNT_NAMES[FEES] = 'Expenses:Fees'
ACCOUNT_NAMES[TAX] = 'Expenses:Tax:Income Tax'
ACCOUNT_NAMES[DIVIDEND] = 'Income:Dividend'
ACCOUNT_NAMES[NEOBANK_USD] = 'd NEOBANK (USD)'

# ============================================================
# EDIT BELOW: Paste raw data
# ============================================================
RAW_DATA_JPY = """
"""

# Tab-separated: DATE	TICKER	TYPE	QUANTITY	EXEC_AMOUNT	FEES	TAX	SETTLEMENT
RAW_DATA_USD_STOCK = """
"""

RAW_DATA_USD_CASH = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# ============================================================
MANUAL_OVERRIDES_JPY = {}
MANUAL_OVERRIDES_USD_STOCK = {}
MANUAL_OVERRIDES_USD_CASH = {}


# ── JPY Mutual Funds ──────────────────────────────────────────

def parse_jpy(raw_data):
    lines = raw_data.strip().split('\n')
    transactions = []
    i = 0
    while i + 5 < len(lines):
        m = re.match(r'^(\d{2}/\d{2}/\d{2})\t(.+)\t(.+)$', lines[i])
        if not m:
            i += 1
            continue
        trade_date_str, security, tx_type = m.groups()
        acct_type = lines[i + 1].split('\t')[0].strip()
        amount = int(lines[i + 5].strip().replace(',', '').replace('\t', ''))
        y, mo, d = trade_date_str.split('/')
        trade_date = date(2000 + int(y), int(mo), int(d))
        is_buy = '買付' in tx_type
        transactions.append({
            'date': trade_date, 'security': security, 'tx_type': tx_type,
            'acct_type': acct_type, 'amount': amount if is_buy else -amount,
        })
        i += 6
    return transactions


def resolve_jpy_account(tx):
    acct_type = tx['acct_type']
    norm = 'NISA(つ)' if 'NISA(つ)' in acct_type else 'NISA(成)' if 'NISA(成)' in acct_type else '特定'
    for (sec_key, acct_key), path in FUND_MAP_JPY.items():
        if sec_key in tx['security'] and acct_key == norm:
            return get_guid(path)
    raise ValueError(f"Unknown: {tx['security']} / {acct_type}")


def get_jpy_info(idx, tx):
    if idx in MANUAL_OVERRIDES_JPY:
        return MANUAL_OVERRIDES_JPY[idx]
    return resolve_jpy_account(tx), None


def review_jpy(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Security':<30} {'Type':<6} {'AcctType':<14} {'Fund Account':<40} {'Amount':>12}")
    print('-' * 124)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        d = tx['date']
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d.weekday()]
        date_str = f"{d.isoformat()} {weekday}"
        if prev_date and prev_date != d:
            print('-' * 124)
        prev_date = d
        fund_account, _ = get_jpy_info(idx, tx)
        fund_name = ACCOUNT_NAMES.get(fund_account, fund_account or '')
        tx_type = 'Buy' if tx['amount'] > 0 else 'Sell'
        amt = f"¥{abs(tx['amount']):,}"
        print(f"{idx:<4} {date_str:<14} {tx['security'][:30]:<30} {tx_type:<6} {tx['acct_type'][:14]:<14} {fund_name:<40} {amt:>12}")


def sql_jpy(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        fund_account, description = get_jpy_info(idx, tx)
        tx_guid, s1_guid, s2_guid = uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date'].isoformat()} 00:{minutes:02d}:{seconds:02d}"
        desc_sql = f"'{description}'" if description else 'NULL'
        amount = tx['amount']
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{JPY_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s1_guid}', '{tx_guid}', '{fund_account}', '', '', 'n', NULL, {amount}, 1, {amount}, 1, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s2_guid}', '{tx_guid}', '{TRANSFER_JPY}', '', '', 'n', NULL, {-amount}, 1, {-amount}, 1, NULL);")
        print()
    print('COMMIT;')


# ── USD Stocks ────────────────────────────────────────────────

def parse_usd_stock(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip() or line.startswith('DATE'):
            continue
        parts = line.split('\t')
        if len(parts) < 8:
            continue
        dt, ticker, tx_type, qty, exec_amt, fees, tax, settlement = parts[:8]
        y, m, d = dt.split('/')
        transactions.append({
            'date': date(int(y), int(m), int(d)),
            'ticker': ticker.strip(),
            'is_sell': '売' in tx_type,
            'quantity': int(qty),
            'exec_amount': float(exec_amt),
            'fees': float(fees),
            'tax': float(tax),
            'settlement': float(settlement),
        })
    return transactions


def get_usd_stock_info(idx, tx):
    if idx in MANUAL_OVERRIDES_USD_STOCK:
        return MANUAL_OVERRIDES_USD_STOCK[idx]
    path = FUND_MAP_USD.get(tx['ticker'])
    if not path:
        raise ValueError(f"Unknown ticker: {tx['ticker']}")
    return get_guid(path), None


def review_usd_stock(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Ticker':<6} {'Type':<6} {'Qty':>5} {'Exec':>12} {'Fees':>10} {'Tax':>10} {'Settlement':>12}")
    print('-' * 82)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        d = tx['date']
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d.weekday()]
        date_str = f"{d.isoformat()} {weekday}"
        if prev_date and prev_date != d:
            print('-' * 82)
        prev_date = d
        print(f"{idx:<4} {date_str:<14} {tx['ticker']:<6} {'Sell' if tx['is_sell'] else 'Buy':<6} {tx['quantity']:>5} ${tx['exec_amount']:>10,.2f} ${tx['fees']:>8,.2f} ${tx['tax']:>8,.2f} ${tx['settlement']:>10,.2f}")


def sql_usd_stock(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        fund_account, description = get_usd_stock_info(idx, tx)
        tx_guid = uuid.uuid4().hex
        s_fund, s_cash, s_fees, s_tax = uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date'].isoformat()} 00:{minutes:02d}:{seconds:02d}"
        desc_sql = f"'{description}'" if description else 'NULL'

        exec_cents = round(tx['exec_amount'] * 100)
        settle_cents = round(tx['settlement'] * 100)
        fees_cents = round(tx['fees'] * 100)
        tax_cents = round(tx['tax'] * 100)

        # For sell: fund decreases, cash increases
        # For buy: fund increases, cash decreases
        sign = -1 if tx['is_sell'] else 1

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{USD_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        # Fund account
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s_fund}', '{tx_guid}', '{fund_account}', '', '', 'n', NULL, {sign * exec_cents}, 100, {sign * exec_cents}, 100, NULL);")
        # Cash account
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s_cash}', '{tx_guid}', '{USD_CASH}', '', '', 'n', NULL, {-sign * settle_cents}, 100, {-sign * settle_cents}, 100, NULL);")
        # Fees
        if fees_cents:
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s_fees}', '{tx_guid}', '{FEES}', '', '', 'n', NULL, {fees_cents}, 100, {fees_cents}, 100, NULL);")
        # Tax
        if tax_cents:
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s_tax}', '{tx_guid}', '{TAX}', '', '', 'n', NULL, {tax_cents}, 100, {tax_cents}, 100, NULL);")
        print()
    print('COMMIT;')


# ── USD Cash ──────────────────────────────────────────────────

def parse_usd_cash(raw_data):
    blocks = re.split(r'\n\n+', raw_data.strip())
    transactions = []
    i = 0
    while i + 6 < len(blocks):
        dt_match = re.match(r'(\d{4}/\d{2}/\d{2})', blocks[i])
        if not dt_match:
            i += 1
            continue
        dt = dt_match.group(1)
        tx_type = blocks[i + 1].strip()  # 入金/出金
        category = blocks[i + 2].strip()  # 分配金 or -
        # blocks[i + 3] = currency (skip)
        desc = blocks[i + 4].strip()
        withdrawal = blocks[i + 5].strip()
        deposit = blocks[i + 6].strip()
        y, m, d = dt.split('/')
        amount_str = deposit if deposit != '-' else withdrawal
        amount = float(amount_str.replace(',', ''))
        if tx_type == '出金':
            amount = -amount
        transactions.append({
            'date': date(int(y), int(m), int(d)),
            'category': category, 'desc': desc, 'amount': amount,
        })
        i += 7
    return transactions


def resolve_usd_cash_account(tx):
    if tx['category'] == '分配金':
        return DIVIDEND
    if '住信SBI' in tx['desc'] or '外貨預り金' in tx['desc']:
        return NEOBANK_USD
    raise ValueError(f"Unknown: {tx['desc']}")


def get_usd_cash_info(idx, tx):
    if idx in MANUAL_OVERRIDES_USD_CASH:
        return MANUAL_OVERRIDES_USD_CASH[idx]
    return resolve_usd_cash_account(tx), None


def review_usd_cash(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Category':<10} {'Desc':<50} {'Transfer':<25} {'Amount':>12}")
    print('-' * 118)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        d = tx['date']
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d.weekday()]
        date_str = f"{d.isoformat()} {weekday}"
        if prev_date and prev_date != d:
            print('-' * 118)
        prev_date = d
        account, _ = get_usd_cash_info(idx, tx)
        transfer = ACCOUNT_NAMES.get(account, account or '')
        sign = '+' if tx['amount'] > 0 else '-'
        print(f"{idx:<4} {date_str:<14} {tx['category']:<10} {tx['desc'][:50]:<50} {transfer:<25} {sign}${abs(tx['amount']):>10,.2f}")


def sql_usd_cash(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account, description = get_usd_cash_info(idx, tx)
        tx_guid, s1_guid, s2_guid = uuid.uuid4().hex, uuid.uuid4().hex, uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date'].isoformat()} 00:{minutes:02d}:{seconds:02d}"
        desc_sql = f"'{description}'" if description else 'NULL'
        cents = round(tx['amount'] * 100)
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{USD_CURRENCY}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s1_guid}', '{tx_guid}', '{USD_CASH}', '', '', 'n', NULL, {cents}, 100, {cents}, 100, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s2_guid}', '{tx_guid}', '{account}', '', '', 'n', NULL, {-cents}, 100, {-cents}, 100, NULL);")
        print()
    print('COMMIT;')


# ── Main ──────────────────────────────────────────────────────

COMMANDS = {
    'review': (RAW_DATA_JPY, parse_jpy, review_jpy),
    'sql': (RAW_DATA_JPY, parse_jpy, sql_jpy),
    'review-usd-stock': (RAW_DATA_USD_STOCK, parse_usd_stock, review_usd_stock),
    'sql-usd-stock': (RAW_DATA_USD_STOCK, parse_usd_stock, sql_usd_stock),
    'review-usd-cash': (RAW_DATA_USD_CASH, parse_usd_cash, review_usd_cash),
    'sql-usd-cash': (RAW_DATA_USD_CASH, parse_usd_cash, sql_usd_cash),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python3 sbi_securities_import.py [{' | '.join(COMMANDS)}]", file=sys.stderr)
        sys.exit(1)
    raw_ref, parse_fn, output_fn = COMMANDS[sys.argv[1]]
    # Resolve RAW_DATA from global name
    raw = globals()[{v[0]: k for k, v in globals().items() if isinstance(v, str)}.get(id(raw_ref), '')]  if False else raw_ref
    if not raw_ref.strip():
        print(f"Error: RAW_DATA is empty for {sys.argv[1]}.", file=sys.stderr)
        sys.exit(1)
    transactions = parse_fn(raw_ref)
    output_fn(transactions)


if __name__ == '__main__':
    main()
