"""Start the Northstar Shell Mystery investigation."""

import sys
from pathlib import Path

from game.investigation_shell import run_shell_console
from game.validate_answer import validate

ROOT = Path(__file__).parent


def main() -> int:
    arguments = sys.argv[1:]
    if not arguments:
        print("Northstar — L'archive disparue")
        print("Mickael vous appelle : l'archive de livraison a disparu.")
        print("Retrouvez la session, la credential utilisée et l'acteur de l'action.")
        print("Quand votre preuve est complète, quittez la console et relancez avec --answer 'PROPRIETAIRE|ACTEUR'.")
        return run_shell_console(ROOT)
    if arguments[0] != "--answer":
        print("Utilisez uniquement l'option --answer pour envoyer votre preuve.")
        return 1
    if len(arguments) != 2:
        print("Indiquez une preuve après --answer.")
        return 1
    return validate(arguments[1])


if __name__ == "__main__":
    raise SystemExit(main())
