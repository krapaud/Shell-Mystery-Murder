# Northstar : l'archive disparue

> « L'archive de livraison a disparu quelques minutes avant la présentation.
> Vous connaissez le fichier manquant. Découvrez qui a utilisé l'accès et
> comment l'action a été réalisée. »
>
> Mickael, reviewer du projet Northstar

## Votre mission

Le projet étudiant **Northstar** doit être présenté aujourd'hui. L'archive
`release/release-candidate.tar.gz` était prête dans l'espace de livraison,
mais elle disparaît à 15 h 42. Une branche `hotfix/release` apparaît presque
au même moment.

Vous devez prouver :

1. quel propriétaire de credential a été utilisé ;
2. qui était l'acteur présent sur le terminal ;
3. comment les traces permettent de relier ces deux identités.

Les traces concernent Kevin, Anthony, Mickael, Lisa et Lydie. Plusieurs actions
sont légitimes. Ne concluez jamais à partir d'un seul indice.

## Le premier pas

Placez-vous à la racine du projet, puis lancez :

~~~bash
python3 main.py
~~~

La console d'enquête s'ouvre automatiquement. Tapez `.help` pour consulter les
commandes disponibles, puis `.files` pour afficher les archives de l'affaire.
Travaillez en équipe, notez les preuves et ne modifiez pas les fichiers.

## Les dossiers de Mickael

> « Chaque dossier ne raconte qu'une partie de l'histoire. Vérifiez les heures,
> les terminaux et les identifiants avant de croire une déclaration. »

Vous pouvez consulter les six dossiers. Ils donnent le contexte de l'enquête,
mais les preuves techniques de `evidence/` permettent de vérifier ce qu'ils
racontent.

### Dossier 1 : La livraison connue

Retrouvez le projet Northstar, le fichier de livraison et les responsabilités
de chacun. Notez le chemin exact de l'archive et le rôle de Kevin, Anthony,
Mickael, Lisa et Lydie.

**Mickael :** « Commencez par identifier ce qui devait être protégé et les
personnes qui avaient une raison légitime d'y accéder. »

### Dossier 2 : Les droits d'accès

Comparez les credentials, leurs propriétaires et les sessions ouvertes sur les
terminaux. Distinguez le propriétaire d'un accès de la personne qui l'utilise.

Notez les identifiants `member_id`, `credential_id`, `session_id` et le
terminal correspondant. Un droit rend une action possible, mais ne prouve pas
qui l'a effectuée.

**Mickael :** « Reliez les fichiers d'identité avant d'interpréter les logs.
Un nom de propriétaire n'est pas encore le nom de l'acteur. »

### Dossier 3 : La dernière vérification

Retrouvez le contrôle d'intégrité réalisé avant l'incident. Comparez son heure
avec l'heure de disparition signalée dans la note d'incident.

Vérifiez que l'archive existait encore avant la période suspecte et notez le
terminal utilisé pour cette vérification.

**Mickael :** « Mon contrôle confirme l'état de l'archive à un instant précis.
Utilisez-le pour construire le début de votre chronologie. »

### Dossier 4 : Les actions légitimes

Rassemblez les traces de Lisa, Anthony et Lydie. Certaines commandes échouent,
certaines portent sur le script de paquetage et certaines vérifient la
checklist. Elles doivent être comparées aux sessions et aux heures, pas
simplement écartées parce qu'elles semblent suspectes.

Pour chaque personne, notez ce qui est observé, ce qui est possible et ce qui
est confirmé par une autre famille de preuves.

**Mickael :** « Une action proche de l'incident n'est pas nécessairement le
vol. Confrontez chaque piste à son terminal et à sa cible. »

### Dossier 5 : La disparition et la branche

Retrouvez l'action qui concerne directement l'archive disparue. Reconstituez
la suite des opérations : variable de chemin, création de branche, action sur
le fichier et push de la branche.

Comparez `access.log`, `terminal-history.log`, `command-audit.txt`,
`branch-log.txt` et `reflog.txt`. Les journaux ne présentent pas tous le même
niveau de détail.

**Mickael :** « Une trace technique décrit une action. Une autre doit vous
permettre d'identifier la personne devant le terminal. »

### Dossier 6 : La conclusion

Formulez votre conclusion à partir de plusieurs traces indépendantes. Vérifiez :

- le moment où l'archive était encore présente ;
- la session et le terminal liés à sa disparition ;
- la credential utilisée et son propriétaire ;
- la branche créée et poussée ;
- les actions légitimes qui écartent les autres personnes.

Vous devez réunir au moins trois preuves indépendantes avant de conclure.

Votre rapport doit contenir une chronologie, les fausses pistes écartées et une
conclusion argumentée.

**Mickael :** « Votre preuve finale contient le propriétaire de l'accès puis
l'acteur de l'action. Confirmez les deux identités avec les heures et les
terminaux. »

## Validation finale

Quand votre enquête est terminée, quittez la console avec `.exit`, puis lancez :

~~~bash
python3 main.py --answer 'PROPRIETAIRE|ACTEUR'
~~~

Remplacez les deux valeurs par votre conclusion, dans cet ordre. Une réponse
correcte permettra à Mickael de clôturer l'incident Northstar.

> « L'archive a disparu, mais la chronologie a conservé la trace de l'action. »
> Mickael
