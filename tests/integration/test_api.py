"""Tests d'intégration de l'API avec TestClient, sur la base de test."""

from datetime import datetime

import pytest

from api.models import Incident, Station, Trajet


@pytest.fixture()
def donnees(db_session):
    """Un petit jeu de données : 3 stations, 2 trajets, 2 incidents."""

    db_session.add_all([
        Station(station_id="S001", nom="Lille - Gare", commune="Lille", capacite=15),
        Station(station_id="S002", nom="Lille - Mairie", commune="Lille", capacite=30),
        Station(station_id="S003", nom="Roubaix - Gare", commune="Roubaix", capacite=20),
    ])
    db_session.flush()

    db_session.add_all([
        Trajet(trajet_id="T1", velo_id="V0001", depart_horodatage=datetime(2026, 8, 24, 8, 0),
               station_depart="S001", station_arrivee="S002", duree_secondes=600,
               type_usager="occasionnel"),
        Trajet(trajet_id="T2", velo_id="V0002", depart_horodatage=datetime(2026, 8, 25, 9, 0),
               station_depart="S003", station_arrivee=None, duree_secondes=600,
               type_usager="occasionnel"),
        Incident(incident_id="I1", date_signalement=datetime(2026, 8, 1, 8, 0),
                 cible="velo", velo_id="V0001", type_incident="pneu creve",
                 statut="ouvert"),
        Incident(incident_id="I2", date_signalement=datetime(2026, 8, 2, 8, 0),
                 cible="station", station_id="S001", type_incident="borne hors service",
                 statut="en_cours", technicien="A. Diallo"),
    ])
    db_session.flush()


# Santé et connexion

def test_sante(client):
    """GET /sante répond sans jeton."""

    response = client.get("/sante")

    assert response.status_code == 200
    assert response.json() == {"statut": "ok"}


def test_login_ok(client, utilisateurs, mot_de_passe_test):
    """Des identifiants valides retournent un JWT et le rôle."""

    response = client.post(
        "/auth/login",
        json={"username": "exploitant_test", "password": mot_de_passe_test},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["role"] == "exploitant"


def test_login_mauvais_mot_de_passe(client, utilisateurs):
    """Un mauvais mot de passe produit 401."""

    response = client.post(
        "/auth/login",
        json={"username": "exploitant_test", "password": "mauvais"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Identifiants invalides"}


def test_login_utilisateur_inconnu_meme_message(client, utilisateurs, mot_de_passe_test):
    """Un identifiant inconnu produit le même message qu'un mauvais mot de passe."""

    response = client.post(
        "/auth/login",
        json={"username": "inconnu", "password": mot_de_passe_test},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Identifiants invalides"}


# Protection des routes

def test_route_protegee_sans_jeton(client):
    """Une route protégée appelée sans jeton produit 401."""

    response = client.get("/stations")

    assert response.status_code == 401


def test_route_protegee_jeton_invalide(client):
    """Un faux jeton produit également 401."""

    response = client.get(
        "/stations",
        headers={"Authorization": "Bearer jeton.invalide.xyz"},
    )

    assert response.status_code == 401


def test_jeton_modifie_refuse(client, jeton_direction):
    """Un jeton modifié d'un seul caractère est refusé (401)."""

    jeton = jeton_direction["Authorization"]
    dernier = "A" if jeton[-1] != "A" else "B"

    response = client.get("/stations", headers={"Authorization": jeton[:-1] + dernier})

    assert response.status_code == 401


# Stations

def test_stations_pagination(client, jeton_direction, donnees):
    """L'enveloppe paginée contient le total et la page demandée."""

    response = client.get(
        "/stations",
        params={"page": 1, "taille_page": 2},
        headers=jeton_direction,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 3
    assert data["page"] == 1
    assert data["taille_page"] == 2
    assert [s["station_id"] for s in data["resultats"]] == ["S001", "S002"]


def test_stations_filtre_commune(client, jeton_direction, donnees):
    """Le filtre commune ne garde que les stations de cette commune."""

    response = client.get("/stations", params={"commune": "Roubaix"}, headers=jeton_direction)

    assert response.json()["total"] == 1
    assert response.json()["resultats"][0]["station_id"] == "S003"


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"page": 0}, id="page_0"),
        pytest.param({"taille_page": 0}, id="taille_page_0"),
        pytest.param({"taille_page": 101}, id="taille_page_101"),
    ],
)
def test_stations_parametres_hors_bornes(client, jeton_direction, params):
    """Une page ou une taille de page hors bornes produit 422."""

    response = client.get("/stations", params=params, headers=jeton_direction)

    assert response.status_code == 422


def test_station_introuvable(client, jeton_direction, donnees):
    """Une station inexistante produit 404 avec le message du contrat."""

    response = client.get("/stations/S999", headers=jeton_direction)

    assert response.status_code == 404
    assert response.json() == {"detail": "Station introuvable"}


# Trajets

def test_trajets_filtre_station(client, jeton_direction, donnees):
    """Le filtre station retient le départ OU l'arrivée."""

    response = client.get("/trajets", params={"station": "S002"}, headers=jeton_direction)

    assert response.status_code == 200
    assert [t["trajet_id"] for t in response.json()["resultats"]] == ["T1"]


def test_trajets_filtre_dates(client, jeton_direction, donnees):
    """Les bornes de dates sont incluses."""

    response = client.get(
        "/trajets",
        params={"date_debut": "2026-08-25", "date_fin": "2026-08-25"},
        headers=jeton_direction,
    )

    assert [t["trajet_id"] for t in response.json()["resultats"]] == ["T2"]


# Incidents

def test_incidents_tries_du_plus_recent(client, jeton_direction, donnees):
    """La direction peut lire les incidents, du plus récent au plus ancien."""

    response = client.get("/incidents", headers=jeton_direction)

    assert response.status_code == 200
    assert [i["incident_id"] for i in response.json()["resultats"]] == ["I2", "I1"]


def test_put_statut_direction_interdit(client, jeton_direction, donnees, db_session):
    """Le rôle direction reçoit 403 et le statut n'est pas modifié."""

    response = client.put(
        "/incidents/I1/statut",
        json={"statut": "en_cours"},
        headers=jeton_direction,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Acces reserve au role exploitant"}
    assert db_session.get(Incident, "I1").statut == "ouvert"


def test_put_statut_exploitant_autorise(client, jeton_exploitant, donnees, db_session):
    """L'exploitant fait passer un incident de ouvert à en_cours."""

    response = client.put(
        "/incidents/I1/statut",
        json={"statut": "en_cours"},
        headers=jeton_exploitant,
    )

    assert response.status_code == 200
    assert response.json()["statut"] == "en_cours"
    assert db_session.get(Incident, "I1").statut == "en_cours"


def test_put_statut_transition_interdite(client, jeton_exploitant, donnees):
    """Une transition non autorisée (en_cours -> en_cours) produit 422."""

    response = client.put(
        "/incidents/I2/statut",
        json={"statut": "en_cours"},
        headers=jeton_exploitant,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Transition de statut non autorisee"}


def test_put_statut_resolu_remplit_la_date(client, jeton_exploitant, donnees):
    """Le passage à resolu renseigne la date de résolution."""

    response = client.put(
        "/incidents/I2/statut",
        json={"statut": "resolu"},
        headers=jeton_exploitant,
    )

    assert response.status_code == 200
    assert response.json()["statut"] == "resolu"
    assert response.json()["date_resolution"] is not None


def test_put_statut_incident_introuvable(client, jeton_exploitant, donnees):
    """Un incident inexistant produit 404 avec le message du contrat."""

    response = client.put(
        "/incidents/I999/statut",
        json={"statut": "resolu"},
        headers=jeton_exploitant,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Incident introuvable"}


# Indicateurs

def test_indicateurs_accessibles_a_la_direction(client, jeton_direction, donnees):
    """Les trois indicateurs répondent 200 au rôle direction."""

    activite = client.get("/indicateurs/activite-par-jour", headers=jeton_direction)
    stations = client.get("/indicateurs/stations-actives", headers=jeton_direction)
    incidents = client.get("/indicateurs/incidents-par-statut", headers=jeton_direction)

    assert activite.status_code == 200
    assert stations.status_code == 200
    assert incidents.status_code == 200
    assert len(activite.json()["donnees"]) == 2


# Pseudonyme d'abonné (non-régression ANO-005)

@pytest.fixture()
def trajet_abonne(db_session, donnees):
    """Un trajet d'abonné, avec son pseudonyme."""

    db_session.add(
        Trajet(trajet_id="T3", velo_id="V0003", depart_horodatage=datetime(2026, 8, 26, 9, 0),
               station_depart="S001", station_arrivee="S002", duree_secondes=600,
               type_usager="abonne", usager_ref="U12345678")
    )
    db_session.flush()


def test_usager_ref_masque_pour_la_direction(client, jeton_direction, trajet_abonne):
    """La direction ne voit pas le pseudonyme de l'abonné (7.3, ANO-005)."""

    response = client.get("/trajets", params={"station": "S001"}, headers=jeton_direction)

    trajets = {t["trajet_id"]: t for t in response.json()["resultats"]}
    assert trajets["T3"]["type_usager"] == "abonne"
    assert trajets["T3"]["usager_ref"] is None


def test_usager_ref_visible_pour_l_exploitant(client, jeton_exploitant, trajet_abonne):
    """L'exploitant voit le pseudonyme, à des fins de support (7.3)."""

    response = client.get("/trajets", params={"station": "S001"}, headers=jeton_exploitant)

    trajets = {t["trajet_id"]: t for t in response.json()["resultats"]}
    assert trajets["T3"]["usager_ref"] == "U12345678"
