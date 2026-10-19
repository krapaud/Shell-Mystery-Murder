"""Tests for the Shell Mystery startup and answer validation."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from game.investigation_shell import _custom, _progress_reaction, _result_evidence, _run


ROOT = Path(__file__).parents[1]


class GameStartupTests(unittest.TestCase):
    def test_custom_find_cannot_list_outside_project(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                _custom(Path(directory), ".find ../*")

    def test_pipeline_does_not_credit_unused_upstream_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = root / "evidence" / "identity"
            identity.mkdir(parents=True)
            (identity / "members.txt").write_text("Kevin\n", encoding="utf-8")
            (identity / "credentials.txt").write_text("cred-17\n", encoding="utf-8")
            command = (
                "grep __NO_MATCH__ evidence/identity/members.txt | "
                "cat evidence/identity/credentials.txt"
            )
            output, error = _run(root, command)
            observed, _, _ = _result_evidence(root, command, output, error)
            self.assertIn("evidence/identity/credentials", observed)
            self.assertNotIn("evidence/identity/members", observed)

    def test_empty_search_does_not_validate_a_dossier(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dossier = root / "dossiers" / "dossier-01"
            dossier.mkdir(parents=True)
            (dossier / "briefing.txt").write_text("Northstar\n", encoding="utf-8")
            command = "grep introuvable dossiers/dossier-01/briefing.txt"
            output, error = _run(root, command)
            observed, _, commands = _result_evidence(root, command, output, error)
            step, reaction = _progress_reaction(observed, commands, 0, set(), {"find"})
            self.assertEqual((step, reaction), (0, None))
            self.assertFalse(observed)

    def test_compact_cut_delimiter_in_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "members.txt").write_text("m-01|Kevin\n", encoding="utf-8")
            output, error = _run(root, "grep m- members.txt | cut -d'|' -f1")
            self.assertEqual((output, error), ("m-01\n", ""))

    def test_correct_names_require_completed_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "investigation-report.md"
            report.write_text("# Rapport vierge\n", encoding="utf-8")
            with patch.object(main, "ROOT", Path(directory)), patch.object(
                sys, "argv", ["main.py", "--answer", "ANTHONY|KEVIN"]
            ):
                self.assertEqual(main.main(), 1)

    def test_console_rejects_shell_execution_from_read_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence").mkdir()
            (root / "evidence" / "sample.txt").write_text("preuve\n")
            for command in (
                'awk \'BEGIN { system("id") }\'',
                'find evidence -exec id ;',
            ):
                with self.subTest(command=command):
                    with self.assertRaises(ValueError):
                        _run(root, command)

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

    def test_read_only_pipeline_is_supported(self):
        result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=ROOT,
            input="find evidence -type f -print | sort\n.exit\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("evidence/logs/terminal-history.log", result.stdout)
        self.assertNotIn("unknown primary or operator", result.stdout)

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
