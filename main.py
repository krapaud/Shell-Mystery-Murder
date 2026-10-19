"""Start the Northstar Shell Mystery investigation."""

import sys
from pathlib import Path

from game.investigation_shell import run_shell_console
from game.validate_answer import validate

ROOT = Path(__file__).parent


class Theme:
    """ANSI theme used by the terminal briefing."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"


def title(text: str) -> None:
    print(f"{Theme.BOLD}{Theme.CYAN}{'=' * 62}{Theme.RESET}")
    print(f"{Theme.BOLD}{Theme.CYAN}{text.center(62)}{Theme.RESET}")
    print(f"{Theme.BOLD}{Theme.CYAN}{'=' * 62}{Theme.RESET}")


def section(label: str, text: str, color: str = Theme.YELLOW) -> None:
    print(f"\n{Theme.BOLD}{color}[ {label} ]{Theme.RESET}")
    print(text)


def main() -> int:
    arguments = sys.argv[1:]
    if not arguments:
        title("Northstar : L'archive disparue")
        section(
            "ALERTE",
            "L'archive de livraison a disparu quelques minutes avant la présentation.\n"
            "Une branche hotfix/release est apparue dans le dépôt.",
            Theme.RED,
        )
        section(
            "BRIEFING DE MICKAEL",
            "Le contrôle d'intégrité était terminé avant l'incident.\n"
            "Votre mission consiste à retrouver la chronologie, le propriétaire\n"
            "de l'accès utilisé et l'acteur présent sur le terminal.",
        )
        section(
            "MÉTHODE",
            "1. Ouvrez les six dossiers narratifs.\n"
            "2. Recoupez-les avec les preuves techniques.\n"
            "3. Écartez les actions légitimes.\n"
            "4. Rédigez votre rapport avant de conclure.",
            Theme.GREEN,
        )
        print(f"\n{Theme.BOLD}Quand votre preuve est complète, utilisez :{Theme.RESET}")
        print("python3 main.py --answer 'PROPRIETAIRE|ACTEUR'")
        return run_shell_console(ROOT)
    if arguments[0] != "--answer":
        print("Utilisez uniquement l'option --answer pour envoyer votre preuve.")
        return 1
    if len(arguments) != 2:
        print("Indiquez une preuve après --answer.")
        return 1
    report = ROOT / "investigation-report.md"
    content = report.read_text(encoding="utf-8") if report.exists() else ""
    if not all(f"<!-- NORTHSTAR_STAGE_{stage}_COMPLETED -->" in content for stage in range(1, 7)):
        print("Le rapport comporte encore des étapes incomplètes. Terminez l'enquête avant de conclure.")
        return 1
    return validate(arguments[1])


if __name__ == "__main__":
    raise SystemExit(main())
