"""Tests unitaires des règles de fiabilisation.

Aucune base de données n'est nécessaire : les fonctions testées sont pures.
"""

from datetime import datetime

import pytest

from api.services.fiabilisation import (
    Rejet,
    normaliser_horodatage,
    normaliser_statut,
    normaliser_velo_id,
    separer_doublons,
    verifier_duree,
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
