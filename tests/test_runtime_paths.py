import ast
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, cast
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".kiro/skills/gnucash-import/references/templates/script-template.py"


@contextmanager
def working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class RuntimePathTest(unittest.TestCase):
    @staticmethod
    def _targets():
        paths = sorted((ROOT / "scripts").glob("*_import.py"))
        if len(paths) != 32:
            raise AssertionError(f"expected 32 import scripts, found {len(paths)}")
        return paths + [TEMPLATE]

    @staticmethod
    def _resolver(path: Path, source_file: Path) -> Callable[[], Path]:
        tree = ast.parse(path.read_text())
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "find_project_root"
        )
        namespace: dict[str, Any] = {
            "Path": Path,
            "__file__": str(source_file),
            "os": os,
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
        return cast(Callable[[], Path], namespace["find_project_root"])

    @staticmethod
    def _root(path: Path) -> Path:
        (path / ".kiro/skills/gnucash-import").mkdir(parents=True)
        return path

    def test_all_resolvers_honor_precedence_fallback_spaces_and_failure(self):
        for target in self._targets():
            with self.subTest(target=target.name), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                env_root = self._root(base / "environment root with spaces")
                cwd_root = self._root(base / "working root with spaces")
                source_root = self._root(base / "source root with spaces")
                source_file = source_root / "scripts" / target.name
                source_file.parent.mkdir()
                resolver = self._resolver(target, source_file)

                with patch.dict(os.environ, {"GNUCASH_IMPORT_ROOT": str(env_root)}), working_directory(cwd_root):
                    self.assertEqual(env_root, resolver())
                with patch.dict(os.environ, {}, clear=True), working_directory(cwd_root):
                    self.assertEqual(cwd_root.resolve(), resolver().resolve())
                with patch.dict(os.environ, {}, clear=True), working_directory(base):
                    self.assertEqual(source_root.resolve(), resolver().resolve())

                missing_source = base / "missing" / "scripts" / target.name
                missing_resolver = self._resolver(target, missing_source)
                with patch.dict(os.environ, {}, clear=True), working_directory(base):
                    with self.assertRaises(FileNotFoundError):
                        missing_resolver()


if __name__ == "__main__":
    unittest.main()
