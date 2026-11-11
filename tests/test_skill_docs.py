from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/gnucash-import/SKILL.md"


def psql_commands(markdown: str) -> list[str]:
    """Return each shell command in a bash block that runs psql.

    Backslash-continued lines are joined into one command.
    """
    commands = []
    for block in re.findall(r"```bash\n(.*?)```", markdown, re.DOTALL):
        command = ""
        for line in block.splitlines():
            if not command and line.lstrip().startswith("#"):
                continue
            command += line.rstrip("\\").strip() + " "
            if line.endswith("\\"):
                continue
            if re.search(r"(^|\s)psql\s", command):
                commands.append(command.strip())
            command = ""
    return commands


class SkillDocsTest(unittest.TestCase):
    def test_every_psql_command_sets_verified_tls_inline(self):
        commands = psql_commands(SKILL.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(commands), 4)
        for command in commands:
            with self.subTest(command=command[:80]):
                self.assertIn("PGSSLMODE=verify-full ", command)
                self.assertIn("PGSSLROOTCERT=", command)

    def test_database_item_is_read_by_id(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertNotIn("op://gnucash/gnucash-db/", text)
        self.assertIn("op://gnucash/n4k5eoi3jxo7ynmsfxisls7liu/server", text)

    def test_tunnel_access_keeps_host_verification(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("export PGHOSTADDR=127.0.0.1", text)
        self.assertNotIn("over the internet from the office", text)

    def test_multiple_sql_files_run_separately_as_validated(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?i)outer `?BEGIN")
        self.assertIn("Execute each validated SQL file separately", text)
        self.assertIn("Never concatenate SQL files", text)


if __name__ == "__main__":
    unittest.main()
