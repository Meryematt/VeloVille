"""Purge des trajets de plus de N jours.

Le cahier des charges fixe la durée de conservation des trajets détaillés
à 13 mois (environ 395 jours).

Par défaut, le script est en mode simulation : il affiche le nombre de
trajets concernés sans rien supprimer. La suppression n'a lieu qu'avec
l'option --executer.

Usage :
    python scripts/purge.py --jours 395             (simulation)
    python scripts/purge.py --jours 395 --executer  (suppression)
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Permet d'importer le paquet api/ quand le script est lancé depuis la racine.
RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from api.database import SessionLocal
from api.services.purge import purge_old_trips


def main():
    parser = argparse.ArgumentParser(description="Purge des trajets de plus de N jours.")
    parser.add_argument("--jours", type=int, required=True,
                        help="âge maximum des trajets à conserver, en jours")
    parser.add_argument("--executer", action="store_true",
                        help="supprime vraiment les trajets (sinon simulation)")
    arguments = parser.parse_args()

    if arguments.jours < 1:
        parser.error("--jours doit être un entier positif")

    date_limite = datetime.now() - timedelta(days=arguments.jours)

    with SessionLocal() as db:
        nombre = purge_old_trips(db, date_limite, arguments.executer)

    if arguments.executer:
        print(f"{nombre} trajet(s) parti(s) avant le {date_limite:%Y-%m-%d %H:%M} supprimé(s).")
    else:
        print(f"Simulation : {nombre} trajet(s) parti(s) avant le "
              f"{date_limite:%Y-%m-%d %H:%M} serai(en)t supprimé(s).")
        print("Relancer avec --executer pour les supprimer.")


if __name__ == "__main__":
    main()
