#!/usr/bin/env bash
# Sauvegarde horodatée de la base veloville avec pg_dump.
#
# Usage (depuis n'importe quel dossier) : bash scripts/sauvegarde.sh
# Résultat : sauvegardes/veloville_AAAAMMJJ_HHMMSS.dump (format custom)
# Restauration : voir docs/procedure-deploiement.md

# Arrêter le script à la première erreur.
set -euo pipefail

# Se placer à la racine du projet (le dossier parent de scripts/).
cd "$(dirname "$0")/.."

# Connexion lue dans l'environnement, sinon dans le fichier .env.
# On ne l'affiche jamais : elle contient le mot de passe de la base.
if [ -z "${DATABASE_URL:-}" ] && [ -f .env ]; then
    DATABASE_URL=$(grep -E '^DATABASE_URL=' .env | cut -d '=' -f 2- | tr -d '\r')
fi

if [ -z "${DATABASE_URL:-}" ]; then
    echo "Erreur : DATABASE_URL n'est défini ni dans l'environnement ni dans .env." >&2
    exit 1
fi

if ! command -v pg_dump > /dev/null; then
    echo "Erreur : pg_dump est introuvable. Ajoutez le dossier bin de PostgreSQL au PATH." >&2
    exit 1
fi

# pg_dump ne comprend pas « +psycopg », réservé à SQLAlchemy :
# postgresql+psycopg://... devient postgresql://...
URL_PG="${DATABASE_URL/+psycopg/}"

# Nom du fichier : veloville_AAAAMMJJ_HHMMSS.dump
mkdir -p sauvegardes
FICHIER="sauvegardes/veloville_$(date +%Y%m%d_%H%M%S).dump"

# -Fc : format « custom », compressé et lisible par pg_restore.
if ! pg_dump --format=custom --file="$FICHIER" --dbname="$URL_PG"; then
    # Pas de fichier incomplet laissé derrière en cas d'échec.
    rm -f "$FICHIER"
    echo "Erreur : la sauvegarde a échoué." >&2
    exit 1
fi

echo "Sauvegarde créée : $FICHIER"
