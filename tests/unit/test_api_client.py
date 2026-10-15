"""Test de non-régression de l'anomalie ANO-003 (trace Python dans le front).

Une adresse d'API mal écrite doit donner une ErreurApi avec un message en
français, et non une erreur de requests qui remonte jusqu'à l'écran.
"""

import sys
from pathlib import Path

import pytest

# Le client du front est dans front/, qui n'est pas un paquet Python.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "front"))

import api_client


def test_adresse_api_mal_ecrite_donne_un_message_francais(monkeypatch):
    """Une adresse invalide lève ErreurApi, avec un message en français (ANO-003)."""

    monkeypatch.setattr(api_client, "API_URL", "API_URL=http://127.0.0.1:8000")

    with pytest.raises(api_client.ErreurApi) as erreur:
        api_client.call_api("GET", "/sante")

    assert "API_URL" in erreur.value.message
    assert erreur.value.code_http is None
