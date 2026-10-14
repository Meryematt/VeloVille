"""Lecture et mise à jour des incidents (appelé par le routeur incidents)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.models import Incident


TRANSITIONS = {
    "ouvert": ["en_cours", "resolu"],
    "en_cours": ["resolu"],
    "resolu": [],
}


class InvalidTransitionError(Exception):
    """Changement de statut interdit par RG7."""


def list_incidents(
    db: Session,
    statut: str | None,
    page: int,
    page_size: int,
) -> tuple[int, list[Incident]]:
    """Retourne le nombre total d'incidents et ceux de la page demandée.

    Les incidents sont triés du plus récent au plus ancien signalement.
    """

    requete_total = select(func.count()).select_from(Incident)
    requete = select(Incident)

    if statut is not None:
        requete_total = requete_total.where(Incident.statut == statut)
        requete = requete.where(Incident.statut == statut)

    total = db.scalar(requete_total)

    offset = (page - 1) * page_size

    incidents = db.scalars(
        requete
        # incident_id départage deux incidents signalés à la même heure.
        .order_by(Incident.date_signalement.desc(), Incident.incident_id)
        .offset(offset)
        .limit(page_size)
    ).all()

    return total, list(incidents)


def update_incident_status(
    db: Session,
    incident_id: str,
    nouveau_statut: str,
) -> Incident | None:
    """Change le statut d'un incident si la transition est autorisée.

    Retourne None si l'incident n'existe pas ; lève InvalidTransitionError
    si la transition est interdite.
    """

    incident = db.get(Incident, incident_id)

    if incident is None:
        return None

    if nouveau_statut not in TRANSITIONS[incident.statut]:
        raise InvalidTransitionError()

    incident.statut = nouveau_statut

    # Le passage à « resolu » renseigne la date de résolution si elle est vide.
    if nouveau_statut == "resolu" and incident.date_resolution is None:
        incident.date_resolution = datetime.now()

    db.commit()

    return incident
