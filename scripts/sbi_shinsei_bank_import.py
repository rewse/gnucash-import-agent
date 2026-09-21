#!/usr/bin/env python3
"""SBI Shinsei Bank Statement Importer

Usage:
1. Paste tab-separated data into RAW_DATA (ACCOUNT_TYPE, DATE, DESC, WITHDRAWAL, DEPOSIT)
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 scripts/sbi_shinsei_bank_import.py review
4. Run: python3 scripts/sbi_shinsei_bank_import.py sql
"""
import json
import os
import sys
import uuid
from datetime import date
from pathlib import Path

def find_project_root():
    configured_root = os.environ.get("GNUCASH_IMPORT_ROOT")
    candidates = [Path(configured_root)] if configured_root else []
    candidates.extend([Path.cwd(), Path(__file__).resolve().parent.parent])
    for candidate in candidates:
        if (candidate / ".kiro/skills/gnucash-import").is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot find the repository root. Run from the repository root or set GNUCASH_IMPORT_ROOT."
    )


PROJECT_ROOT = find_project_root()
ACCOUNTS_FILE = PROJECT_ROOT / ".kiro/skills/gnucash-import/references/account-guid-cache.json"


def load_accounts():
    with open(ACCOUNTS_FILE) as account_file:
        data = json.load(account_file)
    raw_accounts = data.get("accounts") if isinstance(data, dict) else None
    if not isinstance(raw_accounts, dict):
        raise ValueError("Malformed account GUID cache.")
    accounts = {}
    for path, value in raw_accounts.items():
        if (
            not isinstance(path, str)
            or not isinstance(value, str)
            or len(value) != 32
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("Malformed account GUID cache.")
        accounts[path.replace("Root Account:", "")] = value
    return accounts


ACCOUNTS = load_accounts()


def get_guid(path):
    return ACCOUNTS.get(path) or ACCOUNTS.get('Root Account:' + path)


SOURCE_ACCOUNTS = {
    'JPY': get_guid('Assets:JPY - Current Assets:Banks:SBI Shinsei Bank'),
    'HYPER': get_guid('Assets:JPY - Current Assets:Banks:SBI Shinsei Bank:SBI Hyper Deposit'),
    'USD': get_guid('Assets:USD - Current Assets:Banks:SBI Shinsei Bank'),
}
INCOME_TAX = get_guid('Expenses:Tax:Income Tax')
INTEREST_INCOME = get_guid('Income:Interest Income')
FEES = get_guid('Expenses:Fees')
CASH = get_guid('Assets:JPY - Current Assets:Cash')
SBI_SEC = get_guid('Assets:JPY - Current Assets:Securities:SBI Securities')
SHINSEI_JPY = SOURCE_ACCOUNTS['JPY']
SHINSEI_TIME_DEPOSIT = get_guid('Assets:JPY - Current Assets:Banks:SBI Shinsei Bank:Saving Account')
DOCOMO_SMTB = get_guid('Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank')
LUXURY_CARD = get_guid('Liabilities:Credit Card:Luxury Card Mastercard Titanium')
CASH_BACK = get_guid('Income:Cash Back')
MORGAN_STANLEY_USD = get_guid('Assets:USD - Current Assets:Securities:Morgan Stanley')

CURRENCIES = {
    'JPY': 'a77d4ee821e04f02bb7429e437c645e4',
    'USD': '327c5a1bcfb147ceba2370ee17093159',
}
CURRENCY_DENOM = {'JPY': 1, 'USD': 100}

ACCOUNT_NAMES = {
    INCOME_TAX: 'Expenses:Tax:Income Tax',
    INTEREST_INCOME: 'Income:Interest Income',
    FEES: 'Expenses:Fees',
    CASH: 'Assets:Cash',
    SBI_SEC: 'Assets:Securities:SBI Securities',
    SHINSEI_JPY: 'Assets:Banks:SBI Shinsei Bank (JPY)',
    SHINSEI_TIME_DEPOSIT: 'Assets:Banks:SBI Shinsei Bank:Saving Account',
    DOCOMO_SMTB: 'Assets:Banks:DOCOMO SMTB Net Bank',
    LUXURY_CARD: 'Liabilities:Credit Card:Luxury Card',
    CASH_BACK: 'Income:Cash Back',
    MORGAN_STANLEY_USD: 'Assets:USD - Securities:Morgan Stanley',
}

# Mapping: (account_type, pattern) -> (account_guid, description)
RULES = {
    ('JPY', 'ATM 現金出金（提携取引）'): (CASH, None),
    ('JPY', '地方税'): (INCOME_TAX, 'Tokyo'),
    ('JPY', '国税'): (INCOME_TAX, 'Japan'),
    ('JPY', '税引前利息'): (INTEREST_INCOME, 'SBI Shinsei Bank'),
    ('HYPER', 'SBI証券精算'): (SBI_SEC, None),
    ('HYPER', '円普通預金'): (SHINSEI_JPY, None),
    ('HYPER', '地方税'): (INCOME_TAX, 'Tokyo'),
    ('HYPER', '国税'): (INCOME_TAX, 'Japan'),
    ('HYPER', '税引前利息'): (INTEREST_INCOME, 'SBI Shinsei Bank'),
    ('USD', '円普通預金'): (SHINSEI_JPY, None),
    ('USD', '地方税'): (INCOME_TAX, 'Tokyo'),
    ('USD', '国税'): (INCOME_TAX, 'Japan'),
    ('USD', '税引前利息'): (INTEREST_INCOME, 'SBI Shinsei Bank'),
    ('USD', '被仕向事務手数料'): (FEES, 'SBI Shinsei Bank'),
    ('USD', '外為送金'): (MORGAN_STANLEY_USD, 'Morgan Stanley'),
    ('JPY', '振込手数料'): (FEES, 'SBI Shinsei Bank'),
    ('JPY', '振込 ｶ) ｱﾌﾟﾗｽ'): (LUXURY_CARD, None),
    ('JPY', 'ｼﾖｳｶｲｷﾔﾝﾍﾟ-ﾝ'): (CASH_BACK, 'Referral Campaign'),
    # Counter side comes from SPLIT_OVERRIDES
    ('JPY', '満期解約 パワーダイレクト円定期100'): (None, None),
}

# Transactions whose counter side needs more than one split.
# ID -> [(account_guid, amount), ...]; amounts must sum to the statement amount.
# 満期解約 credits principal plus interest after withholding, e.g.
#   3: [(SHINSEI_TIME_DEPOSIT, 1000000), (INTEREST_INCOME, 3162)]
SPLIT_OVERRIDES = {}

# ============================================================
# EDIT BELOW: Paste raw data
# ============================================================
RAW_DATA = """
"""

# ============================================================
# EDIT BELOW: Manual overrides by ID (1-based)
# Format: ID: (ACCOUNT_GUID, 'Description') or ID: (ACCOUNT_GUID, None)
# ============================================================
MANUAL_OVERRIDES = {
}


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        acct_type = parts[0].strip()
        y, m, d = parts[1].strip().split('/')
        desc = parts[2].strip()
        withdrawal = float(parts[3].strip()) if parts[3].strip() else 0
        deposit = float(parts[4].strip()) if len(parts) > 4 and parts[4].strip() else 0
        currency = 'USD' if acct_type == 'USD' else 'JPY'
        transactions.append({
            'date': date(int(y), int(m), int(d)),
            'desc': desc,
            'acct_type': acct_type,
            'currency': currency,
            'amount': deposit - withdrawal,
        })
    return transactions


def get_transaction_info(idx, tx):
    if idx in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[idx]
    key = (tx['acct_type'], tx['desc'])
    if key in RULES:
        return RULES[key]
    raise ValueError(f"Unknown transaction type at ID {idx}: [{tx['acct_type']}] {tx['desc']}")


def get_counter_splits(idx, tx):
    """Return the counter side as a list of (account_guid, amount)."""
    if idx in SPLIT_OVERRIDES:
        splits = SPLIT_OVERRIDES[idx]
        total = sum(a for _, a in splits)
        if round(total, 2) != round(tx['amount'], 2):
            raise ValueError(f"Split total {total} != statement amount {tx['amount']} at ID {idx}")
        return splits
    account, _ = get_transaction_info(idx, tx)
    if account is None:
        raise ValueError(f"ID {idx} needs an entry in SPLIT_OVERRIDES")
    return [(account, tx['amount'])]


def output_review(transactions):
    print(f"{'ID':<4} {'Date':<14} {'Type':<6} {'Statement':<30} {'Desc':<20} {'Transfer':<40} {'Increase':>12} {'Decrease':>12}")
    print('-' * 140)
    prev_date = None
    for idx, tx in enumerate(transactions, 1):
        if prev_date and prev_date != tx['date']:
            print('-' * 140)
        prev_date = tx['date']
        account, description = get_transaction_info(idx, tx)
        splits = get_counter_splits(idx, tx)
        weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        date_str = f"{tx['date']} {weekday[tx['date'].weekday()]}"
        transfer = ACCOUNT_NAMES.get(account, account or '') if len(splits) == 1 else ''
        desc_str = description or ''
        if tx['currency'] == 'USD':
            inc = f"${tx['amount']:,.2f}" if tx['amount'] > 0 else ''
            dec = f"${abs(tx['amount']):,.2f}" if tx['amount'] < 0 else ''
        else:
            inc = f"¥{int(tx['amount']):,}" if tx['amount'] > 0 else ''
            dec = f"¥{int(abs(tx['amount'])):,}" if tx['amount'] < 0 else ''
        print(f"{idx:<4} {date_str:<14} {tx['acct_type']:<6} {tx['desc']:<30} {desc_str:<20} {transfer:<40} {inc:>12} {dec:>12}")
        if len(splits) > 1:
            for sub, (acct, amt) in enumerate(splits, 1):
                sub_transfer = ACCOUNT_NAMES.get(acct, acct or '')
                sub_inc = f"¥{int(amt):,}" if amt > 0 else ''
                sub_dec = f"¥{int(abs(amt)):,}" if amt < 0 else ''
                print(f"{str(idx)+'-'+str(sub):<4} {'':<14} {'':<6} {'':<30} {'':<20} {sub_transfer:<40} {sub_inc:>12} {sub_dec:>12}")


def output_sql(transactions):
    print('BEGIN;')
    print()
    total = len(transactions)
    for idx, tx in enumerate(transactions, 1):
        account, description = get_transaction_info(idx, tx)
        counter_splits = get_counter_splits(idx, tx)
        currency = tx['currency']
        currency_guid = CURRENCIES[currency]
        denom = CURRENCY_DENOM[currency]
        source = SOURCE_ACCOUNTS[tx['acct_type']]
        value_num = round(tx['amount'] * denom)

        tx_guid = uuid.uuid4().hex
        s1_guid = uuid.uuid4().hex
        reverse_idx = total - idx + 1
        minutes, seconds = divmod(reverse_idx, 60)
        date_str = f"{tx['date']} 00:{minutes:02d}:{seconds:02d}"
        desc_sql = f"'{description.replace(chr(39), chr(39)*2)}'" if description else 'NULL'

        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{currency_guid}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s1_guid}', '{tx_guid}', '{source}', '', '', 'c', NULL, {value_num}, {denom}, {value_num}, {denom}, NULL);")
        for acct, amt in counter_splits:
            sn = round(amt * denom)
            sg = uuid.uuid4().hex
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{sg}', '{tx_guid}', '{acct}', '', '', 'c', NULL, {-sn}, {denom}, {-sn}, {denom}, NULL);")
        print()
    print('COMMIT;')


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('review', 'sql'):
        print('Usage: python3 sbi_shinsei_bank_import.py [review|sql]', file=sys.stderr)
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
