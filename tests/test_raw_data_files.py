from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import tempfile
import unicodedata
import unittest
from collections.abc import Callable
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TEMPLATE = ROOT / ".kiro/skills/gnucash-import/references/templates/script-template.py"

# Text that would run as Python if it were pasted into a triple-quoted literal.
SOURCE_BREAKOUT = '"""\nraise SystemExit("statement text executed as code")\n"""'
CONTROL_PAYLOAD = "a\r\nb\rc\x1b[2Kd\x07e\x85f\x7fg\u202eh\u2066i\tj\x00k\n"
CONTROL_EXPECTED = "a\nbc[2Kdefghi\tjk\n"


def _targets() -> list[Path]:
    paths = sorted(SCRIPTS.glob("*_import.py"))
    if len(paths) != 32:
        raise AssertionError(f"expected 32 import scripts, found {len(paths)}")
    return paths + [TEMPLATE]


def _raw_data_names(path: Path) -> list[str]:
    """Return module-level names that hold statement data."""
    tree = ast.parse(path.read_text())
    names = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith("RAW_DATA"):
                    names.append(target.id)
    return names


def _environment_variable(name: str) -> str:
    return "GNUCASH_" + name


class RawDataFileTest(unittest.TestCase):
    def _load_functions(self, path: Path, source_file: Path) -> dict[str, Any]:
        tree = ast.parse(path.read_text())
        wanted = {"load_raw_data", "strip_control_characters"}
        body: list[ast.stmt] = [
            node
            for node in tree.body
            if (isinstance(node, ast.FunctionDef) and node.name in wanted)
            or (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id in {"RAW_DATA_FILE", "BIDI_CONTROLS"}
                    for target in node.targets
                )
            )
        ]
        namespace: dict[str, Any] = {
            "Path": Path,
            "__file__": str(source_file),
            "os": os,
            "unicodedata": unicodedata,
        }
        exec(  # noqa: S102 runs a function extracted from a repository script, not untrusted input
            compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"),
            namespace,
        )
        self.assertIn("load_raw_data", namespace, path.name)
        return namespace

    def _import_script(self, script_path: Path, environment: dict[str, str]) -> Any:
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
        spec = importlib.util.spec_from_file_location(
            f"raw_data_{script_path.stem}_{id(temporary)}", script_path
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        with patch.dict(
            os.environ, {"GNUCASH_IMPORT_ROOT": str(project_root), **environment}
        ):
            spec.loader.exec_module(module)
        return module

    def test_no_target_embeds_statement_data_in_python_source(self):
        for target in _targets():
            with self.subTest(target=target.name):
                tree = ast.parse(target.read_text())
                for node in tree.body:
                    if not isinstance(node, ast.Assign):
                        continue
                    names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                    if any(
                        name.startswith("RAW_DATA") and name != "RAW_DATA_FILE"
                        for name in names
                    ):
                        self.assertNotIsInstance(node.value, ast.Constant, names)
                self.assertTrue(
                    any(
                        isinstance(node, ast.FunctionDef)
                        and node.name == "load_raw_data"
                        for node in tree.body
                    )
                )

    def test_scripts_read_statement_data_from_environment_files(self):
        for script in _targets()[:-1]:
            with (
                self.subTest(script=script.name),
                tempfile.TemporaryDirectory() as temporary,
            ):
                names = [
                    name for name in _raw_data_names(script) if name != "RAW_DATA_FILE"
                ]
                self.assertTrue(names)
                environment = {}
                for name in names:
                    data_file = Path(temporary) / f"{name}.txt"
                    data_file.write_text(SOURCE_BREAKOUT, encoding="utf-8")
                    environment[_environment_variable(name)] = str(data_file)
                module = self._import_script(script, environment)
                for name in names:
                    self.assertEqual(SOURCE_BREAKOUT, getattr(module, name))

    def test_default_statement_file_sits_next_to_the_copied_script(self):
        with tempfile.TemporaryDirectory() as temporary:
            work_dir = Path(temporary)
            copied = work_dir / "import.py"
            shutil.copyfile(SCRIPTS / "ihg_rewards_club_import.py", copied)
            (work_dir / "raw.txt").write_text(SOURCE_BREAKOUT, encoding="utf-8")
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GNUCASH_RAW_DATA", None)
                module = self._import_script(copied, {})
            self.assertEqual(SOURCE_BREAKOUT, module.RAW_DATA)

    def test_missing_statement_file_reads_as_empty(self):
        for target in _targets():
            with (
                self.subTest(target=target.name),
                tempfile.TemporaryDirectory() as temporary,
            ):
                functions = self._load_functions(target, Path(temporary) / "import.py")
                load_raw_data = cast(Callable[..., str], functions["load_raw_data"])
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("GNUCASH_RAW_DATA", None)
                    self.assertEqual("", load_raw_data())

    def test_control_characters_are_removed_except_tab_and_newline(self):
        for target in _targets():
            with (
                self.subTest(target=target.name),
                tempfile.TemporaryDirectory() as temporary,
            ):
                work_dir = Path(temporary)
                (work_dir / "raw.txt").write_bytes(
                    ("\ufeff" + CONTROL_PAYLOAD).encode("utf-8")
                )
                functions = self._load_functions(target, work_dir / "import.py")
                load_raw_data = cast(Callable[..., str], functions["load_raw_data"])
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("GNUCASH_RAW_DATA", None)
                    self.assertEqual(CONTROL_EXPECTED, load_raw_data())

    def test_review_and_sql_never_echo_control_characters(self):
        merchant = "Hotel\rDELETE FROM transactions; --\x1b[1A\x1b[2K"
        with tempfile.TemporaryDirectory() as temporary:
            data_file = Path(temporary) / "raw.txt"
            data_file.write_text(
                f"2030/01/02\t{merchant}\t-1,000\tExpenses:Entertainment:Travel\n",
                encoding="utf-8",
            )
            module = self._import_script(
                SCRIPTS / "ihg_rewards_club_import.py",
                {"GNUCASH_RAW_DATA": str(data_file)},
            )
            for command in ("review", "sql"):
                with self.subTest(command=command):
                    module.sys.argv = ["import.py", command]
                    output = StringIO()
                    with redirect_stdout(output):
                        module.main()
                    text = output.getvalue()
                    self.assertIn("HotelDELETE FROM transactions; --[1A[2K", text)
                    self.assertNotIn("\r", text)
                    self.assertNotIn("\x1b", text)
                    self.assertFalse(
                        any(
                            line.lstrip().startswith("DELETE")
                            for line in text.splitlines()
                        )
                    )


if __name__ == "__main__":
    unittest.main()
