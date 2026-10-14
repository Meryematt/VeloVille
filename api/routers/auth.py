"""Routeur auth : POST /auth/login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Utilisateur
from api.schemas import LoginRequest, TokenResponse
from api.securite import create_access_token, verify_password

router = APIRouter(
    prefix="/auth",
    tags=["Authentification"],
)


@router.post("/login", response_model=TokenResponse)
def login(donnees: LoginRequest, db: Session = Depends(get_db)):
    """Vérifie les identifiants puis délivre un JWT."""

    utilisateur = db.scalar(
        select(Utilisateur).where(Utilisateur.username == donnees.username)
    )

    if utilisateur is None or not verify_password(
        donnees.password,
        utilisateur.mot_de_passe_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
        )

    jeton = create_access_token(utilisateur.username, utilisateur.role)

    return TokenResponse(access_token=jeton, role=utilisateur.role)
