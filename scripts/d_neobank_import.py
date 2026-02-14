#!/usr/bin/env python3
"""d NEOBANK Statement Importer

Usage:
1. Paste tab-separated data into RAW_DATA (CURRENCY, DATE, DESC, WITHDRAWAL, DEPOSIT)
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 tmp/d_neobank_import_YYYYMMDD.py review
4. Run: python3 tmp/d_neobank_import_YYYYMMDD.py sql
"""
import json
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


# Source accounts
SOURCE_ACCOUNTS = {
    'JPY': get_guid('Assets:JPY - Current Assets:Banks:d NEOBANK'),
    'USD': get_guid('Assets:USD - Current Assets:Banks:d NEOBANK'),
}

# Transfer accounts
RESERVED_MONEY_FROM = get_guid('Income:Reserved Money from Family')
RESERVED_MONEY_TO = get_guid('Expenses:Reserved Money to Family')
REIMBURSEMENT_FAMILY = get_guid('Assets:JPY - Current Assets:Reimbursement:Family')
LIVING_COST_FAMILY = get_guid('Expenses:Living Cost to Family')
REIMBURSEMENT_FRIEND = get_guid('Assets:JPY - Current Assets:Reimbursement:Friend')
SBI_SHINSEI = get_guid('Assets:JPY - Current Assets:Banks:SBI Shinsei Bank')
NATIONAL_ALLOWANCE = get_guid('Income:National Allowance')
REIMBURSEMENT_AWS = get_guid('Assets:JPY - Current Assets:Reimbursement:AWS Japan')
TOKYU_CARD = get_guid('Liabilities:Credit Card:TOKYU CARD ClubQ JMB')
AMAZON_MC = get_guid('Liabilities:Credit Card:Amazon MasterCard Gold')
ANA_SFC = get_guid('Liabilities:Credit Card:ANA Super Flyers Gold Card')
PAYPAY_CARD = get_guid('Liabilities:Credit Card:PayPay Card JCB')
LUXURY_CARD = get_guid('Liabilities:Credit Card:Luxury Card Mastercard Titanium')
GOLD_POINT = get_guid('Liabilities:Credit Card:GOLD POINT CARD +')
RESERVED_ACCT = get_guid('Assets:JPY - Current Assets:Banks:d NEOBANK:Reserved Account')
LONGTERM_ACCT = get_guid('Assets:JPY - Current Assets:Banks:d NEOBANK:Longterm Account')
RETIREMENT_ACCT = get_guid('Assets:JPY - Current Assets:Banks:d NEOBANK:Retirement Account')
USD_ACCT = get_guid('Assets:USD - Current Assets:Banks:d NEOBANK')
INCOME_TAX = get_guid('Expenses:Tax:Income Tax')
FIXED_ASSETS_TAX = get_guid('Expenses:Tax:Fixed Assets Tax')
INTEREST_INCOME = get_guid('Income:Interest Income')

CURRENCIES = {
    'JPY': 'a77d4ee821e04f02bb7429e437c645e4',
    'USD': '327c5a1bcfb147ceba2370ee17093159',
}
CURRENCY_DENOM = {'JPY': 1, 'USD': 100}

ACCOUNT_NAMES = {
    RESERVED_MONEY_FROM: 'Income:Reserved Money from Family',
    RESERVED_MONEY_TO: 'Expenses:Reserved Money to Family',
    REIMBURSEMENT_FAMILY: 'Assets:Reimbursement:Family',
    LIVING_COST_FAMILY: 'Expenses:Living Cost to Family',
    REIMBURSEMENT_FRIEND: 'Assets:Reimbursement:Friend',
    SBI_SHINSEI: 'Assets:Banks:SBI Shinsei Bank',
    NATIONAL_ALLOWANCE: 'Income:National Allowance',
    REIMBURSEMENT_AWS: 'Assets:Reimbursement:AWS Japan',
    TOKYU_CARD: 'Liabilities:TOKYU CARD',
    AMAZON_MC: 'Liabilities:Amazon MasterCard Gold',
    ANA_SFC: 'Liabilities:ANA Super Flyers Gold',
    PAYPAY_CARD: 'Liabilities:PayPay Card JCB',
    LUXURY_CARD: 'Liabilities:Luxury Card Titanium',
    GOLD_POINT: 'Liabilities:GOLD POINT CARD +',
    RESERVED_ACCT: 'd NEOBANK:Reserved Account',
    LONGTERM_ACCT: 'd NEOBANK:Longterm Account',
    RETIREMENT_ACCT: 'd NEOBANK:Retirement Account',
    USD_ACCT: 'd NEOBANK (USD)',
    INCOME_TAX: 'Expenses:Tax:Income Tax',
    FIXED_ASSETS_TAX: 'Expenses:Tax:Fixed Assets Tax',
    INTEREST_INCOME: 'Income:Interest Income',
}

# Skipped patterns
SKIP_PATTERNS = ['口座振替 ＤＦ エムアイカード', '約定返済 円 住宅']

# Simple rules: (currency, description) -> (account_guid, description)
SIMPLE_RULES = {
    ('JPY', '口座振替 ＤＦ トウキユウカード'): (TOKYU_CARD, None),
    ('JPY', '口座振替 ＰａｙＰａｙカード'): (PAYPAY_CARD, None),
    ('JPY', '口座振替 ＡＰアプラス'): (LUXURY_CARD, None),
    ('JPY', '口座振替 ＤＦ ＧＰマーケテインク'): (GOLD_POINT, None),
    ('JPY', '普通 円 予備費'): (RESERVED_ACCT, None),
    ('JPY', '普通 円 長期貯蓄'): (LONGTERM_ACCT, None),
    ('JPY', '普通 円 老後資金'): (RETIREMENT_ACCT, None),
    ('JPY', '地方税'): (INCOME_TAX, 'Tokyo'),
    ('JPY', '国税'): (INCOME_TAX, 'Japan'),
    ('JPY', '利息'): (INTEREST_INCOME, None),
    ('USD', '国税'): (INCOME_TAX, 'Japan'),
    ('USD', '利息'): (INTEREST_INCOME, None),
}

# ============================================================
# EDIT BELOW: Paste raw data
# ============================================================
RAW_DATA = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# For split: ID: [(ACCOUNT_GUID, amount, 'Description'), ...]
# ============================================================
MANUAL_OVERRIDES = {
}


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        currency = parts[0].strip()
        y, m, d = parts[1].strip().split('/')
        desc = parts[2].strip()
        withdrawal = float(parts[3].strip()) if parts[3].strip() else 0
        deposit = float(parts[4].strip()) if len(parts) > 4 and parts[4].strip() else 0
        transactions.append({
            'date': date(int(y), int(m), int(d)),
            'desc': desc,
            'currency': currency,
            'amount': deposit - withdrawal,
        })
    return transactions


def is_skip(tx):
    return any(tx['desc'].startswith(p) for p in SKIP_PATTERNS)


def get_transaction_info(idx, tx):
    """Return (account_guid, description) or list of (account_guid, amount, description) for splits."""
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]

    desc = tx['desc']
    currency = tx['currency']
    amount = tx['amount']

    # Simple rules
    key = (currency, desc)
    if key in SIMPLE_RULES:
        return SIMPLE_RULES[key]

    # Prefix-based rules
    if desc.startswith('振込＊シバタ ア'):
        if amount > 0 and amount == 32400:
            return (RESERVED_MONEY_FROM, 'Wife')
        elif amount > 0:
            raise ValueError(f"ID {idx}: 振込＊シバタ ア* deposit ¥{int(amount):,} — need manual override (email lookup)")
        else:
            return (RESERVED_MONEY_TO, 'Wife')

    if desc.startswith('振込＊シバタ ノ'):
        if amount == -100000:
            return [(REIMBURSEMENT_FAMILY, -60000, 'Parents'), (LIVING_COST_FAMILY, -40000, 'Parents')]
        raise ValueError(f"ID {idx}: 振込＊シバタ ノ* amount ¥{int(amount):,} — need manual override")

    if desc.startswith('振込＊シズ'):
        return (REIMBURSEMENT_FRIEND, None)

    if desc.startswith('振込＊シバタ タツノリ'):
        return (SBI_SHINSEI, None)

    if desc.startswith('振込＊ジドウテアテ'):
        return (NATIONAL_ALLOWANCE, 'Japan')

    if desc.startswith('振込＊アマゾンウエブサービスジヤパン'):
        return (REIMBURSEMENT_AWS, 'AWS Japan')

    if desc.startswith('振込＊０１８サポートキユウフキン'):
        return (NATIONAL_ALLOWANCE, 'Tokyo')

    if desc.startswith('振込＊シガクザイダンチユウガクジヨセイ'):
        return (NATIONAL_ALLOWANCE, 'Tokyo')

    if desc.startswith('口座振替 ミツイスミトモカード'):
        raise ValueError(f"ID {idx}: ミツイスミトモカード — set override to AMAZON_MC or ANA_SFC")

    if desc.startswith('モバイルレジ（コウキン）'):
        return (FIXED_ASSETS_TAX, 'Tokyo')

    if desc.startswith('取消 モバイルレジ（コウキン）'):
        return (FIXED_ASSETS_TAX, 'Tokyo')

    if desc.startswith('ヨツヤゼイムシヨ'):
        return (INCOME_TAX, 'Japan')

    # Currency transfers handled specially in SQL generation
    if currency == 'JPY' and desc.startswith('普通 米ドル'):
        return (USD_ACCT, None)
    if currency == 'USD' and desc.startswith('普通 円'):
        return 'CURRENCY_TRANSFER'

    raise ValueError(f"ID {idx}: Unknown pattern [{currency}] {desc}")


def build_currency_transfer_map(transactions):
    """Map dates to USD amounts for currency transfers."""
    usd_map = {}
    for tx in transactions:
        if tx['currency'] == 'USD' and tx['desc'].startswith('普通 円'):
            usd_map.setdefault(tx['date'], []).append(tx['amount'])
    return usd_map


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Ccy':<4} {'Statement':<35} {'Desc':<15} {'Transfer':<40} {'Increase':>12} {'Decrease':>12}")
    print('-' * 140)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if is_skip(tx):
            continue
        info = get_transaction_info(idx, tx)
        if info == 'CURRENCY_TRANSFER':
            continue  # USD side shown with JPY side

        if prev_date and prev_date != tx['date']:
            print('-' * 140)
        prev_date = tx['date']

        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        date_str = f"{tx['date']} {weekday[tx['date'].weekday()]}"
        sym = '$' if tx['currency'] == 'USD' else '¥'
        denom = CURRENCY_DENOM[tx['currency']]

        if isinstance(info, list):
            # Split transaction
            for i, (acct, amt, desc) in enumerate(info):
                transfer = ACCOUNT_NAMES.get(acct, acct or '')
                if denom == 1:
                    inc = f"{sym}{int(amt):,}" if amt > 0 else ''
                    dec = f"{sym}{int(abs(amt)):,}" if amt < 0 else ''
                else:
                    inc = f"{sym}{amt:,.2f}" if amt > 0 else ''
                    dec = f"{sym}{abs(amt):,.2f}" if amt < 0 else ''
                prefix = f"{idx:<4} {date_str:<14} {tx['currency']:<4} {tx['desc']:<35}" if i == 0 else f"{'':4} {'':14} {'':4} {'  (split)':35}"
                print(f"{prefix} {desc or '':15} {transfer:<40} {inc:>12} {dec:>12}")
        else:
            account, description = info
            transfer = ACCOUNT_NAMES.get(account, account or '')
            if denom == 1:
                inc = f"{sym}{int(tx['amount']):,}" if tx['amount'] > 0 else ''
                dec = f"{sym}{int(abs(tx['amount'])):,}" if tx['amount'] < 0 else ''
            else:
                inc = f"{sym}{tx['amount']:,.2f}" if tx['amount'] > 0 else ''
                dec = f"{sym}{abs(tx['amount']):,.2f}" if tx['amount'] < 0 else ''
            print(f"{idx:<4} {date_str:<14} {tx['currency']:<4} {tx['desc']:<35} {description or '':15} {transfer:<40} {inc:>12} {dec:>12}")


def output_sql(transactions):
    print('BEGIN;')
    print()
    usd_map = build_currency_transfer_map(transactions)
    total = len([tx for tx in transactions if not is_skip(tx) and not (tx['currency'] == 'USD' and tx['desc'].startswith('普通 円'))])
    seq = 0
    for idx, tx in enumerate(transactions, 1):
        if is_skip(tx):
            continue
        info = get_transaction_info(idx, tx)
        if info == 'CURRENCY_TRANSFER':
            continue

        seq += 1
        currency = tx['currency']
        currency_guid = CURRENCIES[currency]
        denom = CURRENCY_DENOM[currency]
        source = SOURCE_ACCOUNTS[currency]
        reverse_idx = total - seq + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date']} 00:{minutes:02d}:{seconds:02d}"
        tx_guid = uuid.uuid4().hex

        if isinstance(info, list):
            # Split transaction: one source split, multiple target splits
            desc_sql = f"'{info[0][2]}'" if info[0][2] else 'NULL'
            total_amount = sum(a for _, a, _ in info)
            value_num = round(total_amount * denom)
            print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
            print(f"VALUES ('{tx_guid}', '{currency_guid}', '', '{date_str}', NOW(), {desc_sql});")
            s_guid = uuid.uuid4().hex
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s_guid}', '{tx_guid}', '{source}', '', '', 'n', NULL, {value_num}, {denom}, {value_num}, {denom}, NULL);")
            for acct, amt, _ in info:
                s_guid = uuid.uuid4().hex
                v = round(amt * denom)
                print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
                print(f"VALUES ('{s_guid}', '{tx_guid}', '{acct}', '', '', 'n', NULL, {-v}, {denom}, {-v}, {denom}, NULL);")
            print()
            continue

        account, description = info
        desc_sql = f"'{description}'" if description else 'NULL'
        value_num = round(tx['amount'] * denom)

        # Multi-currency transfer (JPY -> USD)
        if account == USD_ACCT and currency == 'JPY':
            usd_amounts = usd_map.get(tx['date'], [])
            if not usd_amounts:
                raise ValueError(f"ID {idx}: No matching USD entry for currency transfer on {tx['date']}")
            usd_amount = usd_amounts.pop(0)
            usd_value = round(abs(usd_amount) * CURRENCY_DENOM['USD'])
            jpy_value = abs(value_num)
            # Determine direction: JPY withdrawal = buying USD, JPY deposit = selling USD
            if tx['amount'] < 0:
                # Buying USD: JPY decreases, USD increases
                jpy_sign, usd_sign = -1, 1
            else:
                # Selling USD: JPY increases, USD decreases
                jpy_sign, usd_sign = 1, -1
            print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
            print(f"VALUES ('{tx_guid}', '{CURRENCIES['JPY']}', '', '{date_str}', NOW(), {desc_sql});")
            s1 = uuid.uuid4().hex
            s2 = uuid.uuid4().hex
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s1}', '{tx_guid}', '{source}', '', '', 'n', NULL, {jpy_sign * jpy_value}, 1, {jpy_sign * jpy_value}, 1, NULL);")
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s2}', '{tx_guid}', '{USD_ACCT}', '', '', 'n', NULL, {-jpy_sign * jpy_value}, 1, {usd_sign * usd_value}, 100, NULL);")
            print()
            continue

        s1_guid = uuid.uuid4().hex
        s2_guid = uuid.uuid4().hex
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
        print('Usage: python3 d_neobank_import.py [review|sql]', file=sys.stderr)
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
