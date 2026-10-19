"""Restricted terminal console with narrative reactions."""

import shlex
import subprocess
import sys
from pathlib import Path


HELP = """Commandes : .files, .cat <fichier>, .find <motif>, .grep <motif> <fichier>, .help, .exit.
Les commandes Shell de lecture (find, cat, grep, cut, sort, awk, head, tail)
peuvent aussi être utilisées. Les écritures et suppressions sont interdites."""
REACTIONS = {
    "dossiers": "Les dossiers racontent l'affaire par fragments. Confrontez leur récit aux preuves.",
    "evidence": "Une trace technique décrit un fait. Vérifiez l'identité liée à la session.",
    "identity": "Un propriétaire de credential n'est pas forcément l'acteur du terminal.",
    "logs": "Les heures commencent à former une chronologie. Cherchez une confirmation indépendante.",
    "git": "Git montre les branches et les auteurs, mais le terminal indique qui était présent.",
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


def _safe_path(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if root.resolve() not in candidate.parents and candidate != root.resolve():
        raise ValueError("Chemin hors du dossier d'enquête.")
    return candidate


def _run(root: Path, command: str) -> tuple[str, str]:
    parts = shlex.split(command)
    if not parts or parts[0] not in ALLOWED:
        raise ValueError("Commande interdite. Utilisez une commande de lecture Shell.")
    for part in parts[1:]:
        if part.startswith("-") or part in {"|", ">", ">>", ";", "&&"}:
            continue
        if "/" in part or part in {"dossiers", "evidence"}:
            _safe_path(root, part)
    result = subprocess.run(parts, cwd=root, capture_output=True, text=True, check=False)
    return result.stdout, result.stderr


def _custom(root: Path, line: str) -> bool:
    parts = line.split(maxsplit=2)
    command = parts[0].lower()
    if command in {".exit", ".quit"}:
        return False
    if command in {".help", ".?"}:
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
            table = next((key for key in REACTIONS if key in line), None)
            if table:
                print(_paint(YELLOW, f"[Mickael] {REACTIONS[table]}"))
        except (OSError, ValueError) as error:
            print(_paint(RED, f"Commande refusée : {error}"))
    return 0
