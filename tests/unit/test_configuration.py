"""Test de non-régression de l'anomalie ANO-002 (temps de réponse du front).

Sous Windows, appeler l'API à l'adresse « localhost » ajoute environ
2 secondes à chaque appel : la configuration fournie doit utiliser 127.0.0.1.
"""

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent


def test_adresse_api_sans_localhost():
    """API_URL dans .env.example utilise 127.0.0.1 et non localhost (ANO-002)."""

    lignes = (RACINE / ".env.example").read_text(encoding="utf-8").splitlines()
    api_url = [ligne for ligne in lignes if ligne.startswith("API_URL=")]

    assert api_url == ["API_URL=http://127.0.0.1:8000"]


def test_adresse_api_par_defaut_sans_localhost():
    """L'adresse par défaut du client HTTP du front utilise 127.0.0.1 (ANO-002)."""

    code = (RACINE / "front" / "api_client.py").read_text(encoding="utf-8")

    assert 'os.getenv("API_URL", "http://127.0.0.1:8000")' in code
