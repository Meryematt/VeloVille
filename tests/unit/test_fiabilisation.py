"""Tests unitaires des règles de fiabilisation.

Aucune base de données n'est nécessaire : les fonctions testées sont pures.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from api.services.fiabilisation import (
    Rejet,
    convertir_date,
    convertir_decimal,
    fiabiliser_incident,
    fiabiliser_station,
    fiabiliser_trajet,
    normaliser_horodatage,
    normaliser_statut,
    normaliser_velo_id,
    separer_doublons,
    signaler_technicien_absent,
    verifier_capacite,
    verifier_cible,
    verifier_duree,
    verifier_identifiant_unique,
    verifier_obligatoire,
    verifier_resolution,
    verifier_station,
    verifier_usager,
)

# Petit référentiel utilisé par les tests de stations.
STATIONS = {"S001", "S002", "S003"}


# Horodatages

def test_horodatage_au_format_attendu():
    """Un horodatage AAAA-MM-JJ HH:MM:SS est accepté sans avertissement."""

    horodatage, avertissement = normaliser_horodatage(
        "depart_horodatage",
        "2026-08-24 08:39:56",
    )

    assert horodatage == datetime(2026, 8, 24, 8, 39, 56)
    assert avertissement is None


def test_horodatage_sans_secondes():
    """Le format des incidents (sans secondes) est accepté sans avertissement."""

    horodatage, avertissement = normaliser_horodatage(
        "date_signalement",
        "2026-08-05 15:00",
    )

    assert horodatage == datetime(2026, 8, 5, 15, 0)
    assert avertissement is None


def test_horodatage_francais_normalise():
    """Un horodatage JJ/MM/AAAA est converti, avec un avertissement."""

    horodatage, avertissement = normaliser_horodatage(
        "depart_horodatage",
        "24/08/2026 11:01",
    )

    assert horodatage == datetime(2026, 8, 24, 11, 1)
    assert avertissement is not None
    assert avertissement.colonne == "depart_horodatage"
    assert avertissement.valeur == "24/08/2026 11:01"


def test_horodatage_illisible_rejete():
    """Un texte qui n'est pas une date est rejeté."""

    with pytest.raises(Rejet) as erreur:
        normaliser_horodatage("depart_horodatage", "hier soir")

    assert erreur.value.colonne == "depart_horodatage"


def test_horodatage_vide_rejete():
    """Un horodatage obligatoire absent est rejeté."""

    with pytest.raises(Rejet):
        normaliser_horodatage("depart_horodatage", "")


# Identifiant de vélo

def test_velo_id_correct():
    """Un identifiant déjà correct est accepté sans avertissement."""

    velo_id, avertissement = normaliser_velo_id("V1167")

    assert velo_id == "V1167"
    assert avertissement is None


def test_velo_id_minuscule_normalise():
    """Un identifiant en minuscule est mis en majuscule, avec avertissement."""

    velo_id, avertissement = normaliser_velo_id("v1281")

    assert velo_id == "V1281"
    assert avertissement is not None
    assert avertissement.valeur == "v1281"


def test_velo_id_invalide_rejete():
    """Un identifiant qui ne respecte pas V + 4 chiffres est rejeté."""

    with pytest.raises(Rejet) as erreur:
        normaliser_velo_id("V12")

    assert erreur.value.colonne == "velo_id"


# Statut d'incident

def test_statut_correct():
    """Un statut déjà correct est accepté sans avertissement."""

    statut, avertissement = normaliser_statut("en_cours")

    assert statut == "en_cours"
    assert avertissement is None


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        ("Ouvert", "ouvert"),
        ("RESOLU", "resolu"),
        ("Resolu", "resolu"),
        ("En cours", "en_cours"),
        ("en cours", "en_cours"),
    ],
)
def test_statut_normalise(valeur, attendu):
    """Les variantes de casse et d'espace rencontrées sont normalisées."""

    statut, avertissement = normaliser_statut(valeur)

    assert statut == attendu
    assert avertissement is not None


def test_statut_inconnu_rejete():
    """Un statut hors des trois valeurs est rejeté (RG7)."""

    with pytest.raises(Rejet) as erreur:
        normaliser_statut("annule")

    assert erreur.value.colonne == "statut"


# Durée d'un trajet

def test_duree_positive():
    """Une durée entière positive est acceptée et convertie en entier."""

    assert verifier_duree("215") == 215


@pytest.mark.parametrize("valeur", ["0", "-45", "-120"])
def test_duree_nulle_ou_negative_rejetee(valeur):
    """Une durée nulle ou négative est rejetée (RG4)."""

    with pytest.raises(Rejet) as erreur:
        verifier_duree(valeur)

    assert erreur.value.colonne == "duree_secondes"


def test_duree_non_entiere_rejetee():
    """Une durée qui n'est pas un nombre entier est rejetée (RG4)."""

    with pytest.raises(Rejet):
        verifier_duree("12.5")


# Référence de station

def test_station_existante():
    """Une station du référentiel est acceptée."""

    assert verifier_station("station_depart", "S001", STATIONS, True) == "S001"


def test_station_inconnue_rejetee():
    """Une station absente du référentiel est rejetée (RG2)."""

    with pytest.raises(Rejet) as erreur:
        verifier_station("station_arrivee", "S999", STATIONS, False)

    assert erreur.value.colonne == "station_arrivee"
    assert erreur.value.valeur == "S999"


def test_station_facultative_absente():
    """Une station d'arrivée vide est acceptée et vaut None (RG3)."""

    assert verifier_station("station_arrivee", "", STATIONS, False) is None


def test_station_obligatoire_absente_rejetee():
    """Une station de départ vide est rejetée (RG2)."""

    with pytest.raises(Rejet):
        verifier_station("station_depart", "", STATIONS, True)


# Type d'usager et pseudonyme

def test_abonne_avec_pseudonyme():
    """Un abonné avec pseudonyme est accepté."""

    assert verifier_usager("abonne", "Ued311b7d") == ("abonne", "Ued311b7d")


def test_occasionnel_sans_pseudonyme():
    """Un occasionnel sans pseudonyme est accepté, le pseudonyme vaut None."""

    assert verifier_usager("occasionnel", "") == ("occasionnel", None)


def test_abonne_sans_pseudonyme_rejete():
    """Un abonné sans pseudonyme est rejeté (RG5)."""

    with pytest.raises(Rejet) as erreur:
        verifier_usager("abonne", "")

    assert erreur.value.colonne == "usager_ref"


def test_occasionnel_avec_pseudonyme_rejete():
    """Un occasionnel avec pseudonyme est rejeté (RG5)."""

    with pytest.raises(Rejet):
        verifier_usager("occasionnel", "Ued311b7d")


def test_type_usager_inconnu_rejete():
    """Un type d'usager hors des deux valeurs est rejeté."""

    with pytest.raises(Rejet) as erreur:
        verifier_usager("touriste", "")

    assert erreur.value.colonne == "type_usager"


# Doublons

def test_doublons_separes():
    """Seule la première occurrence d'une ligne identique est conservée."""

    ligne_a = {"trajet_id": "T1", "duree_secondes": "100"}
    ligne_b = {"trajet_id": "T2", "duree_secondes": "200"}

    uniques, doublons = separer_doublons([ligne_a, ligne_b, dict(ligne_a)])

    assert uniques == [ligne_a, ligne_b]
    assert doublons == [ligne_a]


def test_meme_identifiant_contenu_different_pas_doublon():
    """Deux lignes de même identifiant mais de contenu différent ne sont
    pas des doublons stricts : la règle de doublon ne les fusionne pas."""

    ligne_a = {"trajet_id": "T1", "duree_secondes": "100"}
    ligne_a_modifiee = {"trajet_id": "T1", "duree_secondes": "999"}

    uniques, doublons = separer_doublons([ligne_a, ligne_a_modifiee])

    assert len(uniques) == 2
    assert doublons == []


# Cible d'un incident

def test_cible_velo_correcte():
    """Un incident sur un vélo avec un vélo et sans station est accepté."""

    assert verifier_cible("velo", "V0745", None) == "velo"


def test_cible_station_correcte():
    """Un incident sur une station avec une station et sans vélo est accepté."""

    assert verifier_cible("station", None, "S001") == "station"


@pytest.mark.parametrize(
    ("cible", "velo_id", "station_id"),
    [
        ("velo", None, None),
        ("velo", "V0745", "S001"),
        ("station", None, None),
        ("station", "V0745", "S001"),
        ("borne", None, "S001"),
    ],
)
def test_cible_incoherente_rejetee(cible, velo_id, station_id):
    """Un incident qui ne vise pas exactement un équipement est rejeté (RG6)."""

    with pytest.raises(Rejet) as erreur:
        verifier_cible(cible, velo_id, station_id)

    assert erreur.value.colonne == "cible"


# Date de résolution d'un incident

SIGNALEMENT = datetime(2026, 7, 23, 18, 0)


def test_resolution_coherente():
    """Un incident résolu après son signalement est accepté."""

    verifier_resolution("resolu", SIGNALEMENT, datetime(2026, 7, 24, 9, 0))


def test_incident_ouvert_sans_resolution():
    """Un incident ouvert sans date de résolution est accepté."""

    verifier_resolution("ouvert", SIGNALEMENT, None)


def test_resolution_avant_signalement_rejetee():
    """Une résolution antérieure au signalement est rejetée (RG8)."""

    with pytest.raises(Rejet) as erreur:
        verifier_resolution("resolu", SIGNALEMENT, datetime(2026, 7, 22, 6, 0))

    assert erreur.value.colonne == "date_resolution"


def test_resolu_sans_date_rejete():
    """Un incident résolu sans date de résolution est rejeté (RG8)."""

    with pytest.raises(Rejet):
        verifier_resolution("resolu", SIGNALEMENT, None)


def test_date_sur_incident_non_resolu_rejetee():
    """Une date de résolution sur un incident en cours est rejetée (RG8)."""

    with pytest.raises(Rejet):
        verifier_resolution("en_cours", SIGNALEMENT, datetime(2026, 7, 24, 9, 0))


# Technicien

def test_technicien_present():
    """Un incident pris en charge avec technicien ne produit aucun avertissement."""

    assert signaler_technicien_absent("en_cours", "A. Diallo") is None


def test_technicien_absent_incident_ouvert():
    """Un incident ouvert peut ne pas avoir encore de technicien."""

    assert signaler_technicien_absent("ouvert", "") is None


@pytest.mark.parametrize("statut", ["en_cours", "resolu"])
def test_technicien_absent_signale(statut):
    """Un incident pris en charge sans technicien produit un avertissement."""

    avertissement = signaler_technicien_absent(statut, "")

    assert avertissement is not None
    assert avertissement.colonne == "technicien"


# Valeurs génériques

def test_valeur_obligatoire_presente():
    """Une valeur renseignée est acceptée, sans ses espaces."""

    assert verifier_obligatoire("nom", " Lille - Gare ") == "Lille - Gare"


def test_valeur_obligatoire_absente_rejetee():
    """Une valeur obligatoire vide est rejetée."""

    with pytest.raises(Rejet) as erreur:
        verifier_obligatoire("nom", "  ")

    assert erreur.value.colonne == "nom"


def test_identifiant_nouveau():
    """Un identifiant pas encore retenu est accepté."""

    assert verifier_identifiant_unique("trajet_id", "T2", {"T1"}) == "T2"


def test_identifiant_deja_present_rejete():
    """Un identifiant déjà retenu est rejeté."""

    with pytest.raises(Rejet):
        verifier_identifiant_unique("trajet_id", "T1", {"T1"})


def test_decimal_converti():
    """Une coordonnée est convertie en Decimal ; vide donne None."""

    assert convertir_decimal("latitude", "50.59932") == Decimal("50.59932")
    assert convertir_decimal("latitude", "") is None


def test_decimal_illisible_rejete():
    """Une coordonnée qui n'est pas un nombre est rejetée."""

    with pytest.raises(Rejet):
        convertir_decimal("latitude", "nord")


def test_date_convertie():
    """Une date AAAA-MM-JJ est convertie ; vide donne None."""

    assert convertir_date("date_mise_en_service", "2023-08-07") == date(2023, 8, 7)
    assert convertir_date("date_mise_en_service", "") is None


def test_date_illisible_rejetee():
    """Une date dans un autre format est rejetée."""

    with pytest.raises(Rejet):
        convertir_date("date_mise_en_service", "07/08/2023")


# Capacité d'une station

def test_capacite_positive():
    """Une capacité entière positive est acceptée (RG1)."""

    assert verifier_capacite("15") == 15


@pytest.mark.parametrize("valeur", ["0", "-5", "quinze"])
def test_capacite_invalide_rejetee(valeur):
    """Une capacité nulle, négative ou non entière est rejetée (RG1)."""

    with pytest.raises(Rejet) as erreur:
        verifier_capacite(valeur)

    assert erreur.value.colonne == "capacite"


# Lignes complètes (exemples tirés des CSV fournis)

LIGNE_STATION = {
    "station_id": "S001",
    "nom": "Lille - Gare",
    "commune": "Lille",
    "capacite": "15",
    "latitude": "50.59932",
    "longitude": "3.21953",
    "date_mise_en_service": "2023-08-07",
}

LIGNE_TRAJET = {
    "trajet_id": "T480001",
    "velo_id": "V1167",
    "depart_horodatage": "2026-08-24 08:39:56",
    "station_depart": "S001",
    "station_arrivee": "S002",
    "duree_secondes": "215",
    "type_usager": "abonne",
    "usager_ref": "Ued311b7d",
}

LIGNE_INCIDENT = {
    "incident_id": "I2026-0001",
    "date_signalement": "2026-08-05 15:00",
    "cible": "velo",
    "velo_id": "V0745",
    "station_id": "",
    "type_incident": "vandalisme",
    "statut": "En cours",
    "date_resolution": "",
    "technicien": "A. Diallo",
}


def test_station_complete():
    """Une ligne de station correcte est entièrement convertie."""

    station, avertissements = fiabiliser_station(LIGNE_STATION, set())

    assert station["station_id"] == "S001"
    assert station["capacite"] == 15
    assert station["latitude"] == Decimal("50.59932")
    assert station["date_mise_en_service"] == date(2023, 8, 7)
    assert avertissements == []


def test_trajet_complet():
    """Une ligne de trajet correcte est acceptée sans avertissement."""

    trajet, avertissements = fiabiliser_trajet(LIGNE_TRAJET, STATIONS, set())

    assert trajet["depart_horodatage"] == datetime(2026, 8, 24, 8, 39, 56)
    assert trajet["duree_secondes"] == 215
    assert avertissements == []


def test_trajet_normalise_garde_ses_avertissements():
    """Un trajet corrigé à deux endroits produit deux avertissements."""

    ligne = LIGNE_TRAJET | {
        "velo_id": "v1167",
        "depart_horodatage": "24/08/2026 08:39",
    }

    trajet, avertissements = fiabiliser_trajet(ligne, STATIONS, set())

    assert trajet["velo_id"] == "V1167"
    assert [a.colonne for a in avertissements] == ["velo_id", "depart_horodatage"]


def test_trajet_vers_station_inconnue_rejete():
    """Un trajet vers une station inconnue est rejeté (RG2)."""

    ligne = LIGNE_TRAJET | {"station_arrivee": "S999"}

    with pytest.raises(Rejet) as erreur:
        fiabiliser_trajet(ligne, STATIONS, set())

    assert erreur.value.colonne == "station_arrivee"


def test_incident_complet_normalise():
    """Un incident « En cours » est importé avec son statut normalisé."""

    incident, avertissements = fiabiliser_incident(LIGNE_INCIDENT, STATIONS, set())

    assert incident["statut"] == "en_cours"
    assert incident["velo_id"] == "V0745"
    assert incident["station_id"] is None
    assert [a.colonne for a in avertissements] == ["statut"]


def test_incident_resolu_sans_technicien_avertit():
    """Un incident résolu sans technicien est importé avec un avertissement."""

    ligne = LIGNE_INCIDENT | {
        "statut": "resolu",
        "date_resolution": "2026-08-07 10:00",
        "technicien": "",
    }

    incident, avertissements = fiabiliser_incident(ligne, STATIONS, set())

    assert incident["technicien"] is None
    assert [a.colonne for a in avertissements] == ["technicien"]


def test_incident_resolu_avant_signalement_rejete():
    """Un incident résolu avant son signalement est rejeté (RG8)."""

    ligne = LIGNE_INCIDENT | {
        "statut": "Resolu",
        "date_resolution": "2026-08-04 10:00",
    }

    with pytest.raises(Rejet) as erreur:
        fiabiliser_incident(ligne, STATIONS, set())

    assert erreur.value.colonne == "date_resolution"
