"""Restricted terminal console with narrative reactions."""

import io
import shlex
import subprocess
import sys
from contextlib import redirect_stdout
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
COMMAND_WORDS = ALLOWED | {"help", ".help", ".files", ".cat", ".find", ".grep", ".exit", ".quit"}
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
    (("dossier-01", "dossier-02", "dossier-03", "dossier-04", "dossier-05", "dossier-06"), "Les six dossiers sont parcourus. Le contexte est posé ; vous pouvez maintenant confronter le récit aux preuves techniques."),
    (("evidence/identity/members", "evidence/identity/credentials", "evidence/identity/sessions"), "Les identités sont séparées des actions. Les correspondances sont prêtes à être vérifiées."),
    (("evidence/incident/incident-note",), "Le constat est établi. Il décrit le résultat, pas encore l'auteur."),
    (("evidence/logs/access", "evidence/logs/terminal-history", "evidence/logs/command-audit", "evidence/logs/failed-commands"), "La chronologie technique se précise. Comparez les succès, les actions et le premier échec."),
    (("evidence/team/notes", "evidence/team/interviews"), "Les témoignages sont confrontés aux traces. Une déclaration ne vaut que si les horaires la confirment."),
    (("evidence/git/branch-log", "evidence/git/reflog"), "Git confirme l'ordre des opérations. Utilisez-le pour vérifier la chronologie, pas pour conclure seul."),
)

INTERLUDE_DIALOGUES = {
    (0, "find dossiers"): "Voici les dossiers de l'affaire. Parcourez-les pour comprendre ce qui devait être protégé avant de suivre les traces.",
    (6, "find evidence"): "Le contexte est posé. Les preuves techniques vont maintenant permettre de vérifier ce que les dossiers racontent.",
    (6, "evidence/identity/members"): "Commencez par les identités. Les noms seuls ne suffisent pas : les identifiants feront le lien entre les archives.",
    (7, "evidence/incident/incident-note"): "Le constat de disparition donne un point fixe dans le temps. Il faudra encore retrouver ce qui s'est passé avant.",
    (8, "evidence/logs/access"): "Les journaux d'accès ouvrent la chronologie. Cherchez les actions qui se répondent plutôt qu'une ligne isolée.",
    (9, "evidence/team/interviews"): "Les témoignages apportent les intentions et les alibis. Confrontez-les aux traces avant de les retenir.",
    (10, "evidence/git/branch-log"): "La piste Git arrive en dernier. Elle peut confirmer l'ordre des opérations, mais elle ne remplacera pas les autres preuves.",
}

FILE_DIALOGUES = {
    "dossier-01": "Le briefing sépare déjà le dépôt, l'archive et les accès. Notez ces rôles : ils serviront à lire les preuves sans les confondre.",
    "dossier-02": "Ici, les droits sont associés à des identifiants précis. La prochaine question est de savoir quelle session les a réellement utilisés.",
    "dossier-03": "Le contrôle d'intégrité fournit une heure de référence. Toute action liée à la disparition devra être comparée à ce repère.",
    "dossier-04": "Les déclarations décrivent des observations différentes. Gardez leurs horaires et leurs formulations pour les confronter aux traces techniques.",
    "dossier-05": "Ce dossier place le renommage, la branche et la disparition dans la même fenêtre. Il faudra vérifier l'ordre exact dans les logs.",
    "dossier-06": "Les questions finales distinguent propriétaire de l'accès, utilisateur de la session et acteur de l'action. Une seule preuve ne suffira pas.",
    "identity/members": "La liste relie les noms aux member_id. Ces identifiants permettent maintenant de lire les journaux sans deviner les personnes.",
    "identity/credentials": "Chaque credential a un propriétaire et un périmètre. Un propriétaire d'accès n'est pas automatiquement l'acteur devant le terminal.",
    "identity/sessions": "Les sessions ajoutent un terminal et une période à chaque utilisateur. Comparez ces horaires avec ceux des commandes et des accès.",
    "incident/incident-note": "Le constat indique quel fichier ou chemin a disparu et quand cela a été remarqué. Il décrit l'effet, pas encore son auteur.",
    "logs/access": "Ces lignes combinent action, credential, session et cible. Relevez ces quatre champs : c'est leur correspondance qui donnera du poids à la piste.",
    "logs/terminal-history": "L'historique montre les commandes réellement saisies, notamment la variable de chemin et les opérations Git. Il faudra les rattacher à une session.",
    "logs/command-audit": "L'audit précise le terminal, l'action et son statut. Une opération réussie ne doit pas être confondue avec une simple tentative.",
    "logs/failed-commands": "Les échecs indiquent ce qui a été tenté sans modifier l'état attendu. Ils peuvent préciser l'intention et la chronologie, mais pas prouver seuls le vol.",
    "team/notes": "Ces notes donnent le contexte humain autour des horaires et des accès. Utilisez-les comme pistes à vérifier, pas comme preuves isolées.",
    "team/interviews": "Les témoignages apportent des déclarations et des horaires. La piste devient solide seulement si les logs confirment ce qui a été observé.",
    "git/branch-log": "Le journal Git montre les mouvements de la branche et les changements publiés. Comparez chaque horodatage avec la fenêtre de disparition.",
    "git/reflog": "Le reflog complète le journal de branche en conservant l'ordre local des opérations. Il peut confirmer une séquence, pas l'identité à lui seul.",
}

REPORT_STAGES = (
    "Quels sont le projet, le fichier recherché, les rôles et les questions de l'enquête ?",
    "Quelles correspondances avez-vous trouvées entre membres, sessions, credentials et terminaux ?",
    "Que constate exactement la note d'incident, sans en déduire l'auteur ?",
    "Quelle chronologie pouvez-vous établir à partir des logs ?",
    "Quelles déclarations sont confirmées ou contredites par les traces ?",
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


def _interlude_reaction(command: str, step: int, consulted: set[str]) -> Optional[str]:
    lowered = command.lower()
    for (expected_step, marker), dialogue in INTERLUDE_DIALOGUES.items():
        if expected_step == step and marker in lowered and marker not in consulted:
            return dialogue
    return None


def _file_dialogue(command: str, reacted_files: set[str]) -> Optional[str]:
    lowered = command.lower()
    for marker, dialogue in FILE_DIALOGUES.items():
        if marker in lowered and marker not in reacted_files:
            reacted_files.add(marker)
            return dialogue
    return None


def _write_session_log(log_path: Path, message: str) -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"[{timestamp}] {message}\n")


def _write_session_block(log_path: Path, label: str, content: str) -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"[{timestamp}] {label}_BEGIN\n")
        log.write(content if content.endswith("\n") else f"{content}\n")
        log.write(f"[{timestamp}] {label}_END\n")


def _looks_like_command(value: str) -> bool:
    first_word = value.split(maxsplit=1)[0].lower()
    return first_word in COMMAND_WORDS


def _record_stage_answer(root: Path, stage: int, log_path: Path) -> None:
    """Store one student answer without replacing an existing answer."""
    report = root / "investigation-report.md"
    if stage < 1 or stage > len(REPORT_STAGES) or not report.exists():
        return
    dialogue = f"[Mickael] Étape {stage} validée. {REPORT_STAGES[stage - 1]}"
    print(_paint(GREEN, dialogue))
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
    _write_session_log(log_path, f"INPUT report_stage={stage} value={answer}")
    if not answer:
        dialogue = "[Mickael] Réponse vide : rien n'a été écrit dans le rapport."
        print(_paint(YELLOW, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_NOTE stage={stage} status=empty")
        return
    if _looks_like_command(answer):
        dialogue = "[Mickael] Cette étape attend une note d'enquête, pas une commande. La réponse n'a pas été enregistrée."
        print(_paint(YELLOW, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_NOTE stage={stage} status=command_rejected")
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
        _write_session_log(log_path, f"INPUT report_correction_stage={stage} value={answer}")
        if not answer:
            dialogue = "[Mickael] Réponse vide : la réponse existante est conservée."
            print(_paint(YELLOW, dialogue))
            _write_session_log(log_path, f"DIALOGUE {dialogue}")
            _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=empty")
            return
        if _looks_like_command(answer):
            dialogue = "[Mickael] Cette étape attend une note d'enquête, pas une commande. La réponse existante est conservée."
            print(_paint(YELLOW, dialogue))
            _write_session_log(log_path, f"DIALOGUE {dialogue}")
            _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=command_rejected")
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
        print(_paint(YELLOW, "[Mickael] Les archives sont classées en deux ensembles. Commencez par consulter les six dossiers narratifs, puis confrontez leur récit aux preuves techniques."))
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
    reacted_files = set()
    if readline is not None:
        readline.parse_and_bind("set editing-mode emacs")
    log_dir = root / ".student-data"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "session-current.log"
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
        _write_session_log(log_path, f"INPUT command={line}")
        if line.lower() == "help":
            line = ".help"
        if line.startswith("."):
            custom_output = io.StringIO()
            try:
                with redirect_stdout(custom_output):
                    should_continue = _custom(root, line)
                rendered_output = custom_output.getvalue()
                print(rendered_output, end="")
                if rendered_output:
                    _write_session_block(log_path, "OUTPUT", rendered_output)
                if not should_continue:
                    break
            except (OSError, ValueError) as error:
                print(_paint(RED, f"Archive illisible : {error}"))
                _write_session_log(log_path, f"OUTPUT_ERROR custom_command={error}")
            continue
        try:
            output, error = _run(root, line)
            _result_header(line)
            print(output, end="")
            if output:
                _write_session_block(log_path, "OUTPUT", output)
            if error:
                print(error, end="")
                _write_session_block(log_path, "OUTPUT_ERROR", error)
                if "No such file or directory" in error:
                    print(_paint(YELLOW, "[Mickael] Le chemin n'existe pas. Utilisez .files ou ls pour retrouver le nom exact du dossier et du fichier."))
            file_dialogue = None if error else _file_dialogue(line, reacted_files)
            if file_dialogue:
                dialogue = f"[Mickael] {file_dialogue}"
                print(_paint(YELLOW, dialogue))
                _write_session_log(log_path, f"DIALOGUE {dialogue}")
            interlude = _interlude_reaction(line, progress_step, consulted)
            if interlude:
                dialogue = f"[Mickael] {interlude}"
                print(_paint(YELLOW, dialogue))
                _write_session_log(log_path, f"DIALOGUE {dialogue}")
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
            _write_session_log(log_path, f"OUTPUT_ERROR command_rejected={error}")
    _write_session_log(log_path, "SESSION_END")
    return 0
