"""Tests for the Shell Mystery startup and answer validation."""

import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import main
from game.investigation_shell import (
    PROGRESS_STEPS,
    _custom,
    _interlude_reaction,
    _progress_reaction,
    _result_evidence,
    _run,
    run_shell_console,
)
from game.report_validation import validate_report

ROOT = Path(__file__).parents[1]


def complete_report() -> str:
    stages = "\n".join(
        f"<!-- NORTHSTAR_STAGE_{stage}_COMPLETED -->" for stage in range(1, 7)
    )
    return f"""# Rapport de test synthétique
{stages}

## Chronologie
| Heure | Fait | Source | Certitude |
| --- | --- | --- | --- |
| 09:00 | Un contrôle de test est terminé avant l'incident simulé. | controle-test.txt | confirmée |
| 09:05 | Une opération de test apparaît dans le journal de simulation. | operation-test.log | probable |
| 09:10 | Un second contrôle confirme le nouvel état du fichier. | etat-test.txt | confirmée |

## Accès et personnes
| Élément | Observation | Source |
| --- | --- | --- |
| session S-TEST | Une session de test est associée au terminal T-TEST. | sessions-test.log |
| credential C-TEST | Le registre de test distingue son propriétaire de son utilisateur. | acces-test.txt |

## Fausses pistes écartées
| Piste écartée | Raison de l'exclusion | Source |
| --- | --- | --- |
| Opération préparatoire | Elle ne suffit pas à expliquer l'état observé après l'incident. | journal-test.log |

## Preuves retenues
| Famille de preuve | Source consultée | Ce qu'elle établit |
| --- | --- | --- |
| Identités | membres-test.txt | La correspondance entre une personne et un accès de test. |
| Journaux | commandes-test.log | La séquence d'actions de la session de test. |
| Dépôt | branches-test.txt | La chronologie des changements du dépôt de test. |

## Analyse de l'incident
Action qui explique la disparition : une opération de test produit l'état manquant.
Session et terminal concernés : la session S-TEST est ouverte sur le terminal T-TEST.
Credential utilisée et son propriétaire : la credential C-TEST appartient à la personne A.
Acteur au terminal : la personne B réalise l'opération depuis la session observée.
Lien entre propriétaire, utilisateur et acteur : le registre, la session et les journaux décrivent trois rôles qu'il faut recouper.

## Conclusion
Responsable : personne B
Certitude : élevée
Justification : la chronologie et les trois familles de traces indépendantes concordent sur l'action et les rôles impliqués.
"""

class GameStartupTests(unittest.TestCase):
    def test_custom_find_cannot_list_outside_project(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
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

    def test_six_stage_markers_alone_do_not_validate_the_report(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "investigation-report.md"
            report.write_text(
                "\n".join(
                    f"<!-- NORTHSTAR_STAGE_{stage}_COMPLETED -->"
                    for stage in range(1, 7)
                ),
                encoding="utf-8",
            )
            output = StringIO()
            with patch.object(main, "ROOT", Path(directory)), patch.object(
                sys, "argv", ["main.py", "--answer", "synthetic|proof"]
            ), patch.object(main, "validate") as answer_validator, redirect_stdout(output):
                self.assertEqual(main.main(), 1)
            answer_validator.assert_not_called()
            self.assertIn("Chronologie", output.getvalue())

    def test_unedited_report_template_is_rejected(self):
        report = (ROOT / "investigation-report.md").read_text(encoding="utf-8")
        report += "\n" + "\n".join(
            f"<!-- NORTHSTAR_STAGE_{stage}_COMPLETED -->"
            for stage in range(1, 7)
        )
        issues = validate_report(report)
        self.assertTrue(any("Chronologie" in issue for issue in issues))
        self.assertTrue(any("Preuves retenues" in issue for issue in issues))
        self.assertTrue(any("justification argumentée" in issue for issue in issues))

    def test_table_headers_do_not_count_as_report_entries(self):
        report = complete_report()
        report = report.replace(
            "| Élément | Observation | Source |\n| --- | --- | --- |\n"
            "| session S-TEST | Une session de test est associée au terminal T-TEST. | sessions-test.log |\n"
            "| credential C-TEST | Le registre de test distingue son propriétaire de son utilisateur. | acces-test.txt |",
            "| Sujet | Description | Fichier |\n| --- | --- | --- |",
        ).replace(
            "| Piste écartée | Raison de l'exclusion | Source |\n| --- | --- | --- |\n"
            "| Opération préparatoire | Elle ne suffit pas à expliquer l'état observé après l'incident. | journal-test.log |",
            "| Sujet | Cause | Document |\n| --- | --- | --- |",
        )
        issues = validate_report(report)
        self.assertTrue(any("Accès et personnes" in issue for issue in issues))
        self.assertTrue(any("Fausses pistes" in issue for issue in issues))

    def test_complete_report_is_accepted_without_fixed_answer_wording(self):
        self.assertEqual(validate_report(complete_report()), [])

    def test_complete_prose_report_is_accepted_with_distinct_evidence_families(self):
        report = complete_report()
        report = re.sub(
            r"## Chronologie\n.*?(?=\n## Accès et personnes)",
            "## Chronologie\n"
            "À 09:00, controle-test.txt confirme le contrôle terminé avant l'incident. Certitude : confirmée.\n"
            "À 09:05, operation-test.log rapporte l'opération observée. Certitude : probable.\n"
            "À 09:10, etat-test.txt confirme le nouvel état du fichier. Certitude : confirmée.\n",
            report,
            flags=re.DOTALL,
        )
        report = re.sub(
            r"## Accès et personnes\n.*?(?=\n## Fausses pistes écartées)",
            "## Accès et personnes\n"
            "- La session S-TEST est associée au terminal T-TEST, d'après sessions-test.log.\n"
            "- Le registre acces-test.txt distingue le propriétaire de l'utilisateur.\n",
            report,
            flags=re.DOTALL,
        )
        report = re.sub(
            r"## Fausses pistes écartées\n.*?(?=\n## Preuves retenues)",
            "## Fausses pistes écartées\n"
            "- La piste préparatoire est écartée, car journal-test.log ne montre pas qu'elle a modifié le résultat.\n",
            report,
            flags=re.DOTALL,
        )
        report = re.sub(
            r"## Preuves retenues\n.*?(?=\n## Analyse de l'incident)",
            "## Preuves retenues\n"
            "- Identités : membres-test.txt relie une personne à un accès de test.\n"
            "- Journaux : commandes-test.log établit la séquence de la session.\n"
            "- Dépôt : branches-test.txt situe les changements du dépôt.\n",
            report,
            flags=re.DOTALL,
        )
        self.assertEqual(validate_report(report), [])

    def test_mixed_table_and_prose_entries_are_counted_together(self):
        report = complete_report().replace(
            "| 09:10 | Un second contrôle confirme le nouvel état du fichier. | etat-test.txt | confirmée |",
            "À 09:10, etat-test.txt confirme le nouvel état; certitude confirmée.",
        ).replace(
            "| Dépôt | branches-test.txt | La chronologie des changements du dépôt de test. |",
            "- Dépôt : branches-test.txt situe les changements du dépôt de test.",
        )
        self.assertEqual(validate_report(report), [])

    def test_free_text_chronology_requires_times_sources_and_certainty(self):
        report = re.sub(
            r"## Chronologie\n.*?(?=\n## Accès et personnes)",
            "## Chronologie\n"
            "À 09:00, le contrôle de test se termine; niveau de certitude confirmé.\n"
            "À 09:05, operation-test.log rapporte l'opération; certitude probable.\n"
            "À 09:10, etat-test.txt confirme le nouvel état; certitude confirmée.\n",
            complete_report(),
            flags=re.DOTALL,
        )
        self.assertTrue(any("Chronologie" in issue for issue in validate_report(report)))

    def test_false_lead_requires_a_reason_and_source(self):
        report = complete_report().replace(
            "Elle ne suffit pas à expliquer l'état observé après l'incident. | journal-test.log",
            "Elle est évoquée par un participant. | inconnu",
        )
        self.assertTrue(any("Fausses pistes" in issue for issue in validate_report(report)))

    def test_duplicate_stage_marker_does_not_count_as_complete(self):
        report = complete_report() + "\n<!-- NORTHSTAR_STAGE_1_COMPLETED -->"
        self.assertTrue(any("étapes de progression" in issue for issue in validate_report(report)))

    def test_repeated_evidence_family_does_not_count_as_three_independent_families(self):
        report = complete_report().replace(
            "| Journaux | commandes-test.log",
            "| Identités | commandes-test.log",
        ).replace(
            "| Dépôt | branches-test.txt",
            "| Identités | branches-test.txt",
        )
        self.assertTrue(any("trois familles distinctes" in issue for issue in validate_report(report)))

    def test_short_conclusion_fields_are_rejected(self):
        report = complete_report().replace(
            "Justification : la chronologie et les trois familles de traces indépendantes concordent sur l'action et les rôles impliqués.",
            "Justification : oui.",
        )
        self.assertTrue(any("justification argumentée" in issue for issue in validate_report(report)))

    def test_bracketed_template_placeholder_is_not_a_conclusion_value(self):
        report = complete_report().replace(
            "Responsable : personne B", "Responsable : [À compléter]"
        )
        self.assertTrue(any("Responsable" in issue for issue in validate_report(report)))

    def test_complete_report_is_forwarded_to_answer_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "investigation-report.md").write_text(
                complete_report(), encoding="utf-8"
            )
            with patch.object(main, "ROOT", Path(directory)), patch.object(
                sys, "argv", ["main.py", "--answer", "synthetic|proof"]
            ), patch.object(main, "validate", return_value=0) as answer_validator:
                self.assertEqual(main.main(), 0)
            answer_validator.assert_called_once_with("synthetic|proof")

    def test_test_sources_do_not_embed_an_uppercase_answer_pair(self):
        answer_pattern = re.compile(r"\b[A-Z]{3,}\|[A-Z]{3,}\b")
        for source in (ROOT / "tests").glob("*.py"):
            with self.subTest(source=source.name):
                self.assertIsNone(answer_pattern.search(source.read_text(encoding="utf-8")))

    def test_first_stage_waits_for_all_six_dossiers_and_find(self):
        required = set(PROGRESS_STEPS[0][0])
        step, reaction = _progress_reaction(
            {"dossier-01"}, {"find"}, 0, set(), set()
        )
        self.assertEqual((step, reaction), (0, None))

        step, reaction = _progress_reaction(
            required, {"find"}, 0, set(), set()
        )
        self.assertEqual(step, 1)
        self.assertTrue(reaction)

    def test_next_stage_requires_its_own_shell_operation_on_its_evidence(self):
        required = set(PROGRESS_STEPS[2][0])
        step, reaction = _progress_reaction(
            set(), {"cat"}, 2, required, {"grep"}
        )
        self.assertEqual((step, reaction), (2, None))

        step, reaction = _progress_reaction(
            required, {"grep"}, 2, required, {"grep"}
        )
        self.assertEqual(step, 3)
        self.assertTrue(reaction)

    def test_interlude_matches_discovered_file_path_at_current_stage(self):
        dialogue = _interlude_reaction(
            {"evidence/identity/members.txt"}, 1, set()
        )
        self.assertIn("identifiants", dialogue)

    def test_wrong_stage_does_not_emit_interlude(self):
        dialogue = _interlude_reaction(
            {"evidence/identity/members.txt"}, 0, set()
        )
        self.assertIsNone(dialogue)

    def test_witness_stage_waits_until_all_five_interviews_are_visible(self):
        required = set(PROGRESS_STEPS[4][0])
        observed = required - {"team-interview:Lydie"}
        step, reaction = _progress_reaction(
            observed, {"grep", "cut"}, 4, set(), set()
        )
        self.assertEqual((step, reaction), (4, None))

        step, reaction = _progress_reaction(
            required, {"grep", "cut"}, 4, set(), set()
        )
        self.assertEqual(step, 5)
        self.assertTrue(reaction)

    def test_interview_evidence_tracks_only_statements_in_command_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            team = root / "evidence" / "team"
            team.mkdir(parents=True)
            interviews = team / "interviews.txt"
            interviews.write_text(
                "Kevin|15:47|Je nie.\nLydie|15:50|J'ai vu quelqu'un.\n",
                encoding="utf-8",
            )
            command = "grep Lydie evidence/team/interviews.txt"
            output, error = _run(root, command)
            observed, _, _ = _result_evidence(root, command, output, error)

            self.assertIn("team-interview:Lydie", observed)
            self.assertNotIn("team-interview:Kevin", observed)

    def test_custom_file_dialogues_are_logged_with_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dossier = root / "dossiers" / "dossier-01"
            dossier.mkdir(parents=True)
            (dossier / "briefing.txt").write_text(
                "Le projet Northstar.\n", encoding="utf-8"
            )
            terminal_output = StringIO()
            with patch(
                "builtins.input",
                side_effect=[".files", ".cat dossiers/dossier-01/briefing.txt", ".exit"],
            ), redirect_stdout(terminal_output):
                run_shell_console(root)

            log = (root / ".student-data" / "session-current.log").read_text(
                encoding="utf-8"
            )
            self.assertIn("OUTPUT_BEGIN", log)
            self.assertIn("DIALOGUE [Mickael] Les archives sont classées", log)
            self.assertIn("DIALOGUE [Mickael] Le dossier sépare la copie", log)
            self.assertIn("OUTPUT_BEGIN", log)

    def test_existing_report_answer_requires_confirmation_before_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "investigation-report.md"
            report.write_text(
                "### Étape 1 : test\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_BEGIN -->\nAncienne note\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_END -->\n"
                "<!-- NORTHSTAR_STAGE_1_COMPLETED -->\n",
                encoding="utf-8",
            )
            terminal_output = StringIO()
            prompts = []
            answers = iter((".correct 1", "non", ".exit"))

            def answer(prompt=""):
                prompts.append(prompt)
                return next(answers)

            with patch(
                "builtins.input", side_effect=answer
            ), redirect_stdout(terminal_output):
                run_shell_console(root)

            self.assertIn("Ancienne note", report.read_text(encoding="utf-8"))
            log = (root / ".student-data" / "session-current.log").read_text(
                encoding="utf-8"
            )
            self.assertIn("REPORT_CORRECTION stage=1 status=declined", log)
            self.assertTrue(any("Voulez-vous la corriger ?" in prompt for prompt in prompts))

    def test_confirmed_report_answer_correction_updates_only_that_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "investigation-report.md"
            report.write_text(
                "### Étape 1 : test\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_BEGIN -->\nAncienne note\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_END -->\n"
                "Conclusion personnelle conservée.\n"
                "<!-- NORTHSTAR_STAGE_1_COMPLETED -->\n"
                "<!-- NORTHSTAR_STAGE_2 -->\n",
                encoding="utf-8",
            )
            with patch(
                "builtins.input",
                side_effect=[".correct 1", "oui", "Nouvelle note", ".exit"],
            ), redirect_stdout(StringIO()):
                run_shell_console(root)

            updated = report.read_text(encoding="utf-8")
            self.assertIn("Nouvelle note", updated)
            self.assertNotIn("Ancienne note", updated)
            self.assertIn("Conclusion personnelle conservée.", updated)
            self.assertIn("<!-- NORTHSTAR_STAGE_2 -->", updated)
            log = (root / ".student-data" / "session-current.log").read_text(
                encoding="utf-8"
            )
            self.assertIn("REPORT_CORRECTION stage=1 status=updated", log)

    def test_ambiguous_legacy_note_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "investigation-report.md"
            report.write_text(
                "### Étape 1 : ancienne version\nAncienne note\n"
                "Texte ajouté manuellement\n"
                "<!-- NORTHSTAR_STAGE_1_COMPLETED -->\n",
                encoding="utf-8",
            )
            with patch(
                "builtins.input",
                side_effect=[".correct 1", "oui", "Nouvelle note", ".exit"],
            ), redirect_stdout(StringIO()):
                run_shell_console(root)

            unchanged = report.read_text(encoding="utf-8")
            self.assertIn("Ancienne note", unchanged)
            self.assertIn("Texte ajouté manuellement", unchanged)
            self.assertNotIn("Nouvelle note", unchanged)
            log = (root / ".student-data" / "session-current.log").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                "REPORT_CORRECTION stage=1 status=ambiguous_legacy_note", log
            )

    def test_malformed_report_markers_are_never_modified(self):
        malformed_reports = (
            (
                "### Étape 1 : test\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_BEGIN -->\nAncienne note\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_BEGIN -->\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_END -->\n"
                "<!-- NORTHSTAR_STAGE_1_COMPLETED -->\n"
            ),
            (
                "### Étape 1 : test\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_END -->\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_BEGIN -->\nAncienne note\n"
                "<!-- NORTHSTAR_STAGE_1_COMPLETED -->\n"
            ),
            (
                "### Étape 1 : test\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_BEGIN -->\nAncienne note\n"
                "<!-- NORTHSTAR_STAGE_1_NOTE_END -->\n"
                "<!-- NORTHSTAR_STAGE_1_COMPLETED -->\n"
                "<!-- NORTHSTAR_STAGE_1_COMPLETED -->\n"
            ),
        )
        for original in malformed_reports:
            with self.subTest(original=original), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                report = root / "investigation-report.md"
                report.write_text(original, encoding="utf-8")
                with patch(
                    "builtins.input", side_effect=[".correct 1", ".exit"]
                ), redirect_stdout(StringIO()):
                    run_shell_console(root)

                self.assertEqual(report.read_text(encoding="utf-8"), original)
                log = (root / ".student-data" / "session-current.log").read_text(
                    encoding="utf-8"
                )
                self.assertIn(
                    "REPORT_CORRECTION stage=1 status=malformed_report_markers",
                    log,
                )

    def test_full_interactive_investigation_records_six_report_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "dossiers", root / "dossiers")
            shutil.copytree(ROOT / "evidence", root / "evidence")
            shutil.copy2(ROOT / "investigation-report.md", root / "investigation-report.md")
            commands = [
                ".help",
                ".files",
                "find dossiers -type f -print | sort",
                "cat dossiers/dossier-01/briefing.txt",
                "cat dossiers/dossier-02/access-review.txt",
                "cat dossiers/dossier-03/integrity-check.txt",
                "cat dossiers/dossier-04/team-movements.txt",
                "cat dossiers/dossier-05/disappearance.txt",
                "cat dossiers/dossier-06/final-report.txt",
                "Note: la livraison doit être prête à 16 h.",
                "find evidence -type f -print | sort",
                "cat evidence/identity/members.txt",
                "cat evidence/identity/credentials.txt",
                "cat evidence/identity/sessions.log | sort",
                "grep m- evidence/identity/members.txt | cut -d'|' -f1,2",
                "Anthony possède cred-17, mais plusieurs sessions l'utilisent.",
                "grep cred- evidence/identity/credentials.txt | cut -d'|' -f1,2",
                "grep s- evidence/identity/sessions.log | cut -d'|' -f1,3",
                "cat evidence/incident/incident-note.txt",
                "grep observed evidence/incident/incident-note.txt",
                "Le constat ne donne ni l'heure exacte ni l'auteur.",
                "cat evidence/logs/access.log | sort",
                "cat evidence/logs/terminal-history.log | sort",
                "cat evidence/logs/command-audit.txt | sort",
                "cat evidence/logs/failed-commands.txt",
                "grep 15: evidence/logs/access.log | sort",
                "La référence op-417 vise l'archive à 15:42:16.",
                "cat evidence/team/notes.txt",
                "grep 2026 evidence/team/notes.txt | cut -d' ' -f1,2,3",
                "grep 15: evidence/team/interviews.txt | cut -d'|' -f1,2,3",
                "Lydie ne reconnaît pas le visage; Kevin confirme sa présence.",
                "cat evidence/team/interviews.txt",
                "cat evidence/git/branch-log.txt",
                "cat evidence/git/reflog.txt",
                "sort evidence/git/reflog.txt",
                "Le push suit la suppression; il n'en est pas la cause.",
                ".exit",
            ]
            with patch("builtins.input", side_effect=commands), redirect_stdout(StringIO()):
                self.assertEqual(run_shell_console(root), 0)

            report = (root / "investigation-report.md").read_text(encoding="utf-8")
            log = (root / ".student-data" / "session-current.log").read_text(
                encoding="utf-8"
            )
            self.assertTrue(
                all(
                    f"<!-- NORTHSTAR_STAGE_{stage}_COMPLETED -->" in report
                    for stage in range(1, 7)
                ),
                f"{report}\n--- session log ---\n{log}",
            )
            self.assertEqual(log.count("STAGE_VALIDATED stage="), 6)
            self.assertEqual(log.count("REPORT_NOTE stage="), 6)
            self.assertNotIn("status=command_rejected", log)

    def test_console_rejects_shell_execution_from_read_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evidence").mkdir()
            (root / "evidence" / "sample.txt").write_text("preuve\n")
            for command in (
                'awk \'BEGIN { system("id") }\'',
                'find evidence -exec id ;',
            ):
                with self.subTest(command=command), self.assertRaises(ValueError):
                    _run(root, command)

    def test_game_starts_with_narrative_console(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with patch.object(main, "ROOT", Path(directory)), patch.object(
                sys, "argv", ["main.py"]
            ), patch("builtins.input", side_effect=[".exit"]), redirect_stdout(output):
                self.assertEqual(main.main(), 0)
            self.assertIn("Northstar", output.getvalue())
            self.assertIn("Console d'enquête prête", output.getvalue())

    def test_read_only_pipeline_is_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / "evidence" / "logs"
            logs.mkdir(parents=True)
            (logs / "terminal-history.log").write_text("preuve\n", encoding="utf-8")
            output = StringIO()
            with patch.object(main, "ROOT", root), patch.object(
                sys, "argv", ["main.py"]
            ), patch(
                "builtins.input",
                side_effect=["find evidence -type f -print | sort", ".exit"],
            ), redirect_stdout(output):
                self.assertEqual(main.main(), 0)
            self.assertIn("evidence/logs/terminal-history.log", output.getvalue())
            self.assertNotIn("unknown primary or operator", output.getvalue())

    def test_wrong_answer_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "investigation-report.md").write_text(
                complete_report(), encoding="utf-8"
            )
            output = StringIO()
            with patch.object(main, "ROOT", Path(directory)), patch.object(
                sys, "argv", ["main.py", "--answer", "not-an-owner|not-an-actor"]
            ), redirect_stdout(output):
                self.assertEqual(main.main(), 1)
            self.assertIn("preuve est incomplète", output.getvalue())


if __name__ == "__main__":
    unittest.main()
