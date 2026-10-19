"""Restricted terminal console with narrative reactions."""

from __future__ import annotations

import io
import re
import shlex
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

try:
    import readline
except ImportError:  # pragma: no cover - platform fallback
    readline = None


HELP = """Commandes : .files, .cat <fichier>, .find <motif>, .grep <motif> <fichier>, .correct <étape>, .help (ou help), .exit.
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
COMMAND_WORDS = ALLOWED | {"help", ".help", ".files", ".cat", ".find", ".grep", ".correct", ".exit", ".quit"}
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


def _narrative_reaction(command: str) -> str | None:
    """Return a hint only when the command targets a known evidence item."""
    for marker, reaction in NARRATIVE_REACTIONS.items():
        if marker in command:
            return reaction
    return None


PROGRESS_STEPS = (
    (("dossier-01", "dossier-02", "dossier-03", "dossier-04", "dossier-05", "dossier-06"), "Je pensais que l'empreinte validée clôturait la question. Il faut maintenant distinguer ce qu'elle prouve de ce qui s'est passé ensuite."),
    (("evidence/identity/members", "evidence/identity/credentials", "evidence/identity/sessions"), "J'ai d'abord suivi le nom attaché à cred-17. Les sessions me forcent à distinguer le titulaire du compte connecté et de la personne devant l'écran."),
    (("evidence/incident/incident-note",), "Le premier échec de Lydie fixe une borne, pas l'instant de la disparition. Il nous manque encore le dernier état vérifiable."),
    (("evidence/logs/access", "evidence/logs/terminal-history", "evidence/logs/command-audit", "evidence/logs/failed-commands"), "La lecture réussit à 15:41:18 et échoue à 15:43:01 : une fenêtre de 1 min 43. op-417 relie l'export à une opération sur l'archive; ma piste Git n'explique pas encore ce geste."),
    (("evidence/team/notes", "evidence/team/interviews", "team-interview:Kevin", "team-interview:Anthony", "team-interview:Lisa", "team-interview:Lydie", "team-interview:Mickael"), "Lydie n'a pas reconnu le visage. Kevin confirme être passé au poste-04, mais nie avoir touché l'archive. Quelle trace relie cette présence à la session ?"),
    (("evidence/git/branch-log", "evidence/git/reflog"), "Le push arrive 28 secondes après l'opération sur le fichier. J'avais pris la branche pour la cause; la chronologie montre qu'elle accompagne l'incident. Séparons maintenant le compte du titulaire."),
)

# Chaque étape demande une vraie opération de recherche Shell. Les fichiers
# restent lisibles avec ``cat``, mais la progression récompense aussi la
# découverte, le filtrage, l'extraction et le tri des preuves.
STEP_COMMANDS = (
    {"find"},
    {"grep", "cut"},
    {"grep"},
    {"grep", "sort"},
    {"grep", "cut"},
    {"sort"},
)

INTERLUDE_DIALOGUES = {
    (0, "find dossiers"): "Voici les dossiers de l'affaire. Parcourez-les pour comprendre ce qui devait être protégé avant de suivre les traces.",
    (1, "find evidence"): "Le récit ne suffit plus. Conservons chaque hypothèse et vérifions-la dans les traces techniques.",
    (1, "evidence/identity/members"): "Avant d'accuser qui que ce soit, relions les noms aux identifiants qui apparaissent dans les journaux.",
    (2, "evidence/incident/incident-note"): "Le constat fixe le premier échec. Il ne révèle ni l'instant de l'action ni la personne qui l'a faite.",
    (3, "evidence/logs/access"): "Les accès sont proches dans le temps, mais ils ne désignent pas tous la même session. Gardons la chronologie exacte.",
    (4, "evidence/team/interviews"): "Nous avons maintenant des versions humaines. Je vais les confronter aux traces avant de décider lesquelles tiennent.",
    (5, "evidence/git/branch-log"): "Il reste la piste qui m'a d'abord détourné de l'archive. Voyons ce que Git confirme réellement.",
}

FILE_DIALOGUES = {
    "dossier-01": "Le dossier sépare la copie publiée du dépôt. Je n'avais vérifié que l'empreinte; il faut retrouver exactement ce que ce contrôle couvrait.",
    "dossier-02": "Une credential apparaît dans plusieurs sessions. Son titulaire, le compte de session et la personne au terminal ne sont peut-être pas la même personne.",
    "dossier-03": "J'ai traité mon contrôle comme une garantie. Le texte distingue pourtant une empreinte à un instant précis d'un accès réussi plus tard.",
    "dossier-04": "Ces résumés ne sont pas encore des preuves. Je veux entendre les déclarations exactes avant de choisir la version qui m'arrange.",
    "dossier-05": "La branche et l'archive disparaissent dans la même fenêtre, mais pas forcément par la même action. Séparons création, suppression et constat.",
    "dossier-06": "La conclusion devra expliquer la chaîne complète : état, action, session, acteur et propriétaire. Une correspondance isolée ne suffira pas.",
    "identity/members": "La liste relie les noms aux member_id. Ces identifiants permettent maintenant de lire les journaux sans deviner les personnes.",
    "identity/credentials": "cred-17 est au nom d'Anthony, mais ce relevé ne dit pas qui s'en est servi. Je me suis arrêté trop tôt sur cette ligne.",
    "identity/sessions": "La même credential apparaît dans s-31, s-44 et s-52. Les personnes et les terminaux diffèrent; gardez ces trois sessions séparées.",
    "incident/incident-note": "Le constat indique quel fichier ou chemin a disparu et quand cela a été remarqué. Il décrit l'effet, pas encore son auteur.",
    "logs/access": "La lecture de 15:41:18 réussit après mon contrôle d'empreinte. J'avais laissé presque huit minutes sans preuve entre les deux.",
    "logs/terminal-history": "Le terminal montre `rm` après la définition de RELEASE_DIR. Il faut vérifier que l'audit relie bien cette action au chemin de l'archive.",
    "logs/command-audit": "op-417 apparaît sur une opération réussie visant l'archive. La colonne access_ref relie les journaux, mais n'identifie pas encore la personne.",
    "logs/failed-commands": "Le dépôt Git ne contenait pas l'archive, mais cela ne signifie pas qu'elle était absente de l'espace publié. La lecture de Lydie est le premier échec pertinent.",
    "team/notes": "Ces notes donnent le contexte humain autour des horaires et des accès. Utilisez-les comme pistes à vérifier, pas comme preuves isolées.",
    "team/interviews": "Lydie n'a pas identifié la personne qu'elle a vue. Kevin, lui, admet être passé au poste-04 mais nie la suppression. Les sessions peuvent-elles départager ces propos ?",
    "git/branch-log": "La branche est créée avant l'opération sur l'archive, puis poussée après. C'est le journal de commandes, pas le push, qui explique l'effet constaté.",
    "git/reflog": "Le reflog confirme le push à 15:42:44, après l'opération de 15:42:16. J'ai confondu deux événements proches parce qu'ils partageaient le même terminal.",
}

REPORT_STAGES = (
    "Qu'est-ce qui devait être livré, et quelle certitude Mickael avait-il au début ?",
    "Qui possède la credential, et quelles sessions l'ont utilisée ?",
    "À quel moment l'absence est-elle constatée ? Qu'est-ce que ce constat ne prouve pas ?",
    "À quoi correspond op-417, et comment le savez-vous ?",
    "Quel témoignage change votre hypothèse, et quelle trace le corrobore ?",
    "Que confirme Git sur la séquence, le poste et la session ?",
)


def _progress_reaction(
    observed: set[str],
    commands: set[str],
    step: int,
    consulted: set[str],
    used_commands: set[str],
) -> tuple[int, str | None]:
    used_commands.update(commands)
    consulted.update(observed)
    if step >= len(PROGRESS_STEPS):
        return step, None
    required, reaction = PROGRESS_STEPS[step]
    command_complete = STEP_COMMANDS[step].issubset(used_commands)
    if step > 0:
        required_files = tuple(marker for marker in required if "/" in marker)
        command_complete = (
            command_complete
            and STEP_COMMANDS[step].issubset(commands)
            and any(marker in observed for marker in required_files)
        )
    if all(marker in consulted for marker in required) and command_complete:
        return step + 1, reaction
    return step, None


def _interlude_reaction(discovered: set[str], step: int, consulted: set[str]) -> str | None:
    for (expected_step, marker), dialogue in INTERLUDE_DIALOGUES.items():
        if expected_step == step and marker not in consulted and any(marker in item for item in discovered):
            return dialogue
    return None


def _file_dialogue(observed: set[str], reacted_files: set[str]) -> str | None:
    for marker, dialogue in FILE_DIALOGUES.items():
        if marker in observed and marker not in reacted_files:
            reacted_files.add(marker)
            return dialogue
    return None


def _result_evidence(root: Path, command: str, output: str, error: str) -> tuple[set[str], set[str], set[str]]:
    """Identify files whose contents were returned, separately from discovered paths."""
    if error or not output.strip():
        return set(), set(), set()
    tokens = shlex.split(command)
    commands = {part[0] for part in _pipeline_parts(tokens) if part}
    discovered = set()
    for marker in ("dossiers", "evidence"):
        if any(line.strip().startswith(marker + "/") for line in output.splitlines()):
            discovered.add("find " + marker)
    observed = set()
    if commands.intersection({"cat", "grep", "head", "tail", "awk", "cut", "sort"}):
        file_groups = []
        for part in _pipeline_parts(tokens):
            files = []
            for token in part[1:]:
                if token.startswith("-"):
                    continue
                try:
                    path = _safe_path(root, token)
                except ValueError:
                    continue
                if path.is_file():
                    files.append(path)
            if files:
                file_groups.append(files)
        # A command with its own files ignores the upstream pipe. Attribute
        # the final output only to files opened by the last such command.
        for path in (file_groups[-1] if file_groups else []):
            relative = path.relative_to(root.resolve()).as_posix()
            for markers, _ in PROGRESS_STEPS:
                observed.update(marker for marker in markers if relative.startswith((marker + "/", marker + ".", "dossiers/" + marker + "/")))
            observed.update(marker for marker in FILE_DIALOGUES if relative.startswith(("dossiers/" + marker + "/", "evidence/" + marker + ".", "evidence/" + marker + "/")))
            if relative == "evidence/team/interviews.txt":
                for person in ("Kevin", "Anthony", "Lisa", "Lydie", "Mickael"):
                    if any(line.startswith(f"{person}|") for line in output.splitlines()):
                        observed.add(f"team-interview:{person}")
            discovered.add(relative)
    return observed, discovered, commands


def _pipeline_parts(tokens: list[str]) -> list[list[str]]:
    parts: list[list[str]] = [[]]
    for token in tokens:
        if token == "|":
            parts.append([])
        else:
            parts[-1].append(token)
    return parts


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


def _narrate(log_path: Path, dialogue: str, color: str = YELLOW) -> None:
    message = f"[Mickael] {dialogue}"
    print(_paint(color, message))
    _write_session_log(log_path, f"DIALOGUE {message}")


def _looks_like_command(value: str) -> bool:
    first_word = value.split(maxsplit=1)[0].lower()
    return first_word in COMMAND_WORDS


def _record_stage_answer(
    root: Path, stage: int, log_path: Path, *, correction: bool = False
) -> None:
    """Store one student answer without replacing an existing answer."""
    report = root / "investigation-report.md"
    if stage < 1 or stage > len(REPORT_STAGES) or not report.exists():
        return
    content = report.read_text()
    marker = f"<!-- NORTHSTAR_STAGE_{stage} -->"
    completed_marker = f"<!-- NORTHSTAR_STAGE_{stage}_COMPLETED -->"
    note_start_marker = f"<!-- NORTHSTAR_STAGE_{stage}_NOTE_BEGIN -->"
    note_end_marker = f"<!-- NORTHSTAR_STAGE_{stage}_NOTE_END -->"
    completion_count = content.count(completed_marker)
    has_answer = completion_count == 1
    has_note_markers = note_start_marker in content or note_end_marker in content
    if completion_count > 1:
        dialogue = "[Mickael] Les marqueurs de cette étape sont incohérents. Le rapport reste intact."
        print(_paint(YELLOW, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=malformed_report_markers")
        return
    if has_note_markers:
        note_start = content.find(note_start_marker)
        note_end = content.find(note_end_marker)
        completion = content.find(completed_marker)
        if (
            content.count(note_start_marker) != 1
            or content.count(note_end_marker) != 1
            or not note_start < note_end < completion
        ):
            dialogue = "[Mickael] Les marqueurs de cette étape sont incohérents. Le rapport reste intact."
            print(_paint(YELLOW, dialogue))
            _write_session_log(log_path, f"DIALOGUE {dialogue}")
            _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=malformed_report_markers")
            return
    if correction and not has_answer:
        dialogue = f"[Mickael] Aucune réponse enregistrée pour l'étape {stage}; il n'y a rien à corriger."
        print(_paint(YELLOW, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=no_existing_answer")
        return
    if has_answer:
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
            answer = input(_paint(CYAN, "Nouvelle note : ")).strip()
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
        note_start = content.find(note_start_marker)
        note_end = content.find(note_end_marker)
        if has_note_markers:
            value_start = content.find("\n", note_start) + 1
            updated = content[:value_start] + answer + "\n" + content[note_end:]
        else:
            heading = re.search(rf"(?m)^### Étape {stage}\s*:.*$", content)
            completion_position = content.find(completed_marker)
            legacy_note = (
                content[heading.end():completion_position].strip("\n")
                if heading and completion_position > heading.end()
                else ""
            )
            if len(legacy_note.splitlines()) != 1 or not legacy_note.strip():
                dialogue = "[Mickael] Je ne peux pas isoler cette ancienne note sans risquer d'effacer autre chose. Rien n'a été modifié."
                print(_paint(YELLOW, dialogue))
                _write_session_log(log_path, f"DIALOGUE {dialogue}")
                _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=ambiguous_legacy_note")
                return
            updated = (
                content[:heading.end()]
                + "\n"
                + answer
                + "\n"
                + content[completion_position:]
            )
        report.write_text(updated)
        dialogue = f"[Mickael] Réponse de l'étape {stage} corrigée."
        print(_paint(GREEN, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_CORRECTION stage={stage} status=updated")
        return
    if correction:
        return
    if marker not in content:
        dialogue = "[Mickael] Cette rubrique de rapport est introuvable. Aucune écriture effectuée."
        print(_paint(RED, dialogue))
        _write_session_log(log_path, f"DIALOGUE {dialogue}")
        _write_session_log(log_path, f"REPORT_NOTE stage={stage} status=missing_marker")
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
    note = f"{note_start_marker}\n{answer}\n{note_end_marker}\n{completed_marker}"
    updated = content.replace(marker, note, 1)
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


def _validate_read_command(root: Path, parts: list[str]) -> None:
    """Accept only the small, side-effect-free forms used in the investigation."""
    name, args = parts[0], parts[1:]
    if name not in ALLOWED:
        raise ValueError("Commande interdite. Utilisez une commande de lecture Shell.")
    if name == "find":
        if not args or args[0].startswith("-"):
            raise ValueError("find attend un dossier et des critères de recherche.")
        _safe_path(root, args[0])
        index = 1
        while index < len(args):
            option = args[index]
            if option == "-print":
                index += 1
            elif option in {"-type", "-name", "-maxdepth", "-mindepth"} and index + 1 < len(args):
                value = args[index + 1]
                if option == "-type" and value not in {"f", "d"}:
                    raise ValueError("Type find interdit.")
                if option in {"-maxdepth", "-mindepth"} and not value.isdecimal():
                    raise ValueError("Profondeur find invalide.")
                index += 2
            else:
                raise ValueError("Option find interdite.")
        return
    if name == "awk":
        if len(args) not in {1, 2} or not re.fullmatch(r"\{\s*print\s+\$[1-9][0-9]*\s*\}", args[0]):
            raise ValueError("awk accepte uniquement {print $N}.")
        if len(args) == 2:
            _safe_path(root, args[1])
        return
    simple_flags = {
        "cat": set(), "grep": set("niFEv"), "cut": set(),
        "sort": set("rnu"), "head": set(), "tail": set(),
        "wc": set("lwc"), "pwd": set(), "ls": set("la"),
    }
    index = 0
    operands = []
    while index < len(args):
        arg = args[index]
        if arg == "--":
            operands.extend(args[index + 1:])
            break
        if name in {"head", "tail"} and arg == "-n" and index + 1 < len(args) and args[index + 1].isdecimal():
            index += 2
            continue
        if name == "cut" and arg in {"-d", "-f"} and index + 1 < len(args):
            value = args[index + 1]
            if (arg == "-d" and len(value) != 1) or (arg == "-f" and not re.fullmatch(r"[0-9]+(?:-[0-9]*)?(?:,[0-9]+(?:-[0-9]*)?)*", value)):
                raise ValueError("Option cut invalide.")
            index += 2
            continue
        if name == "cut" and arg.startswith(("-d", "-f")):
            option, value = arg[:2], arg[2:]
            if (option == "-d" and len(value) == 1) or (
                option == "-f" and re.fullmatch(r"[0-9]+(?:-[0-9]*)?(?:,[0-9]+(?:-[0-9]*)?)*", value)
            ):
                index += 1
                continue
            raise ValueError("Option cut invalide.")
        if arg.startswith("-") and arg != "-":
            if len(arg) < 2 or not set(arg[1:]).issubset(simple_flags[name]):
                raise ValueError(f"Option {name} interdite.")
        else:
            operands.append(arg)
        index += 1
    if name == "pwd" and operands:
        raise ValueError("pwd n'accepte pas de chemin.")
    if name == "grep":
        if not operands:
            raise ValueError("grep attend un motif.")
        operands = operands[1:]
    for operand in operands:
        if operand != "-":
            _safe_path(root, operand)


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
        _validate_read_command(root, parts)

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
            process.stderr.close()
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
    elif command == ".cat" and len(parts) == 2:
        print(_safe_path(root, parts[1]).read_text())
    elif command == ".find" and len(parts) == 2:
        _safe_path(root, parts[1])
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
    used_commands = set()
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
        if line.lower().startswith(".correct"):
            parts = line.split()
            if (
                len(parts) != 2
                or not parts[1].isdecimal()
                or not 1 <= int(parts[1]) <= len(REPORT_STAGES)
            ):
                print(_paint(YELLOW, "Utilisation : .correct <étape de 1 à 6>"))
            else:
                _record_stage_answer(root, int(parts[1]), log_path, correction=True)
            continue
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
                if line.split(maxsplit=1)[0].lower() == ".files":
                    _narrate(log_path, "Les archives sont classées en deux ensembles. Commencez par les six dossiers narratifs, puis confrontez leurs récits aux preuves techniques.")
                if line.split(maxsplit=1)[0].lower() == ".cat" and len(line.split()) == 2:
                    observed, discovered, commands = _result_evidence(root, "cat " + shlex.quote(line.split(maxsplit=1)[1]), rendered_output, "")
                    dialogue = _file_dialogue(observed, reacted_files)
                    if dialogue:
                        _narrate(log_path, dialogue)
                    progress_step, progress = _progress_reaction(observed, commands, progress_step, consulted, used_commands)
                    if progress:
                        _narrate(log_path, progress, GREEN)
                        _record_stage_answer(root, progress_step, log_path)
                        used_commands.clear()
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
                    _narrate(log_path, "Ce chemin n'existe pas. Retrouvez son nom exact dans .files ou avec ls.")
            observed, discovered, commands = _result_evidence(root, line, output, error)
            file_dialogue = _file_dialogue(observed, reacted_files)
            if file_dialogue:
                _narrate(log_path, file_dialogue)
            interlude = _interlude_reaction(discovered, progress_step, consulted)
            if interlude:
                _narrate(log_path, interlude)
            progress_step, progress = _progress_reaction(
                observed, commands, progress_step, consulted, used_commands
            )
            if progress:
                _narrate(log_path, progress, GREEN)
                _record_stage_answer(root, progress_step, log_path)
                used_commands.clear()
            elif observed:
                _write_session_log(log_path, "PROGRESS pending_required_evidence")
        except (OSError, ValueError) as error:
            print(_paint(RED, f"Commande refusée : {error}"))
            _write_session_log(log_path, f"OUTPUT_ERROR command_rejected={error}")
    _write_session_log(log_path, "SESSION_END")
    return 0
