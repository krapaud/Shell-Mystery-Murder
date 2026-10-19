# Northstar : l'archive disparue

![Affiche Northstar : The Last commit](assets/northstar-mystery-faceoff.png)

> « L'archive de livraison a disparu avant la présentation. Les fichiers
> existent encore, mais ils ne racontent pas tous la même partie de l'histoire. »

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
5. Qui était l'acteur devant le terminal ?
6. Quelles pistes peuvent être écartées, et pourquoi ?

Les traces concernent Kevin, Anthony, Mickael, Lisa et Lydie. Certaines actions
sont légitimes. Une personne peut être propriétaire d'un accès sans être celle
qui l'utilise.

Durée recommandée : 45 à 60 minutes. Le travail en équipe est recommandé,
mais l'enquête est réalisable seul.

## Règles de l'enquête

- Travaillez uniquement depuis la racine du projet.
- Ne modifiez, ne supprimez et ne créez aucun fichier du jeu.
- Vérifiez chaque hypothèse avec plusieurs traces indépendantes.
- Notez les heures, les identifiants, les terminaux et les cibles exactes.
- Ne concluez pas à partir d'un seul nom ou d'une seule ligne de log.
- Distinguez toujours un préparatif, une action réussie et un effet constaté.
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
refusés. Les fichiers sont le terrain de l'enquête : observez-les sans les
altérer.

## Méthode de recherche

### 1. Lire le contexte

Commencez par découvrir les fichiers disponibles, puis lisez les six dossiers
de `dossiers/`. Ils présentent le contexte, les rôles et les questions à
résoudre. Ils ne constituent pas la preuve finale.

### 2. Construire votre tableau d'identités

Dans `evidence/identity/`, recherchez les correspondances entre les membres,
les credentials, les sessions et les terminaux.

Notez les identifiants exacts et distinguez toujours le propriétaire d'une
credential de la personne qui ouvre une session.

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

Rédigez votre rapport dans `investigation-report.md` ou dans un document
séparé. Il doit contenir :

- une chronologie argumentée ;
- l'action qui explique la disparition ;
- la session et le terminal concernés ;
- la credential utilisée et son propriétaire ;
- l'acteur identifié ;
- au moins trois familles de preuves indépendantes ;
- les fausses pistes écartées et la raison de leur exclusion.
- la différence entre propriétaire du droit, utilisateur de la session et
  personne qui a réalisé l'action.

## Validation finale

Quand votre rapport est terminé, envoyez votre conclusion dans le format
suivant :

```bash
python3 main.py --answer 'PROPRIETAIRE|ACTEUR'
```

Remplacez les deux valeurs par votre conclusion, dans cet ordre. Le programme
confirme uniquement une conclusion complète. Il ne fournit pas d'indice
supplémentaire.

Bonne enquête.
