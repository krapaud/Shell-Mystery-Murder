# Northstar : l'archive disparue

![Affiche Northstar : The Last commit](assets/northstar-mystery-faceoff.png)

> « L'archive de livraison a disparu avant la présentation. Les fichiers
> existent encore, mais ils ne racontent pas tous
> la même partie de l'histoire. »

## Votre mission

Le projet étudiant **Northstar** doit être présenté aujourd'hui. Une archive de
livraison n'est plus disponible dans l'espace de publication et une branche
apparaît dans la même fenêtre temporelle.

Vous devez établir les faits et remettre un rapport d'enquête permettant de
répondre à ces questions :

1. Quelle action explique la disparition de l'archive ?
2. Quelle session et quel terminal sont liés à cette action ?
3. Quelle credential a été utilisée ?
4. Qui en est le propriétaire ?
5. Quelle personne est la plus probablement associée à l'action devant le
   terminal ?
6. Quelles pistes peuvent être écartées, et pourquoi ?

Les traces concernent Kevin, Anthony, Mickael, Lisa et Lydie. Certaines actions
sont légitimes. Une personne peut être propriétaire d'une credential sans
être celle qui l'utilise. Distinguez également ce que les traces établissent
techniquement, comme une session ou un terminal, de l'identité humaine que
vous en déduisez.

Durée recommandée : 45 à 60 minutes. Le travail en équipe est recommandé,
mais l'enquête est réalisable seul.

## Règles de l'enquête

- Travaillez uniquement depuis la racine du projet.
- N'utilisez les commandes Shell que pour lire les fichiers du jeu. La console
  écrit elle-même vos notes dans `investigation-report.md` et conserve un
  journal de session ; ces écritures contrôlées font partie du fonctionnement
  normal de l'enquête.
- Vérifiez chaque hypothèse avec plusieurs traces indépendantes.
- Notez les heures, les identifiants, les terminaux et les cibles exactes.
- Ne concluez pas à partir d'un seul nom ou d'une seule ligne de log.
- Distinguez toujours un préparatif, une action réussie et un effet constaté.
- Si plusieurs extraits portent le même titre, rassemblez-les dans leur ordre
  avant d'interpréter les traces qu'ils désignent.
- Conservez vos observations pour rédiger le rapport final.

## Lancer l'enquête

Depuis la racine du dépôt :

```bash
python3 main.py
```

La console d'enquête s'ouvre. Commencez par consulter l'aide et la liste des
archives :

```text
.help
.files
```

## Commandes disponibles

La console accepte les commandes de lecture Shell vues en cours :

```text
find, cat, grep, cut, sort, awk, head, tail, wc, pwd, ls
```

Les pipelines de lecture sont autorisés, par exemple :

```bash
find evidence -type f -print | sort
```

Les écritures, suppressions, redirections et chemins en dehors du projet sont
refusés dans les commandes Shell saisies. Les fichiers de preuve sont le
terrain de l'enquête : observez-les sans les altérer. La console reste seule
responsable de l'ajout de vos notes au rapport et de son journal de session.

## Méthode de recherche

### 1. Lire le contexte

Commencez par découvrir les fichiers disponibles, puis lisez les six dossiers
de `dossiers/`. Ils présentent le contexte, les rôles et les questions à
résoudre. Ils ne constituent pas la preuve finale.

Découvrez les archives avec `find`, filtrez les identifiants et les horaires
avec `grep`, isolez des colonnes avec `cut`, puis triez les événements avec
`sort`. Les résultats de ces recherches servent à assembler les indices et à
vérifier vos hypothèses. La console réagit aux preuves que vous consultez.

### 2. Construire votre tableau d'identités

Dans `evidence/identity/`, recherchez les correspondances entre les membres,
les credentials, les sessions et les terminaux.

Notez les identifiants exacts et distinguez toujours le propriétaire d'une
credential, la session technique, le terminal concerné et la personne que les
indices permettent d'associer à l'action. Cette dernière attribution est une
inférence : exprimez son niveau de certitude dans le rapport.

### 3. Construire la chronologie

Dans `evidence/incident/` et `evidence/logs/`, comparez les événements dans
l'ordre des heures. Cherchez le dernier état certain de l'archive, les
préparatifs, l'action qui produit sa disparition et la première vérification
qui constate son absence. Calculez la fenêtre temporelle au lieu de recopier
uniquement les heures.

### 4. Comparer les déclarations et les traces

Les notes d'équipe et les entretiens sont des témoignages à vérifier. Comparez
chaque déclaration avec le terminal, l'horaire, la cible et le journal qui peut
la confirmer ou la contredire.

### 5. Vérifier la piste Git

Les fichiers de `evidence/git/` servent à confirmer la chronologie des branches
et des opérations distantes. Ils ne suffisent pas seuls à identifier l'acteur.

### 6. Rédiger avant de valider

Quittez la console avec :

```text
.exit
```

À chaque étape validée, Mickael vous demandera une note et l'ajoutera à la
rubrique correspondante de `investigation-report.md`. Une réponse déjà saisie
n'est jamais remplacée sans vous demander confirmation. Pour revenir sur une
note, utilisez `.correct 1` à `.correct 6` dans la console. Mickael vous
avertira avant la modification. Après les six étapes, quittez la console et
complétez les rubriques de synthèse du rapport. La validation finale vérifie
qu'elles sont renseignées ; elle contrôle la structure, pas la qualité de votre
raisonnement. Vous pouvez garder des notes complémentaires à part. Le rapport
doit contenir :

- au moins trois événements datés, avec fait, source et niveau de certitude ;
- au moins deux observations sur les accès et les personnes, avec leurs
  sources ;
- une fausse piste écartée, la raison de son exclusion et sa source ;
- trois familles de preuves distinctes, leurs sources et ce qu'elles
  établissent ;
- dans « Analyse de l'incident », l'action, la session, le terminal, la
  credential et son propriétaire, la personne la plus probablement associée à
  l'action, ainsi que le lien entre ces rôles et les limites de cette
  attribution ;
- dans « Conclusion », un responsable, un niveau de certitude et une
  justification argumentée.

Le validateur refuse les rubriques vides, les lignes modèles inchangées et les
réponses trop courtes. Les rubriques du modèle restent fixes, mais le texte de
vos réponses est libre : aucune phrase attendue n'est comparée. Le validateur
ne peut pas évaluer si votre interprétation des preuves est juste.

Les trois notes numérotées retrouvées dans des archives différentes forment
une même pensée. Rassemblez-les dans l'ordre, puis décidez quelles traces
permettent de vérifier ce qu'elles suggèrent. La narration de Mickael évolue
quand vous avez consulté l'ensemble des preuves requises, pas après une seule
commande ou un seul fichier.

## Validation finale

Quand votre rapport est terminé, envoyez votre conclusion dans le format
suivant :

```bash
python3 main.py --answer 'PROPRIETAIRE|PERSONNE_PROBABLE'
```

Remplacez les deux valeurs par votre conclusion, dans cet ordre. Le programme
confirme uniquement une conclusion complète. Il ne fournit pas d'indice
supplémentaire.

Bonne enquête.
