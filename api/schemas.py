"""Schémas Pydantic utilisés par l'API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    """Corps de POST /auth/login."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Réponse de POST /auth/login."""

    access_token: str
    token_type: str = "bearer"
    role: str


class StationResponse(BaseModel):
    """Représentation d'une station retournée par l'API."""

    model_config = ConfigDict(from_attributes=True)

    station_id: str
    nom: str
    commune: str
    capacite: int
    # float plutôt que Decimal : le JSON affiche 50.59932 et non "50.59932".
    latitude: float | None
    longitude: float | None
    date_mise_en_service: date | None


class PaginatedStationsResponse(BaseModel):
    """Enveloppe paginée de stations (noms des champs imposés par le contrat)."""

    total: int
    page: int
    taille_page: int
    resultats: list[StationResponse]


class TrajetResponse(BaseModel):
    """Représentation d'un trajet retourné par l'API."""

    model_config = ConfigDict(from_attributes=True)

    trajet_id: str
    velo_id: str
    depart_horodatage: datetime
    station_depart: str
    station_arrivee: str | None
    duree_secondes: int
    type_usager: str
    usager_ref: str | None


class PaginatedTrajetsResponse(BaseModel):
    """Enveloppe paginée de trajets (noms des champs imposés par le contrat)."""

    total: int
    page: int
    taille_page: int
    resultats: list[TrajetResponse]


class IncidentResponse(BaseModel):
    """Représentation d'un incident retourné par l'API."""

    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    date_signalement: datetime
    cible: str
    velo_id: str | None
    station_id: str | None
    type_incident: str
    statut: str
    date_resolution: datetime | None
    technicien: str | None


class PaginatedIncidentsResponse(BaseModel):
    """Enveloppe paginée d'incidents (noms des champs imposés par le contrat)."""

    total: int
    page: int
    taille_page: int
    resultats: list[IncidentResponse]


class StatusUpdateRequest(BaseModel):
    """Corps de PUT /incidents/{incident_id}/statut."""

    statut: str


class DailyActivity(BaseModel):
    """Un jour de l'indicateur « activité par jour »."""

    jour: date
    nb_trajets: int


class DailyActivityResponse(BaseModel):
    """Réponse de GET /indicateurs/activite-par-jour."""

    donnees: list[DailyActivity]


class ActiveStation(BaseModel):
    """Une station de l'indicateur « stations actives »."""

    station_id: str
    nom: str
    nb_departs: int
    nb_arrivees: int


class ActiveStationsResponse(BaseModel):
    """Réponse de GET /indicateurs/stations-actives."""

    donnees: list[ActiveStation]


class StatusCount(BaseModel):
    """Un statut de l'indicateur « incidents par statut »."""

    statut: str
    nb_incidents: int


class IncidentsByStatusResponse(BaseModel):
    """Réponse de GET /indicateurs/incidents-par-statut."""

    donnees: list[StatusCount]
    # None (null en JSON) s'il n'y a aucun incident résolu.
    delai_moyen_resolution_heures: float | None
