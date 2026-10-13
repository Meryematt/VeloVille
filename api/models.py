"""Modèles SQLAlchemy : Station, Trajet, Incident, Utilisateur.

Les tables et leurs contraintes sont créées par sql/schema.sql ;
ces modèles en sont le reflet côté Python.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Station(Base):
    """Station du référentiel."""

    __tablename__ = "station"

    station_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    commune: Mapped[str] = mapped_column(String(50))
    capacite: Mapped[int]
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))
    date_mise_en_service: Mapped[date | None] = mapped_column(Date)


class Trajet(Base):
    """Location d'un vélo entre deux stations."""

    __tablename__ = "trajet"

    trajet_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    velo_id: Mapped[str] = mapped_column(String(8))
    depart_horodatage: Mapped[datetime] = mapped_column(DateTime)
    station_depart: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("station.station_id"),
    )
    station_arrivee: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey("station.station_id"),
    )
    duree_secondes: Mapped[int]
    type_usager: Mapped[str] = mapped_column(String(12))
    usager_ref: Mapped[str | None] = mapped_column(String(9))


class Incident(Base):
    """Signalement de maintenance visant un vélo ou une station."""

    __tablename__ = "incident"

    incident_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    date_signalement: Mapped[datetime] = mapped_column(DateTime)
    cible: Mapped[str] = mapped_column(String(10))
    velo_id: Mapped[str | None] = mapped_column(String(8))
    station_id: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey("station.station_id"),
    )
    type_incident: Mapped[str] = mapped_column(String(50))
    statut: Mapped[str] = mapped_column(String(10))
    date_resolution: Mapped[datetime | None] = mapped_column(DateTime)
    technicien: Mapped[str | None] = mapped_column(String(100))


class Utilisateur(Base):
    """Utilisateur pouvant s'authentifier."""

    __tablename__ = "utilisateur"

    id_utilisateur: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    mot_de_passe_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
