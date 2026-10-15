# Journal des versions

Une section par version, les changements regroupés en « Ajouté »,
« Modifié », « Corrigé ». Chaque version correspond à un tag Git
(`v0.1.0`, `v0.9.0`...).

## [0.9.0] - 2026-10-15

Version livrée avant recette.

### Ajouté
- Base de données PostgreSQL : schéma des tables `station`, `trajet`,
  `incident` et `utilisateur`, avec les contraintes des règles de gestion
  et des index.
- Règles de fiabilisation des données (`api/services/fiabilisation.py`)
  et script d'import `scripts/importer.py`, idempotent, avec un journal des
  rejets et avertissements (`docs/journal-import.csv`).
- Les trois indicateurs : activité par jour, stations les plus actives,
  incidents par statut avec délai moyen de résolution.
- API FastAPI : connexion par jeton JWT, routes stations, trajets,
  incidents et indicateurs, pagination et filtres ; changement de statut
  d'un incident réservé au rôle exploitant.
- Front Streamlit : écrans Connexion, Stations, Incidents et Indicateurs.
- Tests unitaires et d'intégration (98 tests, couverture de 98 % sur
  `api/services`).
- Script de sauvegarde `scripts/sauvegarde.sh`.
- Script de purge des trajets anciens `scripts/purge.py`, en mode
  simulation par défaut.
- Documentation : README, schéma de données et audit des données, matrice
  des rôles et droits, procédure de déploiement.

### Modifié
- `requirements.txt` : versions des dépendances fixées.

## [0.1.0] - 2026-10-13

### Ajouté
- Initialisation du projet à partir du squelette fourni.
