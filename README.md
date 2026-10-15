# VéloVille - Plateforme de valorisation des données

Application de valorisation des données de VéloVille Hauts-de-France,
opérateur de vélos en libre-service (120 stations, 1 800 vélos). Elle :

- importe et fiabilise les exports CSV de la billettique (stations,
  trajets, incidents de maintenance) dans une base PostgreSQL ;
- expose ces données et trois indicateurs par une **API REST sécurisée**
  (FastAPI, jeton JWT, deux rôles : exploitant et direction) ;
- les restitue dans un **front Streamlit** en tableaux et métriques, sans
  graphique.

Version : **0.9.0** (version livrée avant recette).
Auteure : Meryem ATTARI.

## Structure du projet

```
api/            API FastAPI : main.py, database.py, models.py, schemas.py,
                securite.py, routers/ (une ressource par fichier),
                services/ (logique métier : fiabilisation, indicateurs...)
front/          Front Streamlit : app.py (connexion), pages/, api_client.py
scripts/        importer.py (import et fiabilisation), sauvegarde.sh,
                purge.py (suppression des trajets anciens)
sql/            schema.sql (création des tables), comptes.sql (2 comptes)
tests/          tests unitaires (unit/) et d'intégration (integration/)
data/           les 3 exports CSV
docs/           schéma de données, matrice des droits, procédure de
                déploiement, recette, journal de l'import
```

## Prérequis

- Python 3.12 ou plus (développé et testé avec Python 3.14) ;
- PostgreSQL 14 ou plus (testé avec PostgreSQL 18) ;
- Git (et Git Bash pour le script de sauvegarde).

## Installation

Résumé des étapes, sous Windows et PowerShell. La procédure complète, avec
la sauvegarde et la restauration, est dans
[docs/procedure-deploiement.md](docs/procedure-deploiement.md).

```powershell
git clone <adresse-du-depot> veloville
cd veloville
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env        # puis renseigner JWT_SECRET dans .env

psql -U postgres -c "CREATE ROLE veloville LOGIN PASSWORD 'veloville';"
psql -U postgres -c "CREATE DATABASE veloville OWNER veloville;"
psql -U postgres -c "CREATE DATABASE veloville_test OWNER veloville;"
psql -U veloville -d veloville -f sql/schema.sql
psql -U veloville -d veloville -f sql/comptes.sql
psql -U veloville -d veloville_test -f sql/schema.sql
```

## Variables d'environnement

Elles sont lues dans le fichier `.env` (ignoré par Git). Le fichier
`.env.example` donne leur liste, sans valeur sensible.

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | connexion à la base `veloville` |
| `TEST_DATABASE_URL` | connexion à la base de test `veloville_test` |
| `JWT_SECRET` | clé de signature des jetons, à générer avec `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_ALGORITHM` | algorithme de signature (`HS256`) |
| `JWT_EXPIRATION_MINUTES` | durée de validité d'un jeton (60 par défaut) |
| `API_URL` | adresse de l'API, utilisée par le front |
| `API_TIMEOUT_SECONDES` | délai maximum d'attente d'une réponse de l'API |

## Import des données

```powershell
python scripts/importer.py
```

Le script lit les trois CSV de `data/`, applique les règles de
fiabilisation, charge les lignes valides (stations, puis trajets et
incidents) et écrit le journal des rejets et avertissements dans
`docs/journal-import.csv`. Il est idempotent : il vide puis recharge les
tables dans une seule transaction, donc deux exécutions donnent la même
base (120 stations, 2 002 trajets, 177 incidents).

## Lancement

API (premier terminal) :

```powershell
uvicorn api.main:app
```

Vérification : http://localhost:8000/sante affiche `{"statut":"ok"}`. La
documentation interactive est sur http://localhost:8000/docs.

Front (second terminal) :

```powershell
streamlit run front/app.py
```

Le front s'ouvre sur http://localhost:8501. Comptes fournis :
`exploitant01` et `direction01` (voir `sql/comptes.sql`).

## Maintenance

- **Sauvegarde** : `bash scripts/sauvegarde.sh` (dans Git Bash) crée
  `sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump`. La restauration est
  décrite dans [docs/procedure-deploiement.md](docs/procedure-deploiement.md).
- **Purge des trajets anciens** : le cahier des charges limite la
  conservation des trajets détaillés à 13 mois (RGPD). Le script supprime
  les trajets de plus de N jours ; par défaut il ne fait qu'une simulation.

```powershell
python scripts/purge.py --jours 395             # simulation : affiche le nombre de trajets concernés
python scripts/purge.py --jours 395 --executer  # suppression réelle
```

## Audit des données

L'audit des trois exports CSV (défauts trouvés, nombre de lignes
concernées, traitement retenu) est dans
[docs/schema-donnees.md](docs/schema-donnees.md), section « Audit des
données sources ». Le journal des rejets et avertissements produit par
l'import est dans `docs/journal-import.csv`.

## Tests

```powershell
pytest --cov=api/services --cov-report=term-missing
```

Résultat : **98 tests réussis**, couverture des modules métier
(`api/services`) : **98 %** (minimum demandé : 60 %).

- `tests/unit/` : règles de fiabilisation (cas nominal et cas de rejet pour
  chaque règle) et calcul des indicateurs ;
- `tests/integration/` : appels de l'API avec `TestClient` (santé,
  connexion, 401, 403, pagination, filtres, changement de statut...).

Les tests qui utilisent la base travaillent sur `veloville_test`, dans une
transaction annulée à la fin de chaque test : la base de test reste vide.

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

## Choix écoresponsables

- **Pagination côté serveur, taille de page bornée.** Les listes
  (stations, trajets, incidents) sont renvoyées page par page, 20 éléments
  par défaut et 100 au maximum : on ne transfère jamais une table entière.
- **Pas de rafraîchissement automatique.** Le front ne recharge les données
  qu'à la demande : les filtres des indicateurs ne sont appliqués qu'au clic
  sur « Actualiser », et la connexion passe par un formulaire.
- **Mise en cache des données de référence.** La liste des communes de
  l'écran Stations est gardée en cache une heure (`st.cache_data(ttl=3600)`) :
  l'API n'est pas rappelée à chaque clic.
- **Calculs en SQL.** Les indicateurs (comptages, sommes, moyenne) sont
  calculés par PostgreSQL ; seuls les résultats agrégés sont envoyés à
  Python.
- **Index** sur les colonnes utilisées par les filtres et les indicateurs,
  pour lire moins de données à chaque requête.
- **Dépendances limitées au nécessaire** : pas de bibliothèque de graphiques
  ni de framework front supplémentaire.

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

### Autres choix

- **Règles de gestion aussi dans le schéma.** En plus des contraintes
  imposées, `sql/schema.sql` vérifie la capacité, la cohérence abonné /
  pseudonyme (RG5), la cible d'un incident (RG6) et les dates de résolution
  (RG8). La base refuse ainsi une donnée invalide même si elle n'arrive pas
  par l'import.
- **RG5 bloquante.** Le cahier des charges ne cite pas RG5 parmi les règles
  qui entraînent un rejet, mais elle est portée par une contrainte du
  schéma : une ligne qui la viole est donc rejetée. Aucune ligne des
  données fournies n'est concernée.
- **Paramètre `limite` des stations actives borné entre 1 et 100**, comme
  la taille de page. Le contrat ne fixe que sa valeur par défaut (10).
- **Écran Stations sans latitude ni longitude.** La maquette les rend
  facultatives : elles ne sont pas affichées pour garder un tableau lisible
  sur tablette (768 px) et parce que des coordonnées ne parlent pas sans
  carte.
- **Écran Indicateurs** : un message d'erreur s'affiche si la date de début
  est postérieure à la date de fin.
- **Script de purge plutôt que script de contrôle d'intégrité.** Le sujet
  proposait l'un ou l'autre en bonus. La purge répond à un besoin du cahier
  des charges (conservation des trajets limitée à 13 mois, RGPD). Un
  contrôle d'intégrité serait peu utile ici : les contraintes `CHECK` et les
  clés étrangères du schéma empêchent déjà toute donnée qui viole les
  règles de gestion d'entrer en base, son rapport afficherait donc toujours
  zéro anomalie.

## Écarts au contrat

- **`DATABASE_URL` sans valeur par défaut.** Le contrat prévoit une valeur
  par défaut contenant l'utilisateur et le mot de passe de la base. Elle a
  été retirée du code (`api/config.py`) pour qu'aucun identifiant n'y
  figure : l'application refuse de démarrer si la variable manque dans
  `.env`.

## Limites connues

- `GET /trajets` renvoie `usager_ref` (pseudonyme d'abonné) aussi au rôle
  direction. Aucun écran du front n'affiche les trajets, mais l'API ne le
  masque pas.
- Pour une ligne rejetée, seul le motif du rejet est journalisé : une
  correction faite avant le rejet sur la même ligne n'apparaît pas (cas du
  trajet T480152).
- La période par défaut de l'écran Indicateurs est écrite en dur (semaine
  du 24 au 30 août 2026) : avec un nouvel export, l'écran s'ouvrirait sur
  une période vide.
- Les tests affichent un avertissement de dépréciation venant de FastAPI
  (`httpx` utilisé par `TestClient`), sans effet sur les résultats.
- Le front n'a pas de tests automatisés de bout en bout.

## Axes d'amélioration

- **Volumétrie cible (3 millions de trajets).** Si la durée de l'import
  devient trop longue, traiter les lignes par lots (avec pandas, ou une
  insertion en base par paquets) en conservant les mêmes règles de
  fiabilisation.
- **Période par défaut des indicateurs calculée à partir des données** :
  premier et dernier jour renvoyés par l'indicateur d'activité sans bornes.
- **Masquer `usager_ref` pour le rôle direction** dans l'API.
- **Planifier la purge** (par exemple chaque nuit) : la V1 fournit le
  script, la planification est prévue en V2 par le cahier des charges.
- **Tests de bout en bout du front** (par exemple avec Playwright).

## Documentation

- [docs/schema-donnees.md](docs/schema-donnees.md) : MLD, tables, règles de
  gestion, audit des données ;
- [docs/matrice-roles-droits.md](docs/matrice-roles-droits.md) : droits par
  route et données sensibles ;
- [docs/procedure-deploiement.md](docs/procedure-deploiement.md) :
  installation, sauvegarde et restauration ;
- [docs/recette/](docs/recette/) : plan de recette, résultats et fiches
  d'anomalie ;
- [CHANGELOG.md](CHANGELOG.md) : journal des versions.
