import os
import secrets

import bcrypt
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import get_db
from api.main import app
from api.models import Utilisateur

load_dotenv()

engine_test = create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
SessionTest = sessionmaker(bind=engine_test, autoflush=False)


@pytest.fixture()
def db_session():
    """Session sur la base de test, annulée à la fin du test.

    Tout ce que le test insère ou modifie est effacé par le rollback :
    la base de test reste vide d'un test à l'autre.
    """

    connexion = engine_test.connect()
    transaction = connexion.begin()
    session = SessionTest(bind=connexion, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connexion.close()


@pytest.fixture()
def client(db_session):
    """Appelle l'API en mémoire (sans Uvicorn), branchée sur la base de test."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def mot_de_passe_test():
    """Mot de passe tiré au hasard à chaque lancement : aucun secret dans le code."""

    return secrets.token_urlsafe(16)


@pytest.fixture(scope="session")
def hachage_test(mot_de_passe_test):
    """Hachage bcrypt du mot de passe de test, calculé une seule fois.

    rounds=4 (au lieu de 12) : suffisant pour des tests, et bien plus rapide.
    """

    return bcrypt.hashpw(
        mot_de_passe_test.encode("utf-8"),
        bcrypt.gensalt(rounds=4),
    ).decode("utf-8")


@pytest.fixture()
def utilisateurs(db_session, hachage_test):
    """Un compte exploitant et un compte direction dans la base de test."""

    db_session.add_all([
        Utilisateur(username="exploitant_test", mot_de_passe_hash=hachage_test, role="exploitant"),
        Utilisateur(username="direction_test", mot_de_passe_hash=hachage_test, role="direction"),
    ])
    db_session.flush()


def _login_and_get_token(client, username, password):
    """Effectue un vrai login comme le ferait un client de l'API."""

    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 200

    return response.json()["access_token"]


@pytest.fixture()
def jeton_exploitant(client, utilisateurs, mot_de_passe_test):
    """En-tête Authorization d'un utilisateur exploitant."""

    jeton = _login_and_get_token(client, "exploitant_test", mot_de_passe_test)
    return {"Authorization": f"Bearer {jeton}"}


@pytest.fixture()
def jeton_direction(client, utilisateurs, mot_de_passe_test):
    """En-tête Authorization d'un utilisateur direction."""

    jeton = _login_and_get_token(client, "direction_test", mot_de_passe_test)
    return {"Authorization": f"Bearer {jeton}"}
