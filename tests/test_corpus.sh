#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
EVIDENCE="$ROOT/evidence"

for dossier in 01 02 03 04 05 06; do
  test -d "$ROOT/dossiers/dossier-$dossier"
done

for file in \
  "$EVIDENCE/incident/incident-note.txt" \
  "$EVIDENCE/identity/members.txt" \
  "$EVIDENCE/identity/credentials.txt" \
  "$EVIDENCE/identity/sessions.log" \
  "$EVIDENCE/logs/access.log" \
  "$EVIDENCE/logs/terminal-history.log" \
  "$EVIDENCE/logs/command-audit.txt" \
  "$EVIDENCE/logs/failed-commands.txt" \
  "$EVIDENCE/git/branch-log.txt" \
  "$EVIDENCE/git/reflog.txt" \
  "$EVIDENCE/permissions/current.txt" \
  "$EVIDENCE/team/notes.txt" \
  "$EVIDENCE/team/interviews.txt"; do
  test -s "$file"
done

test -s "$ROOT/dossiers/README.md"

grep -Fq 'missing_file=release/release-candidate.tar.gz' "$EVIDENCE/incident/incident-note.txt"
grep -Fq 's-07|m-03|poste-01' "$EVIDENCE/identity/sessions.log"
grep -Fq 's-07|cred-review-03|checksum' "$EVIDENCE/logs/access.log"
grep -Fq 's-44|m-01|poste-04' "$EVIDENCE/identity/sessions.log"
grep -Fq 'cred-17|m-02' "$EVIDENCE/identity/credentials.txt"
grep -Fq 's-44|cred-17|filesystem-event|op-417|success' "$EVIDENCE/logs/access.log"
grep -Fq 'filesystem-operation|release/release-candidate.tar.gz|completed|op-417' "$EVIDENCE/logs/command-audit.txt"
test "$(grep -h -c 'Note de reprise \[[123]/3\]' "$EVIDENCE/team/notes.txt" "$EVIDENCE/git/reflog.txt" "$EVIDENCE/incident/incident-note.txt" | awk '{s+=$1} END {print s}')" -eq 3
grep -Fq 'poste-04 rm' "$EVIDENCE/logs/terminal-history.log"
grep -Fq 'cmd-105|2026-10-19 15:42:16|poste-04' "$EVIDENCE/logs/command-audit.txt"
grep -Fq 'session=s-44' "$EVIDENCE/git/branch-log.txt"
grep -Fq 'workstation=poste-04' "$EVIDENCE/git/reflog.txt"
grep -Fq 'réussit encore à 15:41:18' "$ROOT/dossiers/dossier-03/integrity-check.txt"
grep -Fq 'sans distinguer son visage' "$EVIDENCE/team/interviews.txt"
grep -Fq "Je n'ai pas supprimé le paquet" "$EVIDENCE/team/interviews.txt"
grep -Fq 'op-417 ne nomme ni la cible' "$EVIDENCE/git/reflog.txt"
grep -Fq 'reliez cette référence à la cible' "$EVIDENCE/incident/incident-note.txt"
! grep -Fq "j'ai vu Kevin au poste-04" "$EVIDENCE/team/interviews.txt"

echo "Shell Mystery Murder corpus: OK"
