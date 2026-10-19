"""Restricted terminal console with narrative reactions."""

import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional


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
                if "No such file or directory" in error:
                    print(_paint(YELLOW, "[Mickael] Le chemin n'existe pas. Utilisez .files ou ls pour retrouver le nom exact du dossier et du fichier."))
            reaction = _narrative_reaction(line)
            if reaction:
                print(_paint(YELLOW, f"[Mickael] {reaction}"))
        except (OSError, ValueError) as error:
            print(_paint(RED, f"Commande refusée : {error}"))
    return 0
