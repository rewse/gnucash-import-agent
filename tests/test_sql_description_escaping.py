from __future__ import annotations

import ast
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SQL_MARKER = "SYNTHETIC_SQL_MARKER"


def executable_sql(sql: str) -> str:
    """Return SQL text outside string literals and line comments."""
    result = []
    index = 0
    in_literal = False
    while index < len(sql):
        character = sql[index]
        if in_literal:
            if character == "'":
                if index + 1 < len(sql) and sql[index + 1] == "'":
                    index += 2
                    continue
                in_literal = False
            index += 1
            continue
        if character == "'":
            in_literal = True
            index += 1
            continue
        if sql.startswith("--", index):
            newline = sql.find("\n", index)
            index = len(sql) if newline == -1 else newline
            continue
        result.append(character)
        index += 1
    if in_literal:
        raise AssertionError("generated SQL contains an unterminated string literal")
    return "".join(result)


class SqlDescriptionEscapingTest(unittest.TestCase):
    def _import_script(self, source_slug: str, personal: Any = None) -> Any:
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
            f"test_sql_{source_slug}_{id(temporary)}", script_path
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {"GNUCASH_IMPORT_ROOT": str(project_root)}):
            spec.loader.exec_module(module)
        return module

    @staticmethod
    def _capture_sql(module: Any, transactions: list[dict[str, Any]]) -> str:
        output = StringIO()
        with redirect_stdout(output):
            module.output_sql(transactions)
        return output.getvalue()

    def test_docomo_split_description_cannot_escape_sql_literal(self):
        description = f"x'); SELECT '{SQL_MARKER}'; --"
        personal = {
            "transfer_rules": {
                "docomo_smtb_net_bank": {
                    "family_split": {
                        "amount": -100,
                        "description": description,
                        "pattern": "振込＊EXAMPLE FAMILY",
                        "splits": [
                            {"account": "Assets:Example A", "amount": -60},
                            {"account": "Expenses:Example B", "amount": -40},
                        ],
                    }
                }
            }
        }
        module = self._import_script("docomo_smtb_net_bank", personal)
        module.ACCOUNTS.update(
            {"Assets:Example A": "a" * 32, "Expenses:Example B": "b" * 32}
        )
        module.PERSONAL_RULES, error = module.load_personal_rules(
            "docomo_smtb_net_bank"
        )
        self.assertIsNone(error)
        sql = self._capture_sql(
            module,
            [
                {
                    "amount": -100,
                    "currency": "JPY",
                    "date": date(2030, 1, 2),
                    "desc": "振込＊EXAMPLE FAMILY",
                }
            ],
        )

        self.assertIn("x''); SELECT ''SYNTHETIC_SQL_MARKER''; --", sql)
        self.assertNotIn(SQL_MARKER, executable_sql(sql))

    def _amazon_point_sql(self, description: str | None) -> str:
        module = self._import_script("amazon_point")
        module.ACCOUNTS["Expenses:Example"] = "c" * 32
        return self._capture_sql(
            module,
            [
                {
                    "date": datetime(2030, 1, 2),
                    "desc": description,
                    "splits": [
                        {
                            "account": "Expenses:Example",
                            "points": 10,
                        }
                    ],
                }
            ],
        )

    def test_amazon_point_none_description_outputs_null(self):
        sql = self._amazon_point_sql(None)

        self.assertIn("NOW(), NULL);", sql)

    def test_amazon_point_empty_description_outputs_empty_literal(self):
        sql = self._amazon_point_sql("")

        self.assertIn("NOW(), '');", sql)

    def test_amazon_point_normal_description_outputs_quoted_literal(self):
        sql = self._amazon_point_sql("Example purchase")

        self.assertIn("NOW(), 'Example purchase');", sql)

    def test_amazon_point_quoted_description_outputs_doubled_quotes(self):
        sql = self._amazon_point_sql("Amazon's reward")

        self.assertIn("NOW(), 'Amazon''s reward');", sql)

    def test_amazon_point_description_cannot_escape_literal_or_comment(self):
        description = f"x'); SELECT '{SQL_MARKER}'; --\nCOMMIT; --"
        sql = self._amazon_point_sql(description)

        self.assertIn("x''); SELECT ''SYNTHETIC_SQL_MARKER''; --", sql)
        self.assertNotIn(description, sql.splitlines()[2])
        self.assertNotIn(SQL_MARKER, executable_sql(sql))
        self.assertEqual(1, sum(line.startswith("-- Transaction ") for line in sql.splitlines()))


if __name__ == "__main__":
    unittest.main()
