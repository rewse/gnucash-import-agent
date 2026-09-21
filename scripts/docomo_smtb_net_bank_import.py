#!/usr/bin/env python3
"""DOCOMO SMTB Net Bank Statement Importer

Usage:
1. Paste tab-separated data into RAW_DATA (CURRENCY, DATE, DESC, WITHDRAWAL, DEPOSIT)
2. Set MANUAL_OVERRIDES for any transactions that need custom accounts/descriptions
3. Run: python3 scripts/docomo_smtb_net_bank_import.py review
4. Run: python3 scripts/docomo_smtb_net_bank_import.py sql
"""
import json
import math
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


PERSONAL_FILE = PROJECT_ROOT / ".kiro/skills/gnucash-import/references/personal.json"


def _personal_error(key):
    suffix = "" if key == "personal.json" else f" {key}"
    return f"DOCOMO SMTB Net Bank: malformed personal.json{suffix}"


def _is_nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def _is_safe_personal_pattern(value):
    if not _is_nonempty_string(value):
        return False
    normalized = "".join(value.split())
    markers = ("ことら送金", "振込＊", "振込")
    identity = normalized
    for marker in markers:
        if normalized.startswith(marker):
            identity = normalized[len(marker):]
            break
    return len(identity) >= 3 and not any(identity in marker for marker in markers)


def _is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def load_personal_rules(source_name):
    if not PERSONAL_FILE.exists():
        return {}, None
    try:
        with open(PERSONAL_FILE) as personal_file:
            settings = json.load(personal_file)
    except (OSError, json.JSONDecodeError):
        return {}, _personal_error("personal.json")
    if not isinstance(settings, dict):
        return {}, _personal_error("personal.json")
    transfer_rules = settings.get("transfer_rules", {})
    if not isinstance(transfer_rules, dict):
        return {}, _personal_error("transfer_rules")
    rules = transfer_rules.get(source_name, {})
    source_key = f"transfer_rules.{source_name}"
    if not isinstance(rules, dict):
        return {}, _personal_error(source_key)

    schemas = {
        "family_deposit": {
            "account", "amount", "description", "pattern", "withdrawal_account"
        },
        "family_split": {"amount", "description", "pattern", "splits"},
        "friend_transfer": {"account", "pattern"},
        "self_transfer": {"account", "pattern"},
    }
    resolved = {}
    for rule_name, configured_rule in rules.items():
        key_prefix = f"{source_key}.{rule_name}"
        if rule_name not in schemas:
            return {}, _personal_error(key_prefix)
        if not isinstance(configured_rule, dict):
            return {}, _personal_error(key_prefix)
        expected_fields = schemas[rule_name]
        unexpected_fields = set(configured_rule) - expected_fields
        if unexpected_fields:
            field = sorted(unexpected_fields)[0]
            return {}, _personal_error(f"{key_prefix}.{field}")
        missing_fields = expected_fields - set(configured_rule)
        if missing_fields:
            field = sorted(missing_fields)[0]
            return {}, _personal_error(f"{key_prefix}.{field}")
        if not _is_safe_personal_pattern(configured_rule["pattern"]):
            return {}, _personal_error(f"{key_prefix}.pattern")

        rule = dict(configured_rule)
        if rule_name in ("family_deposit", "friend_transfer", "self_transfer"):
            account_fields = ["account"]
            if rule_name == "family_deposit":
                account_fields.append("withdrawal_account")
            for field in account_fields:
                if not _is_nonempty_string(rule[field]):
                    return {}, _personal_error(f"{key_prefix}.{field}")
                rule[field] = get_guid(rule[field])
                if rule[field] is None:
                    return {}, _personal_error(f"{key_prefix}.{field}")
        if rule_name in ("family_deposit", "family_split"):
            if not _is_number(rule["amount"]):
                return {}, _personal_error(f"{key_prefix}.amount")
            if not _is_nonempty_string(rule["description"]):
                return {}, _personal_error(f"{key_prefix}.description")
        if rule_name == "family_split":
            splits = rule["splits"]
            if not isinstance(splits, list) or not splits:
                return {}, _personal_error(f"{key_prefix}.splits")
            resolved_splits = []
            for index, split in enumerate(splits):
                split_key = f"{key_prefix}.splits.{index}"
                if not isinstance(split, dict):
                    return {}, _personal_error(split_key)
                unexpected_fields = set(split) - {"account", "amount"}
                if unexpected_fields:
                    field = sorted(unexpected_fields)[0]
                    return {}, _personal_error(f"{split_key}.{field}")
                for field in ("account", "amount"):
                    if field not in split:
                        return {}, _personal_error(f"{split_key}.{field}")
                if not _is_nonempty_string(split["account"]):
                    return {}, _personal_error(f"{split_key}.account")
                if not _is_number(split["amount"]):
                    return {}, _personal_error(f"{split_key}.amount")
                account = get_guid(split["account"])
                if account is None:
                    return {}, _personal_error(f"{split_key}.account")
                resolved_splits.append({"account": account, "amount": split["amount"]})
            if sum(split["amount"] for split in resolved_splits) != rule["amount"]:
                return {}, _personal_error(f"{key_prefix}.splits")
            rule["splits"] = resolved_splits
        resolved[rule_name] = rule
    return resolved, None


PERSONAL_RULES, PERSONAL_RULE_ERROR = load_personal_rules("docomo_smtb_net_bank")


# Source accounts
SOURCE_ACCOUNTS = {
    'JPY': get_guid('Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank'),
    'USD': get_guid('Assets:USD - Current Assets:Banks:DOCOMO SMTB Net Bank'),
}

# Transfer accounts






NATIONAL_ALLOWANCE = get_guid('Income:National Allowance')
REIMBURSEMENT_AWS = get_guid('Assets:JPY - Current Assets:Reimbursement:AWS Japan')
TOKYU_CARD = get_guid('Liabilities:Credit Card:TOKYU CARD ClubQ JMB')
AMAZON_MC = get_guid('Liabilities:Credit Card:Amazon MasterCard Gold')
ANA_SFC = get_guid('Liabilities:Credit Card:ANA Super Flyers Gold Card')
PAYPAY_CARD = get_guid('Liabilities:Credit Card:PayPay Card JCB')
LUXURY_CARD = get_guid('Liabilities:Credit Card:Luxury Card Mastercard Titanium')
GOLD_POINT = get_guid('Liabilities:Credit Card:GOLD POINT CARD +')
RESERVED_ACCT = get_guid('Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Reserved Account')
LONGTERM_ACCT = get_guid('Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Longterm Account')
RETIREMENT_ACCT = get_guid('Assets:JPY - Current Assets:Banks:DOCOMO SMTB Net Bank:Retirement Account')
USD_ACCT = get_guid('Assets:USD - Current Assets:Banks:DOCOMO SMTB Net Bank')
INCOME_TAX = get_guid('Expenses:Tax:Income Tax')
FIXED_ASSETS_TAX = get_guid('Expenses:Tax:Fixed Assets Tax')
INTEREST_INCOME = get_guid('Income:Interest Income')

CURRENCIES = {
    'JPY': 'a77d4ee821e04f02bb7429e437c645e4',
    'USD': '327c5a1bcfb147ceba2370ee17093159',
}
CURRENCY_DENOM = {'JPY': 1, 'USD': 100}

ACCOUNT_NAMES = {






    NATIONAL_ALLOWANCE: 'Income:National Allowance',
    REIMBURSEMENT_AWS: 'Assets:Reimbursement:AWS Japan',
    TOKYU_CARD: 'Liabilities:TOKYU CARD',
    AMAZON_MC: 'Liabilities:Amazon MasterCard Gold',
    ANA_SFC: 'Liabilities:ANA Super Flyers Gold',
    PAYPAY_CARD: 'Liabilities:PayPay Card JCB',
    LUXURY_CARD: 'Liabilities:Luxury Card Titanium',
    GOLD_POINT: 'Liabilities:GOLD POINT CARD +',
    RESERVED_ACCT: 'DOCOMO SMTB Net Bank:Reserved Account',
    LONGTERM_ACCT: 'DOCOMO SMTB Net Bank:Longterm Account',
    RETIREMENT_ACCT: 'DOCOMO SMTB Net Bank:Retirement Account',
    USD_ACCT: 'DOCOMO SMTB Net Bank (USD)',
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


def sql_string(value):
    if not value:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def parse_transactions(raw_data):
    transactions = []
    for line in raw_data.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        currency = parts[0].strip()
        y, m, d = parts[1].strip().split('/')
        # Normalize full-width space to half-width for pattern matching
        desc = parts[2].strip().replace('\u3000', ' ')
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
    for rule_name in ("family_deposit", "family_split", "friend_transfer", "self_transfer"):
        rule = PERSONAL_RULES.get(rule_name)
        if not rule:
            continue
        pattern = rule.get("pattern")
        if not isinstance(pattern, str) or not desc.startswith(pattern):
            continue
        key_prefix = f"transfer_rules.docomo_smtb_net_bank.{rule_name}"
        if rule_name == "family_deposit":
            if amount < 0:
                return rule["withdrawal_account"], rule["description"]
            if amount != rule["amount"]:
                raise ValueError(f"DOCOMO SMTB Net Bank: invalid {key_prefix}.amount")
            return rule["account"], rule["description"]
        if rule_name == "family_split":
            splits = rule.get("splits", [])
            if amount != rule.get("amount"):
                raise ValueError(f"DOCOMO SMTB Net Bank: invalid {key_prefix}.amount")
            if sum(split.get("amount", 0) for split in splits) != amount:
                raise ValueError(f"DOCOMO SMTB Net Bank: split amounts do not sum to transaction amount in {key_prefix}")
            if not isinstance(rule.get("description"), str) or any(split.get("account") is None for split in splits):
                raise ValueError(f"DOCOMO SMTB Net Bank: malformed personal.json {key_prefix}")
            return [(split["account"], split["amount"], rule["description"]) for split in splits]
        if rule.get("account") is None:
            raise ValueError(f"DOCOMO SMTB Net Bank: malformed personal.json {key_prefix}.account")
        return rule["account"], None

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

    if desc.startswith("振込＊"):
        if PERSONAL_RULE_ERROR:
            raise ValueError(PERSONAL_RULE_ERROR)
        raise ValueError(
            "DOCOMO SMTB Net Bank: missing personal.json transfer_rules.docomo_smtb_net_bank"
        )
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
            desc_sql = sql_string(info[0][2])
            total_amount = sum(a for _, a, _ in info)
            value_num = round(total_amount * denom)
            print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
            print(f"VALUES ('{tx_guid}', '{currency_guid}', '', '{date_str}', NOW(), {desc_sql});")
            s_guid = uuid.uuid4().hex
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s_guid}', '{tx_guid}', '{source}', '', '', 'c', NULL, {value_num}, {denom}, {value_num}, {denom}, NULL);")
            for acct, amt, _ in info:
                s_guid = uuid.uuid4().hex
                v = round(amt * denom)
                print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
                print(f"VALUES ('{s_guid}', '{tx_guid}', '{acct}', '', '', 'c', NULL, {-v}, {denom}, {-v}, {denom}, NULL);")
            print()
            continue

        account, description = info
        desc_sql = sql_string(description)
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
            print(f"VALUES ('{s1}', '{tx_guid}', '{source}', '', '', 'c', NULL, {jpy_sign * jpy_value}, 1, {jpy_sign * jpy_value}, 1, NULL);")
            print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
            print(f"VALUES ('{s2}', '{tx_guid}', '{USD_ACCT}', '', '', 'c', NULL, {-jpy_sign * jpy_value}, 1, {usd_sign * usd_value}, 100, NULL);")
            print()
            continue

        s1_guid = uuid.uuid4().hex
        s2_guid = uuid.uuid4().hex
        print(f"INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)")
        print(f"VALUES ('{tx_guid}', '{currency_guid}', '', '{date_str}', NOW(), {desc_sql});")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s1_guid}', '{tx_guid}', '{source}', '', '', 'c', NULL, {value_num}, {denom}, {value_num}, {denom}, NULL);")
        print(f"INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)")
        print(f"VALUES ('{s2_guid}', '{tx_guid}', '{account}', '', '', 'c', NULL, {-value_num}, {denom}, {-value_num}, {denom}, NULL);")
        print()

    print('COMMIT;')


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('review', 'sql'):
        print('Usage: python3 docomo_smtb_net_bank_import.py [review|sql]', file=sys.stderr)
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
