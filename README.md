# Northstar — L'archive disparue

## L'affaire

Le projet étudiant **Northstar** doit être présenté aujourd'hui. L'archive de
livraison est prête et déposée dans l'espace release. Quelques minutes avant
la présentation, `release/release-candidate.tar.gz` disparaît. Au même moment,
une branche `hotfix/release` apparaît dans le dépôt.

Vous êtes l'équipe chargée de reprendre l'enquête. Les traces sont dispersées
et plusieurs membres ont effectué des actions parfaitement légitimes. Votre
mission est de reconstituer les faits, de comprendre comment l'archive a
disparu et d'identifier la personne qui doit répondre de l'incident.

Travaillez en équipe, échangez vos hypothèses et ne modifiez jamais les
éléments de l'enquête.

## Les personnes concernées

- **Kevin**, coordinateur de la livraison ;
- **Anthony**, propriétaire technique de l'espace release ;
- **Mickael**, reviewer chargé de vérifier l'intégrité de l'archive ;
- **Lisa**, responsable de la documentation et du script de paquetage ;
- **Lydie**, chargée de la vérification finale.

Le propriétaire d'un accès n'est pas forcément la personne qui l'utilise.
Cette distinction sera importante pour votre enquête.

## Les dossiers

Les informations sont réparties dans six dossiers. Ils ne sont pas classés
dans l'ordre des événements :

1. **Ouverture du projet** — la livraison et les responsabilités ;
2. **Les droits** — les accès et les credentials ;
3. **La dernière vérification** — le contrôle effectué avant l'incident ;
4. **Les témoins** — les actions légitimes de l'équipe ;
5. **La disparition** — l'archive manquante et la branche suspecte ;
6. **Le rapport final** — les questions auxquelles votre enquête doit répondre.

Les dossiers donnent le contexte. Les preuves techniques permettent de vérifier
ou de réfuter ce qu'ils racontent.

## Parcours conseillé

1. Commencez par `dossiers/` et ouvrez les dossiers dans l'ordre de votre choix.
2. Relevez les noms, heures, sessions, branches et chemins.
3. Retrouvez les traces correspondantes dans `evidence/`.
4. Croisez au moins trois familles de preuves.
5. Écartez les actions légitimes avant de conclure.
6. Rédigez `investigation-report.md`.

## Votre rapport

Votre rapport doit présenter :

- la chronologie des événements ;
- les personnes, sessions et terminaux concernés ;
- les fausses pistes écartées ;
- au moins trois preuves indépendantes ;
- une conclusion argumentée et son niveau de certitude.

Une accusation fondée sur un seul indice ne suffit pas.

## Commencer l'enquête

```bash
cd Shell-Mystery-Murder
find dossiers evidence -type f -print | sort
```

La console propose les mêmes archives sous forme de fichiers et vous permet
d'utiliser les commandes Shell vues en cours. Quand votre preuve est complète,
quittez-la puis validez votre conclusion :

```bash
python3 main.py --answer 'PROPRIETAIRE|ACTEUR'
```

Remplacez les deux valeurs par votre conclusion, dans cet ordre. Ne cherchez
pas un document de correction : la réponse doit être démontrée par votre
rapport.
