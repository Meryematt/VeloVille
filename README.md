# VéloVille - Plateforme de valorisation des données

À compléter : présentation du projet, prérequis, installation, lancement de
l'API et du front, exécution des tests, liens vers la documentation
(docs/), auteur et version.

## Choix techniques

### Import ligne par ligne plutôt qu'avec pandas

`scripts/importer.py` parcourt les lignes des CSV une par une et applique
les règles de `api/services/fiabilisation.py` à chacune. Un traitement par
colonnes avec pandas aurait donné un script d'import plus court, mais ce
choix a été écarté pour la V1 :

- **Le volume V1 ne le justifie pas.** Le cahier des charges porte sur
  environ 2 000 trajets : l'import actuel les traite en moins d'une seconde.
  Optimiser dès maintenant pour 3 millions de trajets ajouterait de la
  complexité pour un problème qui ne se pose pas encore.
- **Le journal est exact et simple à produire.** Une ligne donne une
  décision et un motif : le premier `Rejet` arrête le contrôle de la ligne.
  Avec pandas, il faudrait enchaîner des masques en veillant à ne pas
  rejeter deux fois la même ligne.
- **Le code reste lisible par l'équipe de maintenance** (deux développeurs,
  compétences Python et SQL selon le cahier des charges), sans maîtrise
  avancée de pandas.

Ce choix n'empêche pas d'évoluer : les règles de fiabilisation sont des
fonctions pures, testées indépendamment de l'import. Passer à un
traitement par lots ne demanderait de modifier que la boucle de
`importer.py` ; les règles et leurs tests resteraient valables. Ce
changement n'est à envisager qu'après avoir mesuré un vrai problème de
performance (voir « Axes d'amélioration »).

## Axes d'amélioration

- **Volumétrie cible (3 millions de trajets).** Si la durée de l'import
  devient trop longue, traiter les lignes par lots (avec pandas, ou une
  insertion en base par paquets) en conservant les mêmes règles de
  fiabilisation.

## Tests

### Comptes utilisés par les tests

Les tests d'intégration ne se connectent pas avec les comptes fournis
(`exploitant01`, `direction01`) : leur mot de passe n'apparaît donc nulle
part dans le code. Chaque lancement de `pytest` crée, dans la base de test,
deux comptes temporaires (`exploitant_test` et `direction_test`) avec un
mot de passe tiré au hasard (`secrets.token_urlsafe`). Ces comptes sont
effacés à la fin de chaque test par le rollback de la transaction.

### Coût bcrypt réduit dans les tests (`rounds=4`)

bcrypt est volontairement lent : son facteur de coût (`rounds`) fixe le
nombre de répétitions du calcul, soit 2 puissance `rounds`. Chaque +1
double le temps de calcul, ce qui ralentit d'autant une attaque qui
essaierait des millions de mots de passe.

| rounds | Répétitions | Hachage ou vérification (mesuré) |
|---|---|---|
| 4 | 16 | environ 1 ms |
| 12 | 4 096 | environ 180 ms |

- Les **vrais comptes** (`sql/comptes.sql`) utilisent le coût **12**, la
  valeur recommandée : leurs hachages commencent par `$2b$12$`.
- Les **comptes de test** utilisent le coût **4**
  (`bcrypt.gensalt(rounds=4)` dans `tests/conftest.py`). La sécurité n'a pas
  d'importance ici (mot de passe aléatoire, base de test vidée à chaque
  test), alors que la vitesse compte : une vingtaine de tests se
  connectent. Avec le coût par défaut (12), la suite de tests passerait
  d'environ 0,3 seconde à environ 4 secondes.

Le coût est écrit dans le hachage lui-même : `verify_password` s'y adapte
tout seul, le code de l'API n'a donc pas besoin de changer selon le coût.

Remarque : `bcrypt.gensalt()` est obligatoire. Il fabrique le sel aléatoire
(deux mots de passe identiques donnent deux hachages différents) et porte
le facteur de coût ; sans lui, `bcrypt.hashpw` lève une `TypeError`.
