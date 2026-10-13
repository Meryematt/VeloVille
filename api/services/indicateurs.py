"""Calcul des trois indicateurs (module métier testé)."""

from datetime import date

from sqlalchemy import Date, cast, extract, func, literal, select, union_all
from sqlalchemy.orm import Session

from api.models import Incident, Station, Trajet


def activite_par_jour(
    session: Session,
    date_debut: date | None = None,
    date_fin: date | None = None,
) -> dict:
    """Indicateur 1 : nombre de trajets par jour de départ."""

    jour = cast(Trajet.depart_horodatage, Date)

    requete = (
        select(jour.label("jour"), func.count().label("nb_trajets"))
        .group_by(jour)
        .order_by(jour)
    )

    if date_debut is not None:
        requete = requete.where(jour >= date_debut)
    if date_fin is not None:
        requete = requete.where(jour <= date_fin)

    donnees = []
    for ligne in session.execute(requete):
        donnees.append({"jour": ligne.jour, "nb_trajets": ligne.nb_trajets})

    return {"donnees": donnees}


def stations_actives(session: Session, limite: int = 10) -> dict:
    """Indicateur 2 : les stations ayant le plus de départs et d'arrivées."""

    departs = select(
        Trajet.station_depart.label("station_id"),
        literal(1).label("depart"),
        literal(0).label("arrivee"),
    )

    arrivees = select(
        Trajet.station_arrivee.label("station_id"),
        literal(0).label("depart"),
        literal(1).label("arrivee"),
    ).where(Trajet.station_arrivee.is_not(None))

    mouvements = union_all(departs, arrivees).subquery()

    nb_departs = func.sum(mouvements.c.depart)
    nb_arrivees = func.sum(mouvements.c.arrivee)

    requete = (
        select(
            Station.station_id,
            Station.nom,
            nb_departs.label("nb_departs"),
            nb_arrivees.label("nb_arrivees"),
        )
        .join(mouvements, mouvements.c.station_id == Station.station_id)
        .group_by(Station.station_id, Station.nom)
        .order_by((nb_departs + nb_arrivees).desc(), Station.station_id)
        .limit(limite)
    )

    donnees = []
    for ligne in session.execute(requete):
        donnees.append({
            "station_id": ligne.station_id,
            "nom": ligne.nom,
            "nb_departs": ligne.nb_departs,
            "nb_arrivees": ligne.nb_arrivees,
        })

    return {"donnees": donnees}


def incidents_par_statut(session: Session) -> dict:
    """Indicateur 3 : nombre d'incidents par statut et délai moyen de
    résolution en heures (arrondi à une décimale, None si aucun résolu)."""

    requete_statuts = (
        select(Incident.statut, func.count().label("nb_incidents"))
        .group_by(Incident.statut)
        .order_by(Incident.statut)
    )

    donnees = []
    for ligne in session.execute(requete_statuts):
        donnees.append({"statut": ligne.statut, "nb_incidents": ligne.nb_incidents})

    duree_heures = (
        extract("epoch", Incident.date_resolution - Incident.date_signalement) / 3600
    )

    requete_delai = select(func.round(func.avg(duree_heures), 1)).where(
        Incident.statut == "resolu",
        Incident.date_resolution.is_not(None),
    )

    delai = session.scalar(requete_delai)

    if delai is not None:
        delai = float(delai)

    return {"donnees": donnees, "delai_moyen_resolution_heures": delai}
