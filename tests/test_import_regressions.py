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
    def _import_script(
        self,
        source_slug: str,
        personal: dict[str, Any] | None = None,
        extra_accounts: set[str] | None = None,
    ):
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
        paths.update(extra_accounts or set())
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

    def test_sbi_securities_usd_cash_ignores_non_usd_rows(self):
        module = self._import_script("sbi_securities")
        fields = [
            "2026/09/01",
            "入金",
            "分配金",
            "米ドル",
            "QQQ 銘柄名:EXAMPLE",
            "-",
            "12.34",
            "2026/09/02",
            "出金",
            "-",
            "-",
            "入出金振替",
            "999,999",
            "-",
        ]

        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                transactions = module.parse_usd_cash(
                    (newline * 2).join(fields)
                )

                self.assertEqual(1, len(transactions))
                self.assertEqual(12.34, transactions[0]["amount"])
                self.assertEqual("分配金", transactions[0]["category"])

    def test_sompo_japan_dc_maps_old_and_new_fund_names_to_current_account(self):
        expected = (
            "Assets:JPY - Current Assets:Securities:Sompo Japan DC Securities:"
            "One Japan Stock Index Fund <DC Pension>"
        )
        module = self._import_script(
            "sompo_japan_dc", extra_accounts={expected}
        )
        expected_guid = module.get_guid(expected)
        self.assertIsNotNone(expected_guid)

        for fund_name in (
            "ＤＩＡＭ国内株式インデックス",
            "Ｏｎｅ国内株式インデックス",
        ):
            with self.subTest(fund_name=fund_name):
                transaction = module.parse_transactions(
                    "2026/09/01\t2026/09/02\t"
                    f"{fund_name}\t500\t7.7000\t3,850\t買 掛金"
                )[0]
                self.assertEqual(
                    (expected_guid, None),
                    module.get_transaction_info(1, transaction),
                )

    def test_lumine_confirmed_csv_skips_refunded_and_note_rows(self):
        module = self._import_script("lumine_card")
        raw = "\n".join(
            [
                "ご利用年月日,ご利用箇所,ご利用額,払戻額,ご請求額（うち手数料・利息）,支払区分（回数）,今回回数,今回ご請求額・弁済金（うち手数料・利息）,現地通貨額,通貨略称,換算レート",
                '2099/07/30,えきねっと,"1,111","1,111",0,１回払,,0,,   ,',
                '2099/07/30,えきねっと,"1,111",,"1,111",１回払,,"1,111",,   ,',
                '2099/07/30,えきねっと,"-1,111",,0,,,0,,   ,',
                '2099/07/30,えきねっと,"1,111",2099/07/30,えきねっと,"1,111",0,払戻しの場合は、ご相殺いたします。',
            ]
        )
        transactions = module.parse_transactions(raw)
        self.assertEqual([tx["amount"] for tx in transactions], [-1111])

    def test_ana_confirmed_fee_rows_use_pay_amount(self):
        module = self._import_script("ana_super_flyers_gold_card")
        raw = "\n".join(
            [
                "\t99/05/24\tEXAMPLE BANK (BANGKOK )\t11,111\t１\t１\t\t６月　１日繰上返済期間　８日利息　８日分\t",
                "\t99/05/24\tＡＴＭ利用手数料　海外キャッシング\t\t\t\t220\t\t",
                "\t99/06/15\tゴールドカード年会費\t\t\t\t3,333\t（うち消費税等３０３円）\t",
                "#\t99/05/26\tMRT-BEM (BANGKOK )\t172\t１\t１\t172\t34.00\tTHB\t5.0711\t05 27\t◎",
            ]
        )
        transactions = module.parse_transactions(raw)
        self.assertEqual(
            [tx["amount"] for tx in transactions], [-11111, -220, -3333, -172]
        )
        self.assertEqual(transactions[3]["remarks"], "34.00 THB")

    def test_amazon_mastercard_maps_revolut_top_up(self):
        module = self._import_script("amazon_mastercard_gold")
        raw = "\t99/08/03\tＲ　　　　　　＊＊９９９９＊\t1,234\t１\t１\t1,234\t\t"
        transactions = module.parse_transactions(raw)
        self.assertEqual(
            module.get_transaction_info(1, transactions[0]), (module.REVOLUT, None)
        )

    def test_sbi_shinsei_usd_rows_use_jpy_quantity_for_jpy_accounts(self):
        module = self._import_script("sbi_shinsei_bank")
        raw = "USD\t2099/09/01\t税引前利息\t\t4.79\nUSD\t2099/09/18\t円普通預金\t100.00\t"
        transactions = module.parse_transactions(raw)
        module.JPY_QUANTITIES = {1: 765, 2: 15692}
        output = StringIO()
        with redirect_stdout(output):
            module.output_sql(transactions)
        sql = output.getvalue()
        self.assertIn(", 'c', NULL, -479, 100, -765, 1, NULL);", sql)
        self.assertIn(", 'c', NULL, 10000, 100, 15692, 1, NULL);", sql)
        module.JPY_QUANTITIES = {}
        with self.assertRaises(ValueError), redirect_stdout(StringIO()):
            module.output_sql(transactions)

    def test_luxury_kddi_landline_absorbs_variable_amount(self):
        module = self._import_script("luxury_card_mastercard_titanium")
        splits = module.kddi_splits(5846)
        self.assertEqual([amount for _, amount, _ in splits], [4454, 1392])
        with self.assertRaises(ValueError):
            module.kddi_splits(4000)

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
