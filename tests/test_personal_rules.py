from __future__ import annotations
import ast
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class PersonalRulesTest(unittest.TestCase):
    _old_root: Optional[str] = None
    _temporary_directory: Any = None
    project_root = Path()

    def setUp(self):
        self._old_root = os.environ.get("GNUCASH_IMPORT_ROOT")
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.project_root = Path(self._temporary_directory.name)
        references = self.project_root / ".kiro/skills/gnucash-import/references"
        references.mkdir(parents=True)
        os.environ["GNUCASH_IMPORT_ROOT"] = str(self.project_root)

    def tearDown(self):
        if self._old_root is None:
            os.environ.pop("GNUCASH_IMPORT_ROOT", None)
        else:
            os.environ["GNUCASH_IMPORT_ROOT"] = self._old_root
        self._temporary_directory.cleanup()

    def _import_script(self, source_slug: str, personal: Any) -> Any:
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
        accounts = {
            path: f"{index + 10:032x}" for index, path in enumerate(sorted(paths))
        }
        accounts.update(
            {
                "Assets:Example": "1" * 32,
                "Assets:JPY - Current Assets:Banks:Example": "2" * 32,
                "Expenses:Example": "3" * 32,
                "Income:Example": "4" * 32,
            }
        )
        references = self.project_root / ".kiro/skills/gnucash-import/references"
        (references / "account-guid-cache.json").write_text(
            json.dumps({"accounts": accounts})
        )
        if personal is not None:
            content = personal if isinstance(personal, str) else json.dumps(personal)
            (references / "personal.json").write_text(content)

        spec = importlib.util.spec_from_file_location(
            f"test_{source_slug}_{id(self)}", script_path
        )
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(self.project_root, module.PROJECT_ROOT)
        return module

    @staticmethod
    def _personal_settings() -> dict[str, Any]:
        return {
            "accounts": {
                "pasmo": {
                    "shopping": "Assets:Example",
                    "source": "Assets:JPY - Current Assets:Banks:Example",
                }
            },
            "nearest_station": "Example Station",
            "transfer_rules": {
                "docomo_smtb_net_bank": {
                    "family_deposit": {
                        "account": "Income:Example",
                        "amount": 12345,
                        "description": "Family",
                        "pattern": "振込＊EXAMPLE A",
                        "withdrawal_account": "Assets:Example",
                    },
                    "family_split": {
                        "amount": -10000,
                        "description": "Family",
                        "pattern": "振込＊EXAMPLE B",
                        "splits": [
                            {"account": "Assets:Example", "amount": -6000},
                            {"account": "Expenses:Example", "amount": -4000},
                        ],
                    },
                    "friend_transfer": {
                        "account": "Assets:Example",
                        "pattern": "振込＊EXAMPLE C",
                    },
                    "self_transfer": {
                        "account": "Assets:JPY - Current Assets:Banks:Example",
                        "pattern": "振込＊EXAMPLE SELF",
                    },
                },
                "mufg_bank": {
                    "self_transfer": {
                        "account": "Assets:JPY - Current Assets:Banks:Example",
                        "contains": "EXAMPLE NAME",
                    }
                },
                "sony_bank": {
                    "self_transfer": {
                        "account": "Assets:JPY - Current Assets:Banks:Example",
                        "contains": "EXAMPLE NAME",
                    }
                },
            },
        }

    def test_docomo_configured_deposit_rule(self):
        module = self._import_script("docomo_smtb_net_bank", self._personal_settings())
        info = module.get_transaction_info(
            1, {"currency": "JPY", "desc": "振込＊EXAMPLE A", "amount": 12345}
        )
        self.assertEqual(("4" * 32, "Family"), info)

    def test_docomo_configured_split_rule(self):
        module = self._import_script("docomo_smtb_net_bank", self._personal_settings())
        info = module.get_transaction_info(
            1, {"currency": "JPY", "desc": "振込＊EXAMPLE B", "amount": -10000}
        )
        self.assertEqual(
            [
                ("1" * 32, -6000, "Family"),
                ("3" * 32, -4000, "Family"),
            ],
            info,
        )

    def test_docomo_rejects_split_total_mismatch(self):
        personal = self._personal_settings()
        personal["transfer_rules"]["docomo_smtb_net_bank"]["family_split"][
            "amount"
        ] = -9999
        module = self._import_script("docomo_smtb_net_bank", personal)
        with self.assertRaises(ValueError):
            module.get_transaction_info(
                1,
                {"currency": "JPY", "desc": "振込＊EXAMPLE B", "amount": -9999},
            )

    def test_mufg_configured_self_transfer(self):
        module = self._import_script("mufg_bank", self._personal_settings())
        info = module.get_transaction_info(
            1, {"desc": "振込 EXAMPLE NAME", "amount": 1000}
        )
        self.assertEqual(("2" * 32, None), info)

    def test_sony_configured_self_transfer(self):
        module = self._import_script("sony_bank", self._personal_settings())
        info = module.get_transaction_info(
            1,
            {"currency": "JPY", "desc": "振込 EXAMPLE NAME", "amount": 1000},
        )
        self.assertEqual(("2" * 32, None), info)

    def test_missing_personal_rule_is_not_guessed(self):
        module = self._import_script(
            "docomo_smtb_net_bank", {"nearest_station": "Example Station"}
        )
        with self.assertRaises(ValueError):
            module.get_transaction_info(
                1,
                {"currency": "JPY", "desc": "振込＊EXAMPLE A", "amount": 12345},
            )
    def test_mufg_missing_self_transfer_rule_is_not_guessed(self):
        module = self._import_script("mufg_bank", {"nearest_station": "Example Station"})
        with self.assertRaisesRegex(ValueError, "transfer_rules.mufg_bank.self_transfer"):
            module.get_transaction_info(
                1, {"desc": "振込 EXAMPLE NAME", "amount": 1000}
            )

    def test_sony_missing_self_transfer_rule_is_not_guessed(self):
        module = self._import_script("sony_bank", {"nearest_station": "Example Station"})
        with self.assertRaisesRegex(ValueError, "transfer_rules.sony_bank.self_transfer"):
            module.get_transaction_info(
                1,
                {"currency": "JPY", "desc": "振込 EXAMPLE NAME", "amount": 1000},
            )

    def test_docomo_preserves_direction_specific_family_rule(self):
        module = self._import_script("docomo_smtb_net_bank", self._personal_settings())
        self.assertEqual(
            ("1" * 32, "Family"),
            module.get_transaction_info(
                1, {"currency": "JPY", "desc": "振込＊EXAMPLE A", "amount": -5000}
            ),
        )
        with self.assertRaisesRegex(ValueError, "family_deposit.amount"):
            module.get_transaction_info(
                1, {"currency": "JPY", "desc": "振込＊EXAMPLE A", "amount": 9999}
            )

    def test_self_transfer_requires_source_marker(self):
        cases = (
            ("mufg_bank", {"desc": "CARD EXAMPLE NAME", "amount": -1000}),
            (
                "sony_bank",
                {"currency": "JPY", "desc": "CARD EXAMPLE NAME", "amount": -1000},
            ),
        )
        for source_slug, transaction in cases:
            with self.subTest(source_slug=source_slug):
                module = self._import_script(source_slug, self._personal_settings())
                with self.assertRaises(ValueError):
                    module.get_transaction_info(1, transaction)

    def test_malformed_source_rule_is_deferred_and_redacted(self):
        cases = (
            (
                "docomo_smtb_net_bank",
                {"currency": "JPY", "desc": "振込＊EXAMPLE UNKNOWN", "amount": 1},
                {"currency": "JPY", "desc": "振込＊ジドウテアテ", "amount": 1},
                "docomo_smtb_net_bank.family_deposit",
            ),
            (
                "mufg_bank",
                {"desc": "振込 EXAMPLE NAME", "amount": 1},
                {"desc": "利息", "amount": 1},
                "mufg_bank.self_transfer",
            ),
            (
                "sony_bank",
                {"currency": "JPY", "desc": "振込 EXAMPLE NAME", "amount": 1},
                {"currency": "JPY", "desc": "利息", "amount": 1},
                "sony_bank.self_transfer",
            ),
        )
        for source_slug, personal_tx, public_tx, expected_path in cases:
            with self.subTest(source_slug=source_slug):
                personal = self._personal_settings()
                personal["transfer_rules"][source_slug][next(iter(personal["transfer_rules"][source_slug]))] = "PRIVATE VALUE"
                module = self._import_script(source_slug, personal)
                module.get_transaction_info(1, public_tx)
                with self.assertRaises(ValueError) as caught:
                    module.get_transaction_info(1, personal_tx)
                message = str(caught.exception)
                self.assertIn(expected_path, message)
                self.assertNotIn("PRIVATE VALUE", message)

    def test_rejects_unknown_empty_whitespace_and_non_string_fields(self):
        mutations = (
            ("docomo_smtb_net_bank", "family_deposit", "pattern", ""),
            ("docomo_smtb_net_bank", "family_deposit", "pattern", "   "),
            ("docomo_smtb_net_bank", "family_deposit", "pattern", 7),
            ("docomo_smtb_net_bank", "family_deposit", "description", ""),
            ("docomo_smtb_net_bank", "family_deposit", "account", None),
            ("mufg_bank", "self_transfer", "contains", ""),
            ("mufg_bank", "self_transfer", "contains", "   "),
            ("sony_bank", "self_transfer", "contains", 7),
        )
        transactions = {
            "docomo_smtb_net_bank": {"currency": "JPY", "desc": "振込＊EXAMPLE A", "amount": 12345},
            "mufg_bank": {"desc": "振込 EXAMPLE NAME", "amount": 1000},
            "sony_bank": {"currency": "JPY", "desc": "振込 EXAMPLE NAME", "amount": 1000},
        }
        for source_slug, rule_name, field, invalid_value in mutations:
            with self.subTest(source_slug=source_slug, field=field, value_type=type(invalid_value).__name__):
                personal = self._personal_settings()
                personal["transfer_rules"][source_slug][rule_name][field] = invalid_value
                module = self._import_script(source_slug, personal)
                with self.assertRaisesRegex(
                    ValueError,
                    rf"transfer_rules\.{source_slug}\.{rule_name}\.{field}",
                ):
                    module.get_transaction_info(1, transactions[source_slug])

    def test_rejects_unknown_rule_and_rule_field(self):
        for source_slug in ("docomo_smtb_net_bank", "mufg_bank", "sony_bank"):
            with self.subTest(source_slug=source_slug, kind="rule"):
                personal = self._personal_settings()
                personal["transfer_rules"][source_slug]["unknown_rule"] = {}
                module = self._import_script(source_slug, personal)
                transaction = (
                    {"currency": "JPY", "desc": "振込＊UNKNOWN", "amount": 1}
                    if source_slug == "docomo_smtb_net_bank"
                    else {"currency": "JPY", "desc": "振込 UNKNOWN", "amount": 1}
                    if source_slug == "sony_bank"
                    else {"desc": "振込 UNKNOWN", "amount": 1}
                )
                with self.assertRaisesRegex(ValueError, rf"transfer_rules\.{source_slug}\.unknown_rule"):
                    module.get_transaction_info(1, transaction)
            with self.subTest(source_slug=source_slug, kind="field"):
                personal = self._personal_settings()
                rule_name = next(iter(personal["transfer_rules"][source_slug]))
                personal["transfer_rules"][source_slug][rule_name]["unknown_field"] = "PRIVATE VALUE"
                module = self._import_script(source_slug, personal)
                transaction = (
                    {"currency": "JPY", "desc": "振込＊UNKNOWN", "amount": 1}
                    if source_slug == "docomo_smtb_net_bank"
                    else {"currency": "JPY", "desc": "振込 UNKNOWN", "amount": 1}
                    if source_slug == "sony_bank"
                    else {"desc": "振込 UNKNOWN", "amount": 1}
                )
                with self.assertRaisesRegex(ValueError, rf"{rule_name}\.unknown_field"):
                    module.get_transaction_info(1, transaction)

    def test_rejects_malformed_splits_and_numeric_fields(self):
        mutations = (
            ("amount", True, "family_split.amount"),
            ("amount", float("nan"), "family_split.amount"),
            ("splits", [], "family_split.splits"),
            ("splits", "PRIVATE VALUE", "family_split.splits"),
            ("splits", [{"account": "Assets:Example", "amount": True}], "family_split.splits.0.amount"),
            ("splits", [{"account": "Assets:Example", "amount": -9999}], "family_split.splits"),
        )
        for field, invalid_value, expected_path in mutations:
            with self.subTest(field=field, value_type=type(invalid_value).__name__):
                personal = self._personal_settings()
                personal["transfer_rules"]["docomo_smtb_net_bank"]["family_split"][field] = invalid_value
                module = self._import_script("docomo_smtb_net_bank", personal)
                with self.assertRaisesRegex(ValueError, expected_path):
                    module.get_transaction_info(
                        1, {"currency": "JPY", "desc": "振込＊EXAMPLE B", "amount": -10000}
                    )

    def test_malformed_json_is_deferred_and_does_not_leak(self):
        malformed = '{"transfer_rules": "PRIVATE VALUE"'
        for source_slug in ("docomo_smtb_net_bank", "mufg_bank", "sony_bank"):
            with self.subTest(source_slug=source_slug):
                module = self._import_script(source_slug, malformed)
                transaction = (
                    {"currency": "JPY", "desc": "振込＊UNKNOWN", "amount": 1}
                    if source_slug == "docomo_smtb_net_bank"
                    else {"currency": "JPY", "desc": "振込 UNKNOWN", "amount": 1}
                    if source_slug == "sony_bank"
                    else {"desc": "振込 UNKNOWN", "amount": 1}
                )
                with self.assertRaises(ValueError) as caught:
                    module.get_transaction_info(1, transaction)
                self.assertIn(source_slug.split("_")[0].upper(), str(caught.exception).upper())
                self.assertIn("personal.json", str(caught.exception))
                self.assertNotIn("PRIVATE VALUE", str(caught.exception))

    def test_malformed_containers_are_source_specific_and_redacted(self):
        cases = (
            ({"transfer_rules": "PRIVATE VALUE"}, "transfer_rules"),
            ({"transfer_rules": {"mufg_bank": "PRIVATE VALUE"}}, "transfer_rules.mufg_bank"),
        )
        for personal, expected_path in cases:
            with self.subTest(expected_path=expected_path):
                module = self._import_script("mufg_bank", personal)
                with self.assertRaises(ValueError) as caught:
                    module.get_transaction_info(1, {"desc": "振込 UNKNOWN", "amount": 1})
                message = str(caught.exception)
                self.assertIn("MUFG Bank", message)
                self.assertIn(expected_path, message)
                self.assertNotIn("PRIVATE VALUE", message)

    def test_transit_scripts_reject_malformed_settings_without_leaking(self):
        for source_slug, operation, source_name in (
            ("pasmo", lambda module: module.get_railway_company("A", "B"), "Mobile PASMO"),
            ("suica", lambda module: module._init_business_pairs(), "Mobile Suica"),
        ):
            for personal in ('{"nearest_station": "PRIVATE VALUE"', {"nearest_station": 7}):
                with self.subTest(source_slug=source_slug, value_type=type(personal).__name__):
                    module = self._import_script(source_slug, personal)
                    with self.assertRaises(ValueError) as caught:
                        operation(module)
                    message = str(caught.exception)
                    self.assertIn(source_name, message)
                    self.assertIn("personal.json", message)
                    self.assertNotIn("PRIVATE VALUE", message)

    def test_transit_scripts_allow_absent_personal_file(self):
        for source_slug in ("pasmo", "suica"):
            with self.subTest(source_slug=source_slug):
                module = self._import_script(source_slug, None)
                self.assertEqual("", module.NEAREST_STATION)


    def test_pasmo_uses_nearest_station_for_railway_detection(self):
        module = self._import_script("pasmo", self._personal_settings())
        self.assertEqual(
            "Tokyo Metro", module.get_railway_company("Example Station", "Example B")
        )

    def test_suica_uses_nearest_station_for_railway_detection(self):
        module = self._import_script("suica", self._personal_settings())
        self.assertEqual(
            "Tokyo Metro", module.get_railway_company("Example Station", "Example B")
        )

    def test_suica_business_pairs_use_nearest_station(self):
        module = self._import_script("suica", self._personal_settings())
        pairs = module._init_business_pairs()
        self.assertEqual(4, len(pairs))
        self.assertTrue(all("Example Station" in pair for pair in pairs))
        module.BUSINESS_PAIRS = pairs
        first_pair = next(iter(pairs))
        tx = {
            "date": datetime(2026, 9, 21),
            "station1": first_pair[0],
            "station2": first_pair[1],
            "type": "入",
        }
        self.assertTrue(module.is_business_trip(tx))


    def test_rejects_source_marker_only_personal_matches(self):
        cases = []
        for rule_name in (
            "family_deposit",
            "family_split",
            "friend_transfer",
            "self_transfer",
        ):
            for invalid_pattern in ("振込＊", " \t振込＊\u3000"):
                cases.append(
                    (
                        "docomo_smtb_net_bank",
                        rule_name,
                        "pattern",
                        invalid_pattern,
                        {"currency": "JPY", "desc": "振込＊UNRELATED", "amount": 1},
                    )
                )
        for source_slug, markers, transaction in (
            (
                "mufg_bank",
                ("振込", "ことら送金"),
                {"desc": "振込 UNRELATED", "amount": 1},
            ),
            (
                "sony_bank",
                ("振込",),
                {"currency": "JPY", "desc": "振込 UNRELATED", "amount": 1},
            ),
        ):
            for marker in markers:
                for invalid_contains in (marker, f" \t{marker}\u3000"):
                    cases.append(
                        (
                            source_slug,
                            "self_transfer",
                            "contains",
                            invalid_contains,
                            transaction,
                        )
                    )

        for source_slug, rule_name, field, invalid_value, transaction in cases:
            with self.subTest(
                source_slug=source_slug,
                rule_name=rule_name,
                value=invalid_value,
            ):
                personal = self._personal_settings()
                personal["transfer_rules"][source_slug][rule_name][field] = invalid_value
                module = self._import_script(source_slug, personal)
                with self.assertRaises(ValueError) as caught:
                    module.get_transaction_info(1, transaction)
                message = str(caught.exception)
                self.assertIn(
                    f"transfer_rules.{source_slug}.{rule_name}.{field}", message
                )
                self.assertNotIn(invalid_value.strip(), message)

    def test_suica_main_surfaces_malformed_personal_settings(self):
        cases = (
            ('{"nearest_station": "DUMMY SECRET"', "personal.json", "DUMMY SECRET"),
            ({"nearest_station": 7}, "nearest_station", "7"),
        )
        for personal, expected_key, invalid_value in cases:
            with self.subTest(expected_key=expected_key):
                module = self._import_script("suica", personal)
                module.RAW_DATA = "09/21 物販 -100"
                module.sys.argv = ["suica_import.py", "review"]
                stderr = StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit) as caught:
                    module.main()
                self.assertEqual(1, caught.exception.code)
                message = stderr.getvalue()
                self.assertIn("Mobile Suica", message)
                self.assertIn(expected_key, message)
                self.assertNotIn(invalid_value, message)



    def test_pasmo_missing_nearest_station_rejects_ambiguous_classification(self):
        for personal in (None, {}, {"nearest_station": "   "}):
            with self.subTest(personal=personal):
                module = self._import_script("pasmo", personal)
                with self.assertRaises(ValueError) as caught:
                    module.get_railway_company("Example Unknown", "Example Other")
                message = str(caught.exception)
                self.assertIn("Mobile PASMO", message)
                self.assertIn("nearest_station", message)

    def test_pasmo_public_station_rules_do_not_require_personal_station(self):
        module = self._import_script("pasmo", None)
        cases = (
            ("溜池山王", "Example", "Tokyo Metro"),
            ("地 Example", "Example", "Tokyo Metro"),
            ("KS Example", "Example", "Keisei"),
            ("江ノ島", "Example", "Enoshima Electric Railway"),
        )
        for station1, station2, expected in cases:
            with self.subTest(station1=station1):
                self.assertEqual(expected, module.get_railway_company(station1, station2))

    def test_pasmo_accounts_are_loaded_from_source_specific_personal_settings(self):
        module = self._import_script("pasmo", self._personal_settings())
        self.assertEqual("2" * 32, module.PASMO_ACCOUNT)
        self.assertEqual("1" * 32, module.SHOPPING_ACCOUNT)
        self.assertEqual(
            ("1" * 32, None),
            module.get_transaction_info(
                1,
                {"type": "物販", "station1": "", "station2": "", "amount": -1},
            ),
        )

    def test_pasmo_rejects_malformed_account_settings_without_leaking(self):
        mutations = (
            None,
            "PRIVATE VALUE",
            {},
            {"source": "PRIVATE VALUE", "shopping": "Assets:Example"},
            {"source": "Assets:JPY - Current Assets:Banks:Example"},
        )
        for configured_accounts in mutations:
            with self.subTest(kind=type(configured_accounts).__name__):
                personal = self._personal_settings()
                if configured_accounts is None:
                    personal.pop("accounts")
                else:
                    personal["accounts"]["pasmo"] = configured_accounts
                module = self._import_script("pasmo", personal)
                module.RAW_DATA = "09/21 物販 -100"
                module.sys.argv = ["pasmo_import.py", "review"]
                stderr = StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit):
                    module.main()
                message = stderr.getvalue()
                self.assertIn("Mobile PASMO", message)
                self.assertIn("accounts.pasmo", message)
                self.assertNotIn("PRIVATE VALUE", message)

    def test_rejects_short_or_marker_vocabulary_identity_matches(self):
        cases = (
            (
                "docomo_smtb_net_bank",
                "family_deposit",
                "pattern",
                ("振込＊A", "振込＊とら送"),
                {"currency": "JPY", "desc": "振込＊UNRELATED", "amount": 1},
            ),
            (
                "mufg_bank",
                "self_transfer",
                "contains",
                ("A", "とら送"),
                {"desc": "振込 UNRELATED", "amount": 1},
            ),
            (
                "sony_bank",
                "self_transfer",
                "contains",
                ("AB", "振込"),
                {"currency": "JPY", "desc": "振込 UNRELATED", "amount": 1},
            ),
        )
        for source_slug, rule_name, field, values, transaction in cases:
            for invalid_value in values:
                with self.subTest(source_slug=source_slug, value=invalid_value):
                    personal = self._personal_settings()
                    personal["transfer_rules"][source_slug][rule_name][field] = invalid_value
                    module = self._import_script(source_slug, personal)
                    with self.assertRaises(ValueError) as caught:
                        module.get_transaction_info(1, transaction)
                    message = str(caught.exception)
                    self.assertIn(
                        f"transfer_rules.{source_slug}.{rule_name}.{field}", message
                    )
                    self.assertNotIn(invalid_value, message)
if __name__ == "__main__":
    unittest.main()
