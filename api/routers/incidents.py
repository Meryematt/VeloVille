"""Routeur incidents : GET /incidents et PUT /incidents/{incident_id}/statut."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import IncidentResponse, PaginatedIncidentsResponse, StatusUpdateRequest
from api.securite import get_current_user, require_roles
from api.services.incidents import (
    InvalidTransitionError,
    list_incidents,
    update_incident_status,
)

router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=PaginatedIncidentsResponse)
def read_incidents(
    # Literal : seules ces trois valeurs sont acceptées, sinon 422.
    statut: Literal["ouvert", "en_cours", "resolu"] | None = None,
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Liste paginée des incidents, filtrable par statut."""

    total, incidents = list_incidents(db, statut, page, taille_page)

    return PaginatedIncidentsResponse(
        total=total,
        page=page,
        taille_page=taille_page,
        resultats=incidents,
    )


@router.put(
    "/{incident_id}/statut",
    response_model=IncidentResponse,
    # En plus du jeton, ce rôle est exigé : la direction reçoit 403.
    dependencies=[Depends(require_roles("exploitant"))],
)
def change_incident_status(
    incident_id: str,
    donnees: StatusUpdateRequest,
    db: Session = Depends(get_db),
):
    """Fait évoluer le statut d'un incident (rôle exploitant uniquement)."""

    try:
        incident = update_incident_status(db, incident_id, donnees.statut)
    except InvalidTransitionError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Transition de statut non autorisee",
        )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident introuvable",
        )

    return incident
