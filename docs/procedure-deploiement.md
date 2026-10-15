# Procédure de déploiement

Procédure pour installer VéloVille sur un poste Windows vierge. Les
commandes sont à taper dans un terminal **PowerShell**, sauf la sauvegarde
(étape 9), qui se fait dans **Git Bash**.

## 1. Prérequis

À installer :

- **Python 3.12 ou plus** (développé et testé avec Python 3.14) ;
- **PostgreSQL 14 ou plus** (testé avec PostgreSQL 18) : noter le mot de
  passe de l'utilisateur `postgres` choisi à l'installation ;
- **Git**, qui installe aussi **Git Bash**.

Rendre les commandes PostgreSQL (`psql`, `pg_dump`, `pg_restore`)
utilisables dans le terminal (à refaire dans chaque nouveau terminal, ou à
ajouter une fois pour toutes dans la variable d'environnement `Path` de
Windows) :

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\18\bin"
psql --version
```

Le `18` est le numéro de version de PostgreSQL. Si vous avez installé une
autre version, ouvrez le dossier `C:\Program Files\PostgreSQL` dans
l'explorateur Windows : le nom du dossier qu'il contient (`16`, `17`...)
est votre numéro, à mettre à la place de `18` ici et à l'étape 9.

## 2. Récupérer le projet

```powershell
git clone https://github.com/Meryematt/VeloVille.git veloville
cd veloville
```

Toutes les commandes suivantes se lancent depuis ce dossier `veloville`.

## 3. Environnement Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si PowerShell refuse d'exécuter `Activate.ps1`, lancer d'abord
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, puis recommencer.

## 4. Variables d'environnement

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

La deuxième commande affiche une longue suite de lettres et de chiffres :
copiez-la. Ouvrez ensuite le fichier `.env` dans le Bloc-notes avec la
commande suivante :

```powershell
notepad .env
```

Collez le texte copié juste après `JWT_SECRET=` (sur la même ligne, sans
espace), puis enregistrez (Ctrl+S) et fermez le Bloc-notes.

Remarque : dans l'explorateur Windows, un fichier dont le nom commence par
un point, comme `.env`, peut être caché ; la commande `notepad .env`
l'ouvre directement.

Les autres valeurs de `.env.example` conviennent pour un poste local :

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | connexion à la base `veloville` |
| `TEST_DATABASE_URL` | connexion à la base de test `veloville_test` |
| `JWT_SECRET` | clé de signature des jetons (à garder secrète) |
| `JWT_ALGORITHM` | algorithme de signature (`HS256`) |
| `JWT_EXPIRATION_MINUTES` | durée de validité d'un jeton |
| `API_URL` | adresse de l'API, utilisée par le front |
| `API_TIMEOUT_SECONDES` | délai maximum d'attente d'une réponse de l'API |

Le fichier `.env` ne doit jamais être commité (il est dans `.gitignore`).

## 5. Base de données

Créer le rôle et les deux bases (mot de passe de `postgres` demandé) :

```powershell
psql -U postgres -c "CREATE ROLE veloville LOGIN PASSWORD 'veloville';"
psql -U postgres -c "CREATE DATABASE veloville OWNER veloville;"
psql -U postgres -c "CREATE DATABASE veloville_test OWNER veloville;"
```

Créer les tables et charger les comptes (mot de passe `veloville`) :

```powershell
psql -U veloville -d veloville -f sql/schema.sql
psql -U veloville -d veloville -f sql/comptes.sql
psql -U veloville -d veloville_test -f sql/schema.sql
```

La base de test reste vide : les tests y créent leurs propres données et les
effacent.

## 6. Import des données

```powershell
python scripts/importer.py
```

Résultat attendu :

```
stations.csv : 120 lignes = 120 importées + 0 rejetées + 0 doublons écartés
trajets.csv : 2030 lignes = 2002 importées + 16 rejetées + 12 doublons écartés
incidents.csv : 180 lignes = 177 importées + 3 rejetées + 0 doublons écartés
Journal : docs\journal-import.csv (190 lignes)
```

L'import peut être relancé autant de fois que nécessaire : il vide puis
recharge les tables `station`, `trajet` et `incident` (les comptes ne sont
pas touchés).

## 7. Tests

```powershell
pytest --cov=api/services --cov-report=term-missing
```

Tous les tests doivent passer.

## 8. Lancement et vérification

Dans un premier terminal, lancer l'API :

```powershell
uvicorn api.main:app
```

Vérifier dans un navigateur que http://localhost:8000/sante affiche
`{"statut":"ok"}`. La documentation interactive de l'API est sur
http://localhost:8000/docs.

Dans un second terminal (environnement virtuel activé), lancer le front :

```powershell
streamlit run front/app.py
```

Le navigateur s'ouvre sur http://localhost:8501. Se connecter avec
`exploitant01` ou `direction01` (mot de passe fourni dans `sql/comptes.sql`).

## 9. Sauvegarde

Dans un terminal **Git Bash**, depuis le dossier du projet :

```bash
export PATH="$PATH:/c/Program Files/PostgreSQL/18/bin"
bash scripts/sauvegarde.sh
```

Le script crée un fichier dans le dossier `sauvegardes/` et affiche son
nom, par exemple :

```
Sauvegarde créée : sauvegardes/veloville_20261015_161604.dump
```

Le nom contient la date et l'heure de la sauvegarde (année, mois, jour,
puis heure, minutes, secondes). Dans les commandes ci-dessous et à
l'étape 11, remplacez `veloville_AAAAMMJJ_HHMMSS.dump` par ce nom réel.
Pour revoir la liste des sauvegardes : `ls sauvegardes`. En cas d'échec, il affiche une erreur et se termine avec
un code de retour non nul. Le dossier `sauvegardes/` est ignoré par Git.

Vérifier qu'une sauvegarde est lisible :

```bash
pg_restore --list sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump
```

## 10. Purge des trajets anciens

Les trajets détaillés sont conservés 13 mois (environ 395 jours). Pour voir
combien de trajets seraient supprimés, sans rien supprimer :

```powershell
python scripts/purge.py --jours 395
```

Pour les supprimer vraiment, ajouter `--executer`. Faire une sauvegarde
avant.

## 11. Restauration

Pour remettre la base dans l'état d'une sauvegarde (mot de passe
`veloville`) :

```bash
pg_restore -U veloville -h localhost -d veloville --clean --if-exists sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump
```

- `--clean` supprime les tables existantes avant de les recréer ;
- `--if-exists` évite une erreur si une table n'existe pas encore.

Toutes les données sont remplacées par celles de la sauvegarde, comptes
compris. Relancer ensuite l'API si elle était démarrée.

## Problèmes fréquents

| Message ou symptôme | Cause | Solution |
|---|---|---|
| `psql` n'est pas reconnu | PostgreSQL n'est pas dans le PATH de ce terminal | Refaire la commande `$env:Path += ...` de l'étape 1 (ou `export PATH=...` dans Git Bash), avec votre numéro de version |
| `python` n'est pas reconnu, ou le Microsoft Store s'ouvre | Python n'a pas été ajouté au PATH à l'installation | Réinstaller Python en cochant « Add python.exe to PATH », puis ouvrir un nouveau terminal |
| PowerShell refuse d'exécuter `Activate.ps1` | Les scripts sont bloqués par Windows | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, puis recommencer (étape 3) |
| `échec de l'authentification par mot de passe` | Mauvais mot de passe pour PostgreSQL | Utilisateur `postgres` : le mot de passe choisi à l'installation. Utilisateur `veloville` : `veloville`. Vérifier aussi la ligne `DATABASE_URL` de `.env` |
| `KeyError: 'JWT_SECRET'` ou `'DATABASE_URL'` au lancement | Le fichier `.env` manque ou une valeur est vide | Refaire l'étape 4, depuis le dossier `veloville` |
| Le front affiche « L'API est injoignable » | L'API n'est pas démarrée, ou son terminal a été fermé | Relancer `uvicorn api.main:app` (étape 8) et laisser ce terminal ouvert |
| Le front met plusieurs secondes à chaque clic | `API_URL` utilise `localhost` | Dans `.env` : `API_URL=http://127.0.0.1:8000`, puis relancer le front |
| `error while attempting to bind on address` au lancement de l'API | Une API tourne déjà, dans un autre terminal | Fermer l'autre terminal (ou Ctrl+C dedans), puis relancer |
| « Identifiant ou mot de passe incorrect » avec un compte fourni | Les comptes n'ont pas été chargés | Refaire `psql -U veloville -d veloville -f sql/comptes.sql` (étape 5) |
| Les tests échouent avec une erreur de connexion | La base de test n'existe pas ou n'a pas ses tables | Refaire les commandes de l'étape 5 qui concernent `veloville_test` |
