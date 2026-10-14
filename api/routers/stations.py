"""Routeur stations : GET /stations et GET /stations/{station_id}."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import PaginatedStationsResponse, StationResponse
from api.securite import get_current_user
from api.services.stations import get_station, list_stations

router = APIRouter(
    prefix="/stations",
    tags=["Stations"],
    # Toutes les routes de ce routeur exigent un jeton valide (sinon 401).
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=PaginatedStationsResponse)
def read_stations(
    commune: str | None = None,
    # Query() valide directement les paramètres : hors bornes -> 422.
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Liste paginée des stations, filtrable par commune."""

    total, stations = list_stations(db, commune, page, taille_page)

    return PaginatedStationsResponse(
        total=total,
        page=page,
        taille_page=taille_page,
        resultats=stations,
    )


@router.get("/{station_id}", response_model=StationResponse)
def read_station(station_id: str, db: Session = Depends(get_db)):
    """Une station par son identifiant."""

    station = get_station(db, station_id)

    if station is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station introuvable",
        )

    return station
