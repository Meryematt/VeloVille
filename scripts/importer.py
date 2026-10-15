"""Import et fiabilisation des trois exports CSV dans PostgreSQL.

Lit data/stations.csv, data/trajets.csv et data/incidents.csv, applique les
règles de api/services/fiabilisation.py, charge les lignes valides et écrit
le journal des rejets et avertissements dans docs/journal-import.csv.

Idempotent : les trois tables sont vidées puis rechargées dans une seule
transaction ; deux exécutions donnent donc la même base.
"""

import csv
import sys
from pathlib import Path

# Permet d'importer le paquet api/ quand le script est lancé depuis la racine.
RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from sqlalchemy import delete

from api.database import SessionLocal
from api.models import Incident, Station, Trajet
from api.services.fiabilisation import (
    Rejet,
    fiabiliser_incident,
    fiabiliser_station,
    fiabiliser_trajet,
    journal_line,
    separer_doublons,
)

DOSSIER_DONNEES = RACINE / "data"
CHEMIN_JOURNAL = RACINE / "docs" / "journal-import.csv"
COLONNES_JOURNAL = ["fichier", "identifiant", "colonne", "valeur", "motif", "decision"]


def lire_csv(nom_fichier):
    """Retourne les lignes d'un fichier CSV sous forme de dictionnaires."""

    with open(DOSSIER_DONNEES / nom_fichier, encoding="utf-8", newline="") as fichier:
        return list(csv.DictReader(fichier))


def importer_fichier(db, journal, nom_fichier, modele, colonne_id, stations):
    """Fiabilise un fichier, ajoute ses lignes valides à la session
    et remplit le journal. Retourne les compteurs du fichier."""

    lignes = lire_csv(nom_fichier)
    uniques, doublons = separer_doublons(lignes)

    for ligne in doublons:
        # Le doublon est identifié par la colonne d'identifiant et sa valeur.
        journal.append(journal_line(
            nom_fichier,
            ligne[colonne_id],
            colonne_id,
            ligne[colonne_id],
            "Ligne strictement identique à une ligne précédente",
            "doublon écarté",
        ))

    deja_importes = set()
    nb_rejets = 0

    for ligne in uniques:
        try:
            if nom_fichier == "stations.csv":
                propre, avertissements = fiabiliser_station(ligne, deja_importes)
            elif nom_fichier == "trajets.csv":
                propre, avertissements = fiabiliser_trajet(ligne, stations, deja_importes)
            else:
                propre, avertissements = fiabiliser_incident(ligne, stations, deja_importes)
        except Rejet as rejet:
            journal.append(journal_line(
                nom_fichier,
                ligne[colonne_id],
                rejet.colonne,
                rejet.valeur,
                rejet.motif,
                "rejet",
            ))
            nb_rejets += 1
            continue

        for avertissement in avertissements:
            journal.append(journal_line(
                nom_fichier,
                propre[colonne_id],
                avertissement.colonne,
                avertissement.valeur,
                avertissement.motif,
                "normalisation",
            ))

        db.add(modele(**propre))
        deja_importes.add(propre[colonne_id])

    return {
        "lignes": len(lignes),
        "importees": len(deja_importes),
        "rejetees": nb_rejets,
        "doublons": len(doublons),
        "identifiants": deja_importes,
    }


def ecrire_journal(journal):
    """Écrit le journal des rejets et avertissements au format CSV."""

    with open(CHEMIN_JOURNAL, "w", encoding="utf-8", newline="") as fichier:
        writer = csv.writer(fichier)
        writer.writerow(COLONNES_JOURNAL)
        writer.writerows(journal)


def main():
    journal = []
    bilan = {}

    with SessionLocal() as db:
        db.execute(delete(Trajet))
        db.execute(delete(Incident))
        db.execute(delete(Station))


        bilan["stations.csv"] = importer_fichier(
            db, journal, "stations.csv", Station, "station_id", None
        )
        db.flush()
        stations = bilan["stations.csv"]["identifiants"]

        bilan["trajets.csv"] = importer_fichier(
            db, journal, "trajets.csv", Trajet, "trajet_id", stations
        )
        bilan["incidents.csv"] = importer_fichier(
            db, journal, "incidents.csv", Incident, "incident_id", stations
        )

        db.commit()

    ecrire_journal(journal)

    for nom_fichier, compteurs in bilan.items():
        print(
            f"{nom_fichier} : {compteurs['lignes']} lignes = "
            f"{compteurs['importees']} importées + "
            f"{compteurs['rejetees']} rejetées + "
            f"{compteurs['doublons']} doublons écartés"
        )
    print(f"Journal : {CHEMIN_JOURNAL.relative_to(RACINE)} ({len(journal)} lignes)")


if __name__ == "__main__":
    main()
