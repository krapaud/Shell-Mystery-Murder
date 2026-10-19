"""Tests for the Shell Mystery startup and answer validation."""

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class GameStartupTests(unittest.TestCase):
    def test_game_starts_with_narrative_console(self):
        result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=ROOT,
            input=".exit\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Northstar", result.stdout)
        self.assertIn("Console d'enquête prête", result.stdout)

    def test_wrong_answer_is_rejected(self):
        result = subprocess.run(
            [sys.executable, "main.py", "--answer", "WRONG|ACTOR"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
