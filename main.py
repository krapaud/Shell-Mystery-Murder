"""Start the Northstar Shell Mystery investigation."""

import sys
from pathlib import Path

from game.investigation_shell import run_shell_console
from game.report_validation import validate_report
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
            "À moins de vingt minutes de la présentation, Lydie signale que\n"
            "l'archive publiée ne s'ouvre plus. Une branche hotfix/release vient\n"
            "d'apparaître dans le dépôt, et les récits ne concordent pas.",
            Theme.RED,
        )
        section(
            "BRIEFING DE MICKAEL",
            "À 15:33, j'ai validé l'empreinte et cru que la revue était couverte.\n"
            "À 15:43, Lydie m'a dit que l'archive n'était plus là. Je ne relancerai\n"
            "rien avant d'avoir compris ce qui s'est passé entre les deux.",
        )
        section(
            "MÉTHODE",
            "1. Comprenez ce que chacun affirme avoir fait.\n"
            "2. Rassemblez les fragments et suivez la référence trouvée.\n"
            "3. Distinguez le droit utilisé de la personne au terminal.\n"
            "4. Rédigez votre rapport avant de conclure.",
            Theme.GREEN,
        )
        print(f"\n{Theme.BOLD}Quand votre preuve est complète, utilisez :{Theme.RESET}")
        print("python3 main.py --answer 'PROPRIETAIRE|PERSONNE_PROBABLE'")
        return run_shell_console(ROOT)
    if arguments[0] != "--answer":
        print("Utilisez uniquement l'option --answer pour envoyer votre preuve.")
        return 1
    if len(arguments) != 2:
        print("Indiquez une preuve après --answer.")
        return 1
    report = ROOT / "investigation-report.md"
    content = report.read_text(encoding="utf-8") if report.exists() else ""
    report_issues = validate_report(content)
    if report_issues:
        print("Le rapport d'enquête est incomplet :")
        for issue in report_issues:
            print(f"- {issue}")
        return 1
    result = validate(arguments[1])
    if result == 0:
        print(
            "Les traces étayent cette attribution; elles identifient une session et un compte, "
            "mais ne constituent pas une identification visuelle de la personne."
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
