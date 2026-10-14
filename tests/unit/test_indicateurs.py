"""Tests des fonctions de calcul des indicateurs.

Chaque test insère un petit jeu de données connu dans la base de test,
vérifie les agrégats, puis la fixture db_session annule tout.
"""

from datetime import date, datetime

import pytest

from api.models import Incident, Station, Trajet
from api.services.indicateurs import (
    activite_par_jour,
    incidents_par_statut,
    stations_actives,
)


@pytest.fixture()
def stations(db_session):
    """Trois stations de référence."""

    db_session.add_all([
        Station(station_id="S001", nom="Lille - Gare", commune="Lille", capacite=15),
        Station(station_id="S002", nom="Lille - Mairie", commune="Lille", capacite=30),
        Station(station_id="S003", nom="Roubaix - Gare", commune="Roubaix", capacite=20),
    ])
    db_session.flush()


@pytest.fixture()
def trajets(db_session, stations):
    """Quatre trajets sur trois jours.

    S001 : 2 départs + 1 arrivée = 3 mouvements
    S002 : 1 départ + 2 arrivées = 3 mouvements
    S003 : 1 départ             = 1 mouvement
    T3 n'a pas de station d'arrivée : elle ne compte pour personne.
    """

    db_session.add_all([
        Trajet(trajet_id="T1", velo_id="V0001", depart_horodatage=datetime(2026, 8, 24, 8, 0),
               station_depart="S001", station_arrivee="S002", duree_secondes=600,
               type_usager="occasionnel"),
        Trajet(trajet_id="T2", velo_id="V0002", depart_horodatage=datetime(2026, 8, 24, 17, 30),
               station_depart="S002", station_arrivee="S001", duree_secondes=600,
               type_usager="occasionnel"),
        Trajet(trajet_id="T3", velo_id="V0003", depart_horodatage=datetime(2026, 8, 25, 9, 15),
               station_depart="S001", station_arrivee=None, duree_secondes=600,
               type_usager="occasionnel"),
        Trajet(trajet_id="T4", velo_id="V0004", depart_horodatage=datetime(2026, 8, 26, 10, 0),
               station_depart="S003", station_arrivee="S002", duree_secondes=600,
               type_usager="occasionnel"),
    ])
    db_session.flush()


# Indicateur 1 : activité par jour

def test_activite_par_jour_sans_bornes(db_session, trajets):
    """Sans bornes, un élément par jour, trié par jour croissant."""

    resultat = activite_par_jour(db_session)

    assert resultat["donnees"] == [
        {"jour": date(2026, 8, 24), "nb_trajets": 2},
        {"jour": date(2026, 8, 25), "nb_trajets": 1},
        {"jour": date(2026, 8, 26), "nb_trajets": 1},
    ]


def test_activite_par_jour_bornes_incluses(db_session, trajets):
    """Les deux bornes de la période sont incluses."""

    resultat = activite_par_jour(db_session, date(2026, 8, 25), date(2026, 8, 26))

    jours = [element["jour"] for element in resultat["donnees"]]
    assert jours == [date(2026, 8, 25), date(2026, 8, 26)]


def test_activite_par_jour_periode_vide(db_session, trajets):
    """Une période sans trajet donne une liste vide."""

    resultat = activite_par_jour(db_session, date(2026, 9, 1), date(2026, 9, 30))

    assert resultat["donnees"] == []


# Indicateur 2 : stations actives

def test_stations_actives_classement(db_session, trajets):
    """Tri par mouvements décroissants, puis par station_id en cas d'égalité."""

    resultat = stations_actives(db_session, 10)

    assert resultat["donnees"] == [
        {"station_id": "S001", "nom": "Lille - Gare", "nb_departs": 2, "nb_arrivees": 1},
        {"station_id": "S002", "nom": "Lille - Mairie", "nb_departs": 1, "nb_arrivees": 2},
        {"station_id": "S003", "nom": "Roubaix - Gare", "nb_departs": 1, "nb_arrivees": 0},
    ]


def test_stations_actives_limite(db_session, trajets):
    """Seules les « limite » premières stations sont retournées."""

    resultat = stations_actives(db_session, 1)

    assert len(resultat["donnees"]) == 1
    assert resultat["donnees"][0]["station_id"] == "S001"


# Indicateur 3 : incidents par statut

def test_incidents_par_statut(db_session, stations):
    """Comptage par statut et délai moyen des incidents résolus."""

    db_session.add_all([
        Incident(incident_id="I1", date_signalement=datetime(2026, 7, 1, 8, 0),
                 cible="velo", velo_id="V0001", type_incident="pneu creve",
                 statut="ouvert"),
        Incident(incident_id="I2", date_signalement=datetime(2026, 7, 1, 8, 0),
                 cible="station", station_id="S001", type_incident="borne hors service",
                 statut="en_cours", technicien="A. Diallo"),
        # Résolu en 10 heures.
        Incident(incident_id="I3", date_signalement=datetime(2026, 7, 1, 8, 0),
                 cible="velo", velo_id="V0002", type_incident="frein defectueux",
                 statut="resolu", date_resolution=datetime(2026, 7, 1, 18, 0),
                 technicien="K. Mercier"),
        # Résolu en 24 heures.
        Incident(incident_id="I4", date_signalement=datetime(2026, 7, 2, 8, 0),
                 cible="velo", velo_id="V0003", type_incident="vandalisme",
                 statut="resolu", date_resolution=datetime(2026, 7, 3, 8, 0),
                 technicien="K. Mercier"),
    ])
    db_session.flush()

    resultat = incidents_par_statut(db_session)

    assert resultat["donnees"] == [
        {"statut": "en_cours", "nb_incidents": 1},
        {"statut": "ouvert", "nb_incidents": 1},
        {"statut": "resolu", "nb_incidents": 2},
    ]
    assert resultat["delai_moyen_resolution_heures"] == 17.0


def test_incidents_sans_resolu_delai_none(db_session, stations):
    """Sans incident résolu, le délai moyen vaut None."""

    db_session.add(
        Incident(incident_id="I1", date_signalement=datetime(2026, 7, 1, 8, 0),
                 cible="velo", velo_id="V0001", type_incident="pneu creve",
                 statut="ouvert")
    )
    db_session.flush()

    resultat = incidents_par_statut(db_session)

    assert resultat["donnees"] == [{"statut": "ouvert", "nb_incidents": 1}]
    assert resultat["delai_moyen_resolution_heures"] is None
