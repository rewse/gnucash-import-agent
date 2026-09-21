from __future__ import annotations

import ast
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class ImportRegressionTest(unittest.TestCase):
    def _import_script(self, source_slug: str, personal: dict[str, Any] | None = None):
        script_path = SCRIPTS / f"{source_slug}_import.py"
        tree = ast.parse(script_path.read_text())
        paths = {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "get_guid"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        project_root = Path(temporary.name)
        references = project_root / ".kiro/skills/gnucash-import/references"
        references.mkdir(parents=True)
        accounts = {
            path: f"{index + 1:032x}" for index, path in enumerate(sorted(paths))
        }
        (references / "account-guid-cache.json").write_text(
            json.dumps({"accounts": accounts})
        )
        if personal is not None:
            (references / "personal.json").write_text(json.dumps(personal))
        spec = importlib.util.spec_from_file_location(
            f"regression_{source_slug}_{id(temporary)}", script_path
        )
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        with patch.dict(os.environ, {"GNUCASH_IMPORT_ROOT": str(project_root)}):
            spec.loader.exec_module(module)
        return module

    @staticmethod
    def _personal_settings() -> dict[str, Any]:
        return {
            "accounts": {
                "pasmo": {
                    "shopping": "Expenses:Foods:Dining",
                    "source": "Assets:JPY - Current Assets:Prepaid:PASMO Example",
                }
            },
            "nearest_station": "例駅A",
        }

    def test_amazon_gc_sql_preserves_same_day_source_order(self):
        module = self._import_script("amazon_gc")
        transactions = [
            {
                "date": datetime(2026, 9, 17),
                "desc": "Amazon.co.jpの注文に適用されたギフトカード 111",
                "total_amount": -100,
                "splits": [{"account": next(iter(module.ACCOUNTS)), "amount": -100}],
            },
            {
                "date": datetime(2026, 9, 17),
                "desc": "Amazon.co.jpの注文に適用されたギフトカード 222",
                "total_amount": -200,
                "splits": [{"account": next(iter(module.ACCOUNTS)), "amount": -200}],
            },
        ]
        output = StringIO()
        with redirect_stdout(output):
            module.output_sql(transactions)
        sql = output.getvalue()
        first_transaction = sql.index("-- Transaction 1:")
        first_timestamp = sql.index("2026-09-17 12:00:02")
        second_transaction = sql.index("-- Transaction 2:")
        second_timestamp = sql.index("2026-09-17 12:00:01")
        self.assertLess(first_transaction, first_timestamp)
        self.assertLess(first_timestamp, second_transaction)
        self.assertLess(second_transaction, second_timestamp)

    def test_suica_parses_bus_rows(self):
        module = self._import_script("suica", self._personal_settings())
        transaction = module.parse_transactions("08/26 ﾊﾞｽ等 都電都Ｂ -210")[0]
        self.assertEqual("ﾊﾞｽ等", transaction["type"])
        self.assertEqual("都電都Ｂ", transaction["station1"])
        self.assertEqual(-210, transaction["amount"])
        self.assertEqual(
            (module.TRANSIT_ACCOUNT, "Toei Bus"),
            module.get_transaction_info([transaction], 1, transaction),
        )
        self.assertEqual("バス 都電都Ｂ", module.get_purpose(transaction))

    def test_transit_company_detection_checks_both_endpoints(self):
        for source_slug in ("pasmo", "suica"):
            module = self._import_script(source_slug, self._personal_settings())
            for station1, station2 in (
                ("西新宿", "Example"),
                ("Example", "外苑前"),
                ("Example", "表参道"),
                ("Example", "例駅A"),
            ):
                with self.subTest(
                    source_slug=source_slug, station1=station1, station2=station2
                ):
                    self.assertEqual(
                        "Tokyo Metro",
                        module.get_railway_company(station1, station2),
                    )


if __name__ == "__main__":
    unittest.main()
