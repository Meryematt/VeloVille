"""Authentification et autorisation : bcrypt, JWT et dépendances FastAPI."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import JWT_ALGORITHM, JWT_EXPIRATION_MINUTES, JWT_SECRET
from api.database import get_db
from api.models import Utilisateur


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare le mot de passe saisi avec le hachage stocké en base."""

    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(username: str, role: str) -> str:
    """Crée un JWT signé contenant l'identifiant, le rôle et l'expiration."""

    now = datetime.now(timezone.utc)
    expiration = now + timedelta(minutes=JWT_EXPIRATION_MINUTES)

    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": expiration,
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Vérifie la signature et l'expiration du JWT, puis retourne son contenu."""

    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])



bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    """Vérifie le jeton puis retourne l'utilisateur correspondant (sinon 401)."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # credentials.credentials contient seulement le jeton,
        # sans le préfixe "Bearer".
        payload = decode_access_token(credentials.credentials)
        username = payload.get("sub")

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(Utilisateur).where(Utilisateur.username == username))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur inconnu",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*allowed_roles: str):
    """Crée une dépendance autorisant uniquement certains rôles."""

    def check_role(
        # L'authentification est effectuée avant le contrôle du rôle.
        current_user: Utilisateur = Depends(get_current_user),
    ) -> Utilisateur:

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                # Message imposé par le contrat de l'API.
                detail="Acces reserve au role " + " ou ".join(allowed_roles),
            )

        return current_user

    return check_role
