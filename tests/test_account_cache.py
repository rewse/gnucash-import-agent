import ast
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".kiro/skills/gnucash-import/references/templates/script-template.py"
INJECTED_VALUE = "x'); SELECT 1; --"


class AccountCacheTest(unittest.TestCase):
    @staticmethod
    def _targets():
        scripts = sorted((ROOT / "scripts").glob("*_import.py"))
        if len(scripts) != 32:
            raise AssertionError(f"expected 32 import scripts, found {len(scripts)}")
        return scripts + [TEMPLATE]

    @staticmethod
    def _account_paths(path):
        tree = ast.parse(path.read_text())
        return {
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "get_guid"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        }

    def test_all_targets_reject_non_guid_cache_values_before_exposing_accounts(self):
        for index, target in enumerate(self._targets()):
            with self.subTest(target=target.name), tempfile.TemporaryDirectory() as temporary:
                project_root = Path(temporary)
                references = project_root / ".kiro/skills/gnucash-import/references"
                references.mkdir(parents=True)
                accounts = {path: f"{position + 1:032x}" for position, path in enumerate(sorted(self._account_paths(target)))}
                accounts["Assets:Injected"] = INJECTED_VALUE
                (references / "account-guid-cache.json").write_text(json.dumps({"accounts": accounts}))
                spec = importlib.util.spec_from_file_location(f"cache_target_{index}", target)
                assert spec is not None
                module = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                output = StringIO()
                with patch.dict(os.environ, {"GNUCASH_IMPORT_ROOT": str(project_root)}), redirect_stdout(output):
                    with self.assertRaises(ValueError) as caught:
                        spec.loader.exec_module(module)
                self.assertNotIn(INJECTED_VALUE, str(caught.exception))
                self.assertNotIn("SELECT 1", output.getvalue())
                self.assertFalse(hasattr(module, "ACCOUNTS"))

    def test_valid_cache_values_are_exposed(self):
        target = ROOT / "scripts/amazon_gc_import.py"
        with tempfile.TemporaryDirectory() as temporary:
            project_root = Path(temporary)
            references = project_root / ".kiro/skills/gnucash-import/references"
            references.mkdir(parents=True)
            accounts = {path: "a" * 32 for path in self._account_paths(target)}
            (references / "account-guid-cache.json").write_text(json.dumps({"accounts": accounts}))
            spec = importlib.util.spec_from_file_location("valid_cache_target", target)
            assert spec is not None
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            with patch.dict(os.environ, {"GNUCASH_IMPORT_ROOT": str(project_root)}):
                spec.loader.exec_module(module)
            self.assertEqual(set(accounts.values()), set(module.ACCOUNTS.values()))


if __name__ == "__main__":
    unittest.main()
