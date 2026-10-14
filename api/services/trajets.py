"""Lecture des trajets en base (appelé par le routeur trajets)."""

from datetime import date

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.orm import Session

from api.models import Trajet


def list_trajets(
    db: Session,
    date_debut: date | None,
    date_fin: date | None,
    station: str | None,
    page: int,
    page_size: int,
) -> tuple[int, list[Trajet]]:
    """Retourne le nombre total de trajets filtrés et ceux de la page demandée.

    Les trajets sont triés par horodatage de départ croissant.
    """

    # On rassemble les filtres demandés dans une liste, pour les appliquer à la fois au comptage et à la page.
    filtres = []

    jour_depart = cast(Trajet.depart_horodatage, Date)

    if date_debut is not None:
        filtres.append(jour_depart >= date_debut)
    if date_fin is not None:
        filtres.append(jour_depart <= date_fin)
    if station is not None:
        filtres.append(
            or_(Trajet.station_depart == station, Trajet.station_arrivee == station)
        )

    
    total = db.scalar(select(func.count()).select_from(Trajet).where(*filtres))

    offset = (page - 1) * page_size

    trajets = db.scalars(
        select(Trajet)
        .where(*filtres)
        # trajet_id départage deux trajets partis à la même seconde.
        .order_by(Trajet.depart_horodatage, Trajet.trajet_id)
        .offset(offset)
        .limit(page_size)
    ).all()

    return total, list(trajets)
