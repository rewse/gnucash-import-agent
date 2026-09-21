from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / ".kiro/skills/gnucash-import/scripts/validate_sql.py"
SOURCE = "1" * 32
TARGET = "2" * 32
CURRENCY = "3" * 32


def transaction_block(
    tx_guid: str,
    source_split_guid: str,
    target_split_guid: str,
    timestamp: str,
    amount: int,
    description: str = "'Amazon; -- order'",
) -> str:
    return f"""INSERT INTO transactions (guid, currency_guid, num, post_date, enter_date, description)
VALUES ('{tx_guid}', '{CURRENCY}', '', '{timestamp}', NOW(), {description});
INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)
VALUES ('{source_split_guid}', '{tx_guid}', '{SOURCE}', '', '', 'c', NULL, {amount}, 1, {amount}, 1, NULL);
INSERT INTO splits (guid, tx_guid, account_guid, memo, action, reconcile_state, reconcile_date, value_num, value_denom, quantity_num, quantity_denom, lot_guid)
VALUES ('{target_split_guid}', '{tx_guid}', '{TARGET}', '', '', 'c', NULL, {-amount}, 1, {-amount}, 1, NULL);"""


def valid_sql() -> str:
    block = transaction_block(
        "4" * 32,
        "5" * 32,
        "6" * 32,
        "2026-09-17 00:00:01",
        -100,
    )
    return f"BEGIN;\n{block}\nCOMMIT;\n"


class SqlValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("validate_sql", VALIDATOR)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load SQL validator")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_accepts_valid_generated_sql(self):
        result = self.module.validate_sql(
            valid_sql(), SOURCE, {SOURCE, TARGET}, CURRENCY
        )
        self.assertEqual(1, result.transaction_count)
        self.assertEqual(2, result.split_count)

    def test_rejects_forbidden_statement(self):
        sql = valid_sql().replace("BEGIN;", "BEGIN;\nDELETE FROM accounts;")
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_forbidden_statement_hidden_after_carriage_return(self):
        sql = valid_sql().replace(
            "BEGIN;", "BEGIN; -- hidden through carriage return\rDELETE FROM accounts;\n"
        )
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_invalid_boundary(self):
        sql = valid_sql().replace("BEGIN;", "SELECT 1;")
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_unbalanced_transaction(self):
        sql = valid_sql().replace("NULL, 100, 1, 100, 1", "NULL, 99, 1, 99, 1")
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_non_cleared_split(self):
        sql = valid_sql().replace("'', '', 'c', NULL", "'', '', 'n', NULL", 1)
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_non_ascii_description(self):
        sql = valid_sql().replace("'Amazon; -- order'", "'アマゾン'")
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_unknown_account(self):
        sql = valid_sql().replace(TARGET, "7" * 32)
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_missing_source_split(self):
        sql = valid_sql().replace(SOURCE, TARGET)
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_reversed_same_day_order(self):
        first = transaction_block(
            "4" * 32,
            "5" * 32,
            "6" * 32,
            "2026-09-17 00:00:01",
            -100,
        )
        second = transaction_block(
            "7" * 32,
            "8" * 32,
            "9" * 32,
            "2026-09-17 00:00:02",
            -200,
        )
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(
                f"BEGIN;\n{first}\n{second}\nCOMMIT;\n",
                SOURCE,
                {SOURCE, TARGET},
                CURRENCY,
            )

    def test_rejects_zero_quantity_for_nonzero_value(self):
        sql = valid_sql().replace("NULL, 100, 1, 100, 1", "NULL, 100, 1, 0, 1")
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_invalid_timestamp(self):
        sql = valid_sql().replace(
            "2026-09-17 00:00:01", "2026-99-99 99:99:99"
        )
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_description_backslash(self):
        sql = valid_sql().replace("Amazon; -- order", r"Amazon\\order")
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_rejects_unexpected_currency(self):
        sql = valid_sql().replace(CURRENCY, "f" * 32)
        with self.assertRaises(self.module.ValidationError):
            self.module.validate_sql(sql, SOURCE, {SOURCE, TARGET}, CURRENCY)

    def test_optimized_mode_is_rejected(self):
        completed = subprocess.run(
            [sys.executable, "-O", str(VALIDATOR), "--help"],
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(2, completed.returncode)
        self.assertNotIn("validated", completed.stdout.lower())


if __name__ == "__main__":
    unittest.main()
