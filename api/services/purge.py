"""Purge des trajets anciens (durée de conservation, RGPD).

Appelé par scripts/purge.py.
"""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from api.models import Trajet


def purge_old_trips(db: Session, date_limite: datetime, executer: bool) -> int:
    """Compte les trajets partis avant date_limite et, si executer est vrai, les supprime. Retourne le nombre de trajets concernés.
    """

    nombre = db.scalar(
        select(func.count())
        .select_from(Trajet)
        .where(Trajet.depart_horodatage < date_limite)
    )

    # En simulation, on s'arrête là : rien n'est supprimé.
    if executer:
        db.execute(delete(Trajet).where(Trajet.depart_horodatage < date_limite))
        db.commit()

    return nombre
