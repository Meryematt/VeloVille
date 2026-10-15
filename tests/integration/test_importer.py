"""Test de non-régression de l'anomalie ANO-001 (recette REC-02).

L'import des trois vrais CSV est rejoué sur la base de test ; la fixture
db_session annule tout à la fin.
"""

from api.models import Incident, Station, Trajet
from scripts.importer import importer_fichier


def test_journal_porte_les_six_informations(db_session):
    """Chaque ligne du journal porte fichier, identifiant, colonne, valeur,
    motif et décision : aucune case vide (ANO-001)."""

    journal = []

    bilan = importer_fichier(db_session, journal, "stations.csv", Station, "station_id", None)
    db_session.flush()
    stations = bilan["identifiants"]
    importer_fichier(db_session, journal, "trajets.csv", Trajet, "trajet_id", stations)
    importer_fichier(db_session, journal, "incidents.csv", Incident, "incident_id", stations)

    assert len(journal) == 190

    for ligne in journal:
        assert len(ligne) == 6
        assert all(ligne), ligne
