# Journal des versions

Une section par version, les changements regroupés en « Ajouté »,
« Modifié », « Corrigé ». Chaque version correspond à un tag Git
(`v0.1.0`, `v0.9.0`, `v1.0.0`).

## [1.0.0] - 2026-10-15

Version livrée après recette : les cinq anomalies relevées sont corrigées
et rejouées OK (voir `docs/recette/`).

### Ajouté
- Résultats de la recette (cas REC-01 à REC-10), fiches d'anomalie
  ANO-001 à ANO-005, captures et procès-verbal (`docs/recette/`).
- Tests de non-régression des cinq anomalies (110 tests au total,
  couverture de 98 % sur `api/services`).

### Modifié
- `.env.example` et `front/api_client.py` : l'adresse de l'API est
  `http://127.0.0.1:8000` au lieu de `http://localhost:8000`.
- `GET /trajets` : `usager_ref` est vide (`null`) pour le rôle direction.
- Front : au-delà de la dernière page, le texte indique la dernière page
  existante.

### Corrigé
- ANO-001 : des lignes du journal d'import n'avaient ni colonne ni valeur.
- ANO-002 : chaque écran du front mettait environ 4 secondes à s'afficher.
- ANO-003 : une adresse d'API mal écrite affichait une trace Python dans le
  front.
- ANO-004 : l'écran affichait « Page 9 sur 6 » au-delà de la dernière page.
- ANO-005 : l'API renvoyait le pseudonyme des abonnés au rôle direction.

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
