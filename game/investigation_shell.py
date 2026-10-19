"""Restricted terminal console with narrative reactions."""

import shlex
import subprocess
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
        print(HELP)
    elif command == ".files":
        print("dossiers/")
        print("evidence/")
        print("investigation-report.md")
        print("[Mickael] Six dossiers, puis les preuves techniques : c'est votre fil d'enquête.")
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
    print("Console d'enquête prête. Tapez .help pour commencer.")
    while True:
        try:
            line = input("shell> ").strip()
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
                print(f"Archive illisible : {error}")
            continue
        try:
            output, error = _run(root, line)
            print(output, end="")
            if error:
                print(error, end="")
            table = next((key for key in REACTIONS if key in line), None)
            if table:
                print(f"[Mickael] {REACTIONS[table]}")
        except (OSError, ValueError) as error:
            print(f"Commande refusée : {error}")
    return 0
