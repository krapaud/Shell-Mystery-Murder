"""Structural checks for the student's investigation report."""

import re
from typing import Optional

STAGE_MARKERS = tuple(
    f"<!-- NORTHSTAR_STAGE_{stage}_COMPLETED -->" for stage in range(1, 7)
)

REPORT_SECTIONS = (
    "Chronologie",
    "Accès et personnes",
    "Fausses pistes écartées",
    "Preuves retenues",
    "Analyse de l'incident",
    "Conclusion",
)

TABLE_HEADERS = {
    "Chronologie": ("heure", "fait", "source", "certitude"),
    "Accès et personnes": ("élément", "observation", "source"),
    "Fausses pistes écartées": ("piste écartée", "raison de l'exclusion", "source"),
    "Preuves retenues": (
        "famille de preuve",
        "source consultée",
        "ce qu'elle établit",
    ),
}

TIME_PATTERN = re.compile(r"(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)")
SOURCE_PATTERN = re.compile(
    r"(?i)(?:\b(?:evidence|dossiers)/[\w./-]+|\b[\w.-]+\.(?:txt|log|md|csv)\b)"
)
CERTAINTY_PATTERN = re.compile(
    r"(?i)certitude|certain(?:e)?|probable|infér(?:é|ée|ence)|confirm(?:é|ée|e|ation)|possible|incertain(?:e)?|estim(?:é|ée|e)"
)
REASON_PATTERN = re.compile(
    r"(?i)\b(car|parce que|puisque|donc|contredit|n'explique pas|ne confirme pas|ne montre pas|aucune preuve)\b"
)

ANALYSIS_FIELDS = {
    "Action qui explique la disparition": 10,
    "Session et terminal concernés": 8,
    "Credential utilisée et son propriétaire": 8,
    "Acteur au terminal": 3,
    "Lien entre propriétaire, utilisateur et acteur": 12,
}


def _section_bodies(content: str) -> dict[str, list[str]]:
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    headings = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", content))
    sections: dict[str, list[str]] = {}
    for index, heading in enumerate(headings):
        name = heading.group(1).strip()
        if name not in REPORT_SECTIONS:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
        sections.setdefault(name, []).append(content[heading.end() : end])
    return sections


def _text_size(value: str) -> int:
    cleaned = re.sub(r"[*`_\[\]()]", "", value).strip()
    if cleaned.casefold() in {
        "",
        "à compléter",
        "à renseigner",
        "todo",
        "tbd",
        "...",
        "inconnu",
        "inconnue",
        "unknown",
        "n/a",
        "none",
    }:
        return 0
    return sum(character.isalnum() for character in cleaned)


def _table_rows(body: str, expected_header: tuple[str, ...]) -> list[list[str]]:
    rows = []
    header_skipped = False
    for line in body.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [re.sub(r"[*`_]", "", cell).strip() for cell in stripped[1:-1].split("|")]
        normalized = tuple(cell.casefold() for cell in cells)
        if all(not cell or re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if not header_skipped:
            header_skipped = True
            continue
        if normalized == expected_header:
            continue
        if any(_text_size(cell) for cell in cells):
            rows.append(cells)
    return rows


def _prose_entries(body: str) -> list[str]:
    bullets = []
    prose = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("|", "#")):
            continue
        item = re.match(r"(?:[-*+]\s+|\d+[.)]\s+)(.+)$", stripped)
        if item:
            if _text_size(item.group(1)) >= 12:
                bullets.append(item.group(1).strip())
        elif _text_size(stripped) >= 12:
            prose.append(stripped)
    if bullets and prose:
        return bullets + prose
    if bullets:
        return bullets
    if len(prose) > 1:
        return prose
    combined = " ".join(prose)
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ])", combined)
        if _text_size(sentence) >= 12
    ]


def _field_value(body: str, label: str) -> Optional[str]:  # noqa: UP045
    pattern = re.compile(
        rf"^\s*(?:[-*]\s*)?{re.escape(label)}\s*:\s*(.*?)\s*$",
        re.IGNORECASE,
    )
    matches = [
        match.group(1)
        for line in body.splitlines()
        if (match := pattern.match(re.sub(r"\*\*|__|`", "", line)))
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _complete_rows(
    rows: list[list[str]], minimums: tuple[int, ...]
) -> list[list[str]]:
    return [
        row
        for row in rows
        if len(row) == len(minimums)
        and all(_text_size(cell) >= minimum for cell, minimum in zip(row, minimums))
    ]


def validate_report(content: str) -> list[str]:
    """Return non-spoiling structural issues that prevent final validation."""
    issues = []
    if any(content.count(marker) != 1 for marker in STAGE_MARKERS):
        issues.append("Les six étapes de progression ne sont pas toutes enregistrées une seule fois.")

    sections = _section_bodies(content)
    for name in REPORT_SECTIONS:
        if len(sections.get(name, [])) != 1:
            issues.append(f"La rubrique « {name} » est absente ou dupliquée.")

    if any(len(sections.get(name, [])) != 1 for name in REPORT_SECTIONS):
        return issues

    chronology = sections["Chronologie"][0]
    chronology_rows = _complete_rows(
        _table_rows(chronology, TABLE_HEADERS["Chronologie"]), (3, 10, 3, 3)
    )
    chronology_rows = [row for row in chronology_rows if TIME_PATTERN.search(row[0])]
    chronology_entries = _prose_entries(chronology)
    chronology_entries = [
        entry
        for entry in chronology_entries
        if TIME_PATTERN.search(entry)
        and SOURCE_PATTERN.search(entry)
        and CERTAINTY_PATTERN.search(entry)
    ]
    if len(chronology_rows) + len(chronology_entries) < 3:
        issues.append("Chronologie : renseignez au moins trois événements avec heure, fait, source et certitude.")

    access = sections["Accès et personnes"][0]
    access_rows = _complete_rows(
        _table_rows(access, TABLE_HEADERS["Accès et personnes"]), (3, 10, 3)
    )
    access_entries = _prose_entries(access)
    access_entries = [entry for entry in access_entries if SOURCE_PATTERN.search(entry)]
    if len(access_rows) + len(access_entries) < 2:
        issues.append("Accès et personnes : ajoutez au moins deux observations sourcées.")

    false_body = sections["Fausses pistes écartées"][0]
    false_rows = _complete_rows(
        _table_rows(false_body, TABLE_HEADERS["Fausses pistes écartées"]), (4, 15, 3)
    )
    false_entries = _prose_entries(false_body)
    false_entries = [
        entry
        for entry in false_entries
        if _text_size(entry) >= 20
        and REASON_PATTERN.search(entry)
        and SOURCE_PATTERN.search(entry)
    ]
    if not false_rows and not false_entries:
        issues.append("Fausses pistes : expliquez au moins une piste écartée et la raison.")

    evidence_body = sections["Preuves retenues"][0]
    evidence_rows = _complete_rows(
        _table_rows(evidence_body, TABLE_HEADERS["Preuves retenues"]), (3, 3, 10)
    )
    evidence_entries = _prose_entries(evidence_body)
    families = [row[0].casefold() for row in evidence_rows]
    cited_entries = [
        entry
        for entry in evidence_entries
        if ":" in entry and SOURCE_PATTERN.search(entry) and _text_size(entry) >= 20
    ]
    families.extend(
        re.split(r"\s*:\s*", entry, maxsplit=1)[0].casefold()
        for entry in cited_entries
    )
    evidence_count = len(set(families))
    if evidence_count < 3:
        issues.append("Preuves retenues : présentez trois familles distinctes, leur source et ce qu'elles établissent.")

    analysis = sections["Analyse de l'incident"][0]
    for label, minimum in ANALYSIS_FIELDS.items():
        value = _field_value(analysis, label)
        if value is None or _text_size(value) < minimum:
            issues.append(f"Analyse de l'incident : renseignez le champ « {label} ».")

    conclusion = sections["Conclusion"][0]
    for label, minimum in (("Responsable", 3), ("Certitude", 3), ("Justification", 30)):
        value = _field_value(conclusion, label)
        if value is None or _text_size(value) < minimum:
            if label == "Justification":
                issues.append("Conclusion : ajoutez une justification argumentée.")
            else:
                issues.append(f"Conclusion : renseignez le champ « {label} ».")

    return issues
