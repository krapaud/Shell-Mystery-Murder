"""Validate the final structured proof without exposing it."""

import hashlib


ANSWER_DIGEST = "686d8b3ffb1f06eccefd53f4405496e0fafee01e4e8414b47a5467205abeb92d"


def validate(candidate: str) -> int:
    digest = hashlib.sha256(candidate.strip().upper().encode()).hexdigest()
    if digest == ANSWER_DIGEST:
        print("Félicitations, votre conclusion correspond aux éléments attendus.")
        print("Mickael peut clôturer l'enquête Northstar.")
        return 0
    print("La preuve est incomplète. Recoupez la credential, la session et l'attribution humaine probable.")
    return 1
