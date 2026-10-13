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
)


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
