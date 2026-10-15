"""Test de non-régression de l'anomalie ANO-004 (« Page 9 sur 6 »)."""

import sys
from pathlib import Path

import pytest

# Les fonctions communes du front sont dans front/, qui n'est pas un paquet Python.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "front"))

from session import page_label


@pytest.mark.parametrize(
    "page, nb_pages, attendu",
    [
        pytest.param(1, 6, "Page 1 sur 6", id="premiere_page"),
        pytest.param(6, 6, "Page 6 sur 6", id="derniere_page"),
        pytest.param(9, 6, "Page 9 : la dernière page est la page 6.", id="au_dela_de_la_fin"),
        pytest.param(2, 1, "Page 2 : la dernière page est la page 1.", id="une_seule_page"),
    ],
)
def test_texte_de_la_page(page, nb_pages, attendu):
    """Au-delà de la dernière page, le texte ne dit plus « Page 9 sur 6 » (ANO-004)."""

    assert page_label(page, nb_pages) == attendu
