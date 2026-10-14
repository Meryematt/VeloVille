"""Routeur trajets : GET /trajets."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import PaginatedTrajetsResponse
from api.securite import get_current_user
from api.services.trajets import list_trajets

router = APIRouter(
    prefix="/trajets",
    tags=["Trajets"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=PaginatedTrajetsResponse)
def read_trajets(
    # Format AAAA-MM-JJ ; une date invalide renvoie 422.
    date_debut: date | None = None,
    date_fin: date | None = None,
    station: str | None = None,
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Liste paginée des trajets, filtrable par période et par station."""

    total, trajets = list_trajets(db, date_debut, date_fin, station, page, taille_page)

    return PaginatedTrajetsResponse(
        total=total,
        page=page,
        taille_page=taille_page,
        resultats=trajets,
    )
