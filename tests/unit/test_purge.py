"""Tests de la purge des trajets, sur la base de test."""

from datetime import datetime

import pytest
from sqlalchemy import func, select

from api.models import Station, Trajet
from api.services.purge import purge_old_trips

DATE_LIMITE = datetime(2026, 1, 1)


@pytest.fixture()
def trajets_anciens_et_recents(db_session):
    """Deux trajets avant la date limite, un après."""

    db_session.add(Station(station_id="S001", nom="Lille - Gare", commune="Lille", capacite=15))
    db_session.flush()

    db_session.add_all([
        Trajet(trajet_id="T1", velo_id="V0001", depart_horodatage=datetime(2025, 6, 1, 8, 0),
               station_depart="S001", duree_secondes=600, type_usager="occasionnel"),
        Trajet(trajet_id="T2", velo_id="V0002", depart_horodatage=datetime(2025, 12, 31, 23, 0),
               station_depart="S001", duree_secondes=600, type_usager="occasionnel"),
        Trajet(trajet_id="T3", velo_id="V0003", depart_horodatage=datetime(2026, 8, 24, 8, 0),
               station_depart="S001", duree_secondes=600, type_usager="occasionnel"),
    ])
    db_session.flush()


def nombre_de_trajets(db_session):
    return db_session.scalar(select(func.count()).select_from(Trajet))


def test_simulation_ne_supprime_rien(db_session, trajets_anciens_et_recents):
    """En simulation, les trajets anciens sont comptés mais pas supprimés."""

    nombre = purge_old_trips(db_session, DATE_LIMITE, executer=False)

    assert nombre == 2
    assert nombre_de_trajets(db_session) == 3


def test_execution_supprime_les_trajets_anciens(db_session, trajets_anciens_et_recents):
    """Avec executer=True, seuls les trajets antérieurs à la limite disparaissent."""

    nombre = purge_old_trips(db_session, DATE_LIMITE, executer=True)

    assert nombre == 2
    assert nombre_de_trajets(db_session) == 1
    assert db_session.get(Trajet, "T3") is not None


def test_aucun_trajet_ancien(db_session, trajets_anciens_et_recents):
    """Une date limite plus ancienne que tous les trajets ne purge rien."""

    nombre = purge_old_trips(db_session, datetime(2020, 1, 1), executer=True)

    assert nombre == 0
    assert nombre_de_trajets(db_session) == 3
