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


if __name__ == "__main__":
    unittest.main()
