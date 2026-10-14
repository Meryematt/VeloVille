"""Routeur indicateurs : les trois indicateurs du cahier des charges."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import (
    ActiveStationsResponse,
    DailyActivityResponse,
    IncidentsByStatusResponse,
)
from api.securite import get_current_user
from api.services.indicateurs import (
    activite_par_jour,
    incidents_par_statut,
    stations_actives,
)

router = APIRouter(
    prefix="/indicateurs",
    tags=["Indicateurs"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/activite-par-jour", response_model=DailyActivityResponse)
def read_daily_activity(
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
):
    """Nombre de trajets par jour sur la période (bornes incluses)."""

    return activite_par_jour(db, date_debut, date_fin)


@router.get("/stations-actives", response_model=ActiveStationsResponse)
def read_active_stations(
    limite: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Les stations ayant le plus de départs et d'arrivées."""

    return stations_actives(db, limite)


@router.get("/incidents-par-statut", response_model=IncidentsByStatusResponse)
def read_incidents_by_status(db: Session = Depends(get_db)):
    """Nombre d'incidents par statut et délai moyen de résolution."""

    return incidents_par_statut(db)
