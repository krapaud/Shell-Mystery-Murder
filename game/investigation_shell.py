"""Restricted terminal console with narrative reactions."""

import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import readline
except ImportError:  # pragma: no cover - platform fallback
    readline = None


HELP = """Commandes : .files, .cat <fichier>, .find <motif>, .grep <motif> <fichier>, .help (ou help), .exit.
Les commandes Shell de lecture (find, cat, grep, cut, sort, awk, head, tail)
peuvent aussi être utilisées. Les écritures et suppressions sont interdites."""
NARRATIVE_REACTIONS = {
    "dossier-01": "Le contexte est posé. Notez l'archive et les rôles avant de suivre les traces.",
    "dossier-02": "Ici, séparez bien le propriétaire de la credential de l'acteur de la session.",
    "dossier-03": "Ce contrôle fixe le dernier moment où l'archive est encore confirmée.",
    "dossier-04": "Comparez chaque action légitime avec son terminal et son horaire.",
    "dossier-05": "Cette étape décrit la disparition. Confirmez-la avec les journaux techniques.",
    "dossier-06": "Votre conclusion doit relier plusieurs familles de preuves indépendantes.",
    "credentials.txt": "Cette trace donne le propriétaire de la credential, pas nécessairement l'acteur.",
    "sessions.log": "Cette trace relie une session, une personne et un terminal.",
    "access.log": "Comparez l'heure, la session, la credential et la cible de l'action.",
    "terminal-history.log": "L'historique montre les commandes lancées depuis le terminal.",
    "command-audit.txt": "Ce journal permet de confirmer la commande et son résultat.",
    "incident-note.txt": "Cette note fixe l'heure et la cible de la disparition.",
    "branch-log.txt": "Le journal Git confirme la branche créée autour de l'incident.",
    "reflog.txt": "Le reflog complète la chronologie de la branche et du push.",
}
ALLOWED = {"find", "cat", "grep", "cut", "sort", "awk", "head", "tail", "wc", "pwd", "ls"}
RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"


def _paint(code: str, text: str) -> str:
    return f"{code}{text}{RESET}" if sys.stdout.isatty() else text


def _line(char: str = "─", size: int = 62) -> str:
    return _paint(MAGENTA, char * size)


def _result_header(command: str) -> None:
    print(_line())
    print(_paint(CYAN, f"RÉSULTAT DE LA RECHERCHE : {command}"))
    print(_line("·"))


def _narrative_reaction(command: str) -> Optional[str]:
    """Return a hint only when the command targets a known evidence item."""
    for marker, reaction in NARRATIVE_REACTIONS.items():
        if marker in command:
            return reaction
    return None


PROGRESS_STEPS = (
    (("dossier-01",), "Le cadre de l'affaire est posé. Notez les rôles, mais gardez vos hypothèses ouvertes."),
    (("dossier-02",), "Les accès sont identifiés. La suite consiste à relier les identifiants sans confondre droit et utilisateur."),
    (("dossier-03",), "Vous avez le point de référence de l'intégrité. Il servira à fixer le début de la chronologie."),
    (("dossier-04",), "Les premières pistes humaines apparaissent. Vérifiez maintenant les déclarations dans les traces."),
    (("dossier-05",), "La fenêtre de disparition est définie. Il faut maintenant relier l'action, la session et le terminal."),
    (("dossier-06",), "Les questions du rapport sont posées. Passez aux preuves techniques et construisez votre propre chronologie."),
    (("evidence/identity/members", "evidence/identity/credentials", "evidence/identity/sessions"), "Les identités sont séparées des actions. Les correspondances sont prêtes à être vérifiées."),
    (("evidence/incident/incident-note",), "Le constat est établi. Il décrit le résultat, pas encore l'auteur."),
    (("evidence/logs/access", "evidence/logs/terminal-history", "evidence/logs/command-audit", "evidence/logs/failed-commands"), "La chronologie technique se précise. Comparez les succès, les actions et le premier échec."),
    (("evidence/team/interviews",), "Les témoignages sont confrontés aux traces. Une déclaration ne vaut que si les horaires la confirment."),
    (("evidence/git/branch-log", "evidence/git/reflog"), "Git confirme l'ordre des opérations. Utilisez-le pour vérifier la chronologie, pas pour conclure seul."),
)

REPORT_STAGES = (
    "Quels sont le projet, le fichier recherché et les rôles de l'équipe ?",
    "Quelles correspondances avez-vous trouvées entre membres, sessions, credentials et terminaux ?",
    "Quel est le dernier état certain de l'archive avant l'incident ?",
    "Quelles déclarations devez-vous vérifier et quelles pistes semblent légitimes ?",
    "Que savez-vous de la fenêtre pendant laquelle l'archive disparaît ?",
    "Quelles sont les questions auxquelles votre rapport doit répondre ?",
    "Quelle correspondance d'identité est confirmée par plusieurs fichiers ?",
    "Que constate exactement la note d'incident, sans en déduire l'auteur ?",
    "Quelle chronologie pouvez-vous établir à partir des logs ?",
    "Quelle déclaration est confirmée ou contredite par les traces ?",
    "Que confirme Git dans l'ordre des opérations ?",
)


def _progress_reaction(command: str, step: int, consulted: set[str]) -> tuple[int, Optional[str]]:
    lowered = command.lower()
    consulted.update(marker for markers, _ in PROGRESS_STEPS for marker in markers if marker in lowered)
    if step >= len(PROGRESS_STEPS):
        return step, None
    required, reaction = PROGRESS_STEPS[step]
    if all(marker in consulted for marker in required):
        return step + 1, reaction
    return step, None


def _write_session_log(log_path: Path, message: str) -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"[{timestamp}] {message}\n")


def _record_stage_answer(root: Path, stage: int, log_path: Path) -> None:
    """Store one student answer without replacing an existing answer."""
    report = root / "investigation-report.md"
    if stage < 1 or stage > len(REPORT_STAGES) or not report.exists():
        return
    dialogue = f"[Mickael] Étape {stage} validée. {REPORT_STAGES[stage - 1]}"
    print(_paint(YELLOW, dialogue))
    _write_session_log(log_path, f"DIALOGUE {dialogue}")
    _write_session_log(log_path, f"STAGE_VALIDATED stage={stage}")
    try:
        answer = input(_paint(CYAN, "Votre note : ")).strip()
    except EOFError:
        dialogue = "[Mickael] Aucune note saisie. L'étape reste validée, mais le rapport n'est pas complété."
        print(_paint(YELLOW, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_NOTE stage={stage} status=missing")
        return
    if not answer:
        dialogue = "[Mickael] Réponse vide : rien n'a été écrit dans le rapport."
        print(_paint(YELLOW, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_NOTE stage={stage} status=empty")
        return
    content = report.read_text()
    marker = f"<!-- NORTHSTAR_STAGE_{stage} -->"
    completed_marker = f"<!-- NORTHSTAR_STAGE_{stage}_COMPLETED -->"
    if completed_marker in content:
        dialogue = "[Mickael] Une réponse existe déjà pour cette étape."
        print(_paint(YELLOW, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_NOTE stage={stage} status=already_exists")
        try:
            correction = input(_paint(CYAN, "Voulez-vous la corriger ? (oui/non) : ")).strip().lower()
        except EOFError:
            dialogue = "[Mickael] Aucune confirmation reçue. La réponse existante est conservée."
            print(_paint(YELLOW, dialogue))
            _write_session_log(log_path, f"DIALOGUE {dialogue}")
            _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=no_confirmation")
            return
        if correction not in {"oui", "o", "yes", "y"}:
            dialogue = "[Mickael] La réponse existante n'a pas été modifiée."
            print(_paint(YELLOW, dialogue))
            _write_session_log(log_path, f"DIALOGUE {dialogue}")
            _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=declined")
            return
        try:
            answer = input(_paint(CYAN, "Nouvelle réponse : ")).strip()
        except EOFError:
            dialogue = "[Mickael] Aucune nouvelle réponse reçue. La réponse existante est conservée."
            print(_paint(YELLOW, dialogue))
            _write_session_log(log_path, f"DIALOGUE {dialogue}")
            _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=missing")
            return
        if not answer:
            dialogue = "[Mickael] Réponse vide : la réponse existante est conservée."
            print(_paint(YELLOW, dialogue))
            _write_session_log(log_path, f"DIALOGUE {dialogue}")
            _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=empty")
            return
        marker_start = content.find(completed_marker)
        answer_line_end = content.rfind("\n", 0, marker_start)
        answer_line_start = content.rfind("\n", 0, answer_line_end) + 1
        updated = content[:answer_line_start] + answer + content[answer_line_end:]
        report.write_text(updated)
        dialogue = f"[Mickael] Réponse de l'étape {stage} corrigée."
        print(_paint(GREEN, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=updated")
        return
    if marker not in content:
        dialogue = "[Mickael] Cette rubrique de rapport est introuvable. Aucune écriture effectuée."
        print(_paint(RED, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_NOTE stage={stage} status=missing_marker")
        return
    updated = content.replace(marker, f"{answer}\n{completed_marker}", 1)
    if updated == content:
        print(_paint(RED, "[Mickael] Cette réponse existe déjà. Elle n'a pas été écrasée."))
        return
    report.write_text(updated)
    dialogue = f"[Mickael] Note enregistrée dans l'étape {stage} du rapport."
    print(_paint(GREEN, dialogue))
    _write_session_log(log_path, f"DIALOGUE {dialogue}")
    _write_session_log(log_path, f"REPORT_NOTE stage={stage} status=recorded")


def _safe_path(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if root.resolve() not in candidate.parents and candidate != root.resolve():
        raise ValueError("Chemin hors du dossier d'enquête.")
    return candidate


def _run(root: Path, command: str) -> tuple[str, str]:
    tokens = shlex.split(command)
    if not tokens:
        raise ValueError("Commande interdite. Utilisez une commande de lecture Shell.")

    pipelines: list[list[str]] = [[]]
    for token in tokens:
        if token == "|":
            if not pipelines[-1]:
                raise ValueError("Pipeline invalide. Chaque symbole | doit relier deux commandes.")
            pipelines.append([])
        elif token in {">", ">>", ";", "&&"}:
            raise ValueError("Redirections et enchaînements interdits dans ce terminal.")
        else:
            pipelines[-1].append(token)
    if not pipelines[-1]:
        raise ValueError("Pipeline invalide. Chaque symbole | doit relier deux commandes.")

    for parts in pipelines:
        if parts[0] not in ALLOWED:
            raise ValueError("Commande interdite. Utilisez une commande de lecture Shell.")
        for part in parts[1:]:
            if part.startswith("-"):
                continue
            if "/" in part or part in {"dossiers", "evidence"}:
                _safe_path(root, part)

    processes = []
    previous_stdout = None
    for index, parts in enumerate(pipelines):
        process = subprocess.Popen(
            parts,
            cwd=root,
            stdin=previous_stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if previous_stdout is not None:
            previous_stdout.close()
        previous_stdout = process.stdout
        processes.append(process)

    stdout, stderr = processes[-1].communicate()
    for process in processes[:-1]:
        process.wait()
        if process.stderr:
            stderr += process.stderr.read()
    return stdout, stderr


def _custom(root: Path, line: str) -> bool:
    parts = line.split(maxsplit=2)
    command = parts[0].lower()
    if command in {".exit", ".quit"}:
        return False
    if command in {".help", ".?", "help"}:
        print(_paint(CYAN, HELP))
    elif command == ".files":
        print(_line())
        print(_paint(CYAN, "ARCHIVES NORTHSTAR"))
        print(_line("·"))
        print(_paint(CYAN, "dossiers/"))
        print(_paint(CYAN, "evidence/"))
        print(_paint(CYAN, "investigation-report.md"))
        print(_paint(YELLOW, "[Mickael] Six dossiers, puis les preuves techniques : c'est votre fil d'enquête."))
    elif command == ".cat" and len(parts) == 2:
        print(_safe_path(root, parts[1]).read_text())
    elif command == ".find" and len(parts) == 2:
        print("\n".join(str(path.relative_to(root)) for path in sorted(root.glob(parts[1]))))
    elif command == ".grep" and len(parts) == 3:
        path = _safe_path(root, parts[2])
        print("\n".join(line for line in path.read_text().splitlines() if parts[1].lower() in line.lower()))
    else:
        print("Commande inconnue. Tapez .help pour consulter les commandes disponibles.")
    return True


def run_shell_console(root: Path) -> int:
    progress_step = 0
    consulted = set()
    if readline is not None:
        readline.parse_and_bind("set editing-mode emacs")
    log_dir = root / ".student-data"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"session-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.log"
    _write_session_log(log_path, "SESSION_START")
    print(_paint(YELLOW, f"Journal local de session : {log_path.relative_to(root)}"))
    print(_line())
    print(_paint(GREEN, "Console d'enquête prête. Northstar vous attend."))
    print(_paint(YELLOW, "Tapez .help pour afficher les commandes disponibles."))
    print(_line())
    while True:
        try:
            prompt = _paint(CYAN, "northstar> ") if sys.stdout.isatty() else "shell> "
            line = input(prompt).strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        _write_session_log(log_path, f"COMMAND {line}")
        if line.lower() == "help":
            line = ".help"
        if line.startswith("."):
            try:
                if not _custom(root, line):
                    break
            except (OSError, ValueError) as error:
                print(_paint(RED, f"Archive illisible : {error}"))
            continue
        try:
            output, error = _run(root, line)
            _result_header(line)
            print(output, end="")
            if error:
                print(error, end="")
                _write_session_log(log_path, f"COMMAND_ERROR {error.strip()}")
                if "No such file or directory" in error:
                    print(_paint(YELLOW, "[Mickael] Le chemin n'existe pas. Utilisez .files ou ls pour retrouver le nom exact du dossier et du fichier."))
            progress_step, progress = _progress_reaction(line, progress_step, consulted)
            if progress:
                dialogue = f"[Mickael] {progress}"
                print(_paint(YELLOW, dialogue))
                _write_session_log(log_path, f"DIALOGUE {dialogue}")
                _record_stage_answer(root, progress_step, log_path)
            elif any(marker in line.lower() for markers, _ in PROGRESS_STEPS[progress_step:] for marker in markers):
                _write_session_log(log_path, "PROGRESS pending_required_evidence")
        except (OSError, ValueError) as error:
            print(_paint(RED, f"Commande refusée : {error}"))
            _write_session_log(log_path, f"COMMAND_REJECTED {error}")
    _write_session_log(log_path, "SESSION_END")
    return 0
