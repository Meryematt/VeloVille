"""Lecture des stations en base (appelé par le routeur stations)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.models import Station


def list_stations(
    db: Session,
    commune: str | None,
    page: int,
    page_size: int,
) -> tuple[int, list[Station]]:
    """Retourne le nombre total de stations et celles de la page demandée.

    Les stations sont triées par station_id.
    """

    requete_total = select(func.count()).select_from(Station)
    requete = select(Station)

    # Le filtre n'est ajouté que si une commune est demandée.
    if commune is not None:
        requete_total = requete_total.where(Station.commune == commune)
        requete = requete.where(Station.commune == commune)

    # COUNT(*) : nombre TOTAL de stations, indépendamment de la page.
    total = db.scalar(requete_total)

    # page=1 -> on saute 0 ligne ; page=2 -> on saute page_size lignes...
    offset = (page - 1) * page_size

    stations = db.scalars(
        requete.order_by(Station.station_id).offset(offset).limit(page_size)
    ).all()

    return total, list(stations)


def get_station(db: Session, station_id: str) -> Station | None:
    """Retourne une station par son identifiant, ou None si elle n'existe pas."""

    return db.get(Station, station_id)
