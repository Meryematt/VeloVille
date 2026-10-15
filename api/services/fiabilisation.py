"""Règles de fiabilisation des données (module métier testé).

Fonctions pures : aucune ne lit ni n'écrit dans la base. Chacune retourne
la valeur normalisée, accompagnée d'un avertissement si elle a dû être
corrigée, ou lève Rejet avec le motif lorsque la valeur est inacceptable.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Avertissement:
    """Valeur corrigée sans ambiguïté : la ligne est tout de même importée."""

    colonne: str
    valeur: str
    motif: str


class Rejet(Exception):
    """Valeur qui viole une règle de gestion : la ligne est écartée."""

    def __init__(self, colonne: str, valeur: str, motif: str):
        super().__init__(motif)
        self.colonne = colonne
        self.valeur = valeur
        self.motif = motif



# Horodatages

# Formats attendus par le dictionnaire des données : aucun avertissement.
FORMATS_ATTENDUS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")

# Format français rencontré dans les exports : converti avec avertissement.
FORMAT_FRANCAIS = "%d/%m/%Y %H:%M"


def normaliser_horodatage(
    colonne: str,
    valeur: str,
) -> tuple[datetime, Avertissement | None]:
    """Convertit un horodatage texte en datetime."""

    texte = valeur.strip()

    for format_attendu in FORMATS_ATTENDUS:
        try:
            return datetime.strptime(texte, format_attendu), None
        except ValueError:
            pass

    try:
        horodatage = datetime.strptime(texte, FORMAT_FRANCAIS)
    except ValueError:
        raise Rejet(colonne, valeur, "Horodatage absent ou illisible")

    return horodatage, Avertissement(
        colonne,
        valeur,
        "Format JJ/MM/AAAA converti en AAAA-MM-JJ",
    )



# Identifiant de vélo

MOTIF_VELO_ID = re.compile(r"V\d{4}")


def normaliser_velo_id(valeur: str) -> tuple[str, Avertissement | None]:
    """Met l'identifiant de vélo au format V + 4 chiffres."""

    velo_id = valeur.strip().upper()

    if not MOTIF_VELO_ID.fullmatch(velo_id):
        raise Rejet(
            "velo_id",
            valeur,
            "Identifiant de vélo invalide (attendu V + 4 chiffres)",
        )

    if velo_id != valeur:
        return velo_id, Avertissement(
            "velo_id",
            valeur,
            f"Identifiant de vélo normalisé en {velo_id}",
        )

    return velo_id, None



# Statut d'incident

STATUTS = ("ouvert", "en_cours", "resolu")


def normaliser_statut(valeur: str) -> tuple[str, Avertissement | None]:
    """Ramène un statut saisi librement à l'une des trois valeurs (RG7)."""

    statut = valeur.strip().lower().replace(" ", "_")

    if statut not in STATUTS:
        raise Rejet("statut", valeur, "Statut inconnu (RG7)")

    if statut != valeur:
        return statut, Avertissement(
            "statut",
            valeur,
            f"Statut normalisé en {statut}",
        )

    return statut, None


# Durée d'un trajet

def verifier_duree(valeur: str) -> int:
    """Vérifie que la durée est un entier strictement positif (RG4)."""

    try:
        duree = int(valeur.strip())
    except ValueError:
        raise Rejet("duree_secondes", valeur, "Durée non entière (RG4)")

    if duree <= 0:
        raise Rejet("duree_secondes", valeur, "Durée nulle ou négative (RG4)")

    return duree


# Référence de station

def verifier_station(
    colonne: str,
    valeur: str,
    stations_connues: set[str],
    obligatoire: bool,
) -> str | None:
    """Vérifie qu'une station référencée existe dans le référentiel (RG2).

    Une station facultative absente est acceptée et vaut None (RG3).
    """

    station_id = valeur.strip()

    if not station_id:
        if obligatoire:
            raise Rejet(colonne, valeur, "Station obligatoire absente (RG2)")
        return None

    if station_id not in stations_connues:
        raise Rejet(colonne, valeur, "Station inconnue du référentiel (RG2)")

    return station_id


# Type d'usager et pseudonyme

TYPES_USAGER = ("abonne", "occasionnel")


def verifier_usager(
    type_usager: str,
    usager_ref: str,
) -> tuple[str, str | None]:
    """Vérifie la cohérence entre type d'usager et pseudonyme (RG5)."""

    type_usager_propre = type_usager.strip()
    usager_ref_propre = usager_ref.strip() or None

    if type_usager_propre not in TYPES_USAGER:
        raise Rejet("type_usager", type_usager, "Type d'usager inconnu")

    if type_usager_propre == "abonne" and usager_ref_propre is None:
        raise Rejet("usager_ref", usager_ref, "Abonné sans pseudonyme (RG5)")

    if type_usager_propre == "occasionnel" and usager_ref_propre is not None:
        raise Rejet(
            "usager_ref",
            usager_ref,
            "Usager occasionnel avec pseudonyme (RG5)",
        )

    return type_usager_propre, usager_ref_propre


# Doublons

def separer_doublons(
    lignes: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Sépare les lignes uniques des lignes strictement identiques.

    La première occurrence est conservée ; les suivantes sont des doublons.
    """

    deja_vues = set()
    uniques = []
    doublons = []

    for ligne in lignes:
        empreinte = tuple(ligne.items())

        if empreinte in deja_vues:
            doublons.append(ligne)
        else:
            deja_vues.add(empreinte)
            uniques.append(ligne)

    return uniques, doublons


# Cible d'un incident

CIBLES = ("velo", "station")


def verifier_cible(
    cible: str,
    velo_id: str | None,
    station_id: str | None,
) -> str:
    """Vérifie qu'un incident vise soit un vélo, soit une station (RG6).

    velo_id et station_id sont déjà nettoyés : None signifie absent.
    """

    cible_propre = cible.strip()

    if cible_propre not in CIBLES:
        raise Rejet("cible", cible, "Cible inconnue (RG6)")

    if cible_propre == "velo" and (velo_id is None or station_id is not None):
        raise Rejet(
            "cible",
            cible,
            "Un incident sur un vélo doit porter un vélo et aucune station (RG6)",
        )

    if cible_propre == "station" and (station_id is None or velo_id is not None):
        raise Rejet(
            "cible",
            cible,
            "Un incident sur une station doit porter une station et aucun vélo (RG6)",
        )

    return cible_propre


# Date de résolution d'un incident

def verifier_resolution(
    statut: str,
    date_signalement: datetime,
    date_resolution: datetime | None,
) -> None:
    """Vérifie la cohérence entre statut et date de résolution (RG8).

    La date de résolution est présente si et seulement si l'incident est
    résolu, et elle n'est pas antérieure à la date de signalement.
    """

    if statut == "resolu" and date_resolution is None:
        raise Rejet("date_resolution", "", "Incident résolu sans date de résolution (RG8)")

    if statut != "resolu" and date_resolution is not None:
        raise Rejet(
            "date_resolution",
            str(date_resolution),
            "Date de résolution sur un incident non résolu (RG8)",
        )

    if date_resolution is not None and date_resolution < date_signalement:
        raise Rejet(
            "date_resolution",
            str(date_resolution),
            "Date de résolution antérieure au signalement (RG8)",
        )


# Technicien

def signaler_technicien_absent(
    statut: str,
    technicien: str,
) -> Avertissement | None:
    """Signale un incident pris en charge sans technicien (RG8).

    L'absence n'empêche pas l'import : c'est un simple avertissement.
    """

    if statut in ("en_cours", "resolu") and not technicien.strip():
        return Avertissement(
            "technicien",
            technicien,
            "Technicien absent alors que l'incident est pris en charge (RG8)",
        )

    return None


# Valeurs génériques

def verifier_obligatoire(colonne: str, valeur: str) -> str:
    """Vérifie qu'une valeur obligatoire est renseignée."""

    texte = valeur.strip()

    if not texte:
        raise Rejet(colonne, valeur, "Valeur obligatoire absente")

    return texte


def verifier_identifiant_unique(
    colonne: str,
    valeur: str,
    deja_importes: set[str],
) -> str:
    """Vérifie qu'un identifiant n'a pas déjà été retenu dans le fichier.

    Une ligne de même identifiant mais de contenu différent n'est pas un
    doublon strict : on garde la première et on rejette les suivantes.
    """

    identifiant = verifier_obligatoire(colonne, valeur)

    if identifiant in deja_importes:
        raise Rejet(colonne, valeur, "Identifiant déjà présent avec un autre contenu")

    return identifiant


def convertir_decimal(colonne: str, valeur: str) -> Decimal | None:
    """Convertit un nombre décimal facultatif ; vide donne None."""

    texte = valeur.strip()

    if not texte:
        return None

    try:
        return Decimal(texte)
    except InvalidOperation:
        raise Rejet(colonne, valeur, "Nombre décimal illisible")


def convertir_date(colonne: str, valeur: str) -> date | None:
    """Convertit une date AAAA-MM-JJ facultative ; vide donne None."""

    texte = valeur.strip()

    if not texte:
        return None

    try:
        return date.fromisoformat(texte)
    except ValueError:
        raise Rejet(colonne, valeur, "Date illisible (attendu AAAA-MM-JJ)")


# Capacité d'une station

def verifier_capacite(valeur: str) -> int:
    """Vérifie que la capacité est un entier strictement positif (RG1)."""

    try:
        capacite = int(valeur.strip())
    except ValueError:
        raise Rejet("capacite", valeur, "Capacité non entière (RG1)")

    if capacite <= 0:
        raise Rejet("capacite", valeur, "Capacité nulle ou négative (RG1)")

    return capacite


# Fiabilisation d'une ligne complète
#
# Chaque fonction reçoit une ligne du CSV (dictionnaire colonne -> texte),
# applique les règles ci-dessus dans l'ordre des colonnes et retourne :
#   - la ligne nettoyée, prête à être insérée en base ;
#   - la liste des avertissements produits.
# Au premier Rejet, la ligne est abandonnée.

def fiabiliser_station(
    ligne: dict[str, str],
    deja_importees: set[str],
) -> tuple[dict, list[Avertissement]]:
    """Contrôle une ligne de stations.csv."""

    station = {
        "station_id": verifier_identifiant_unique(
            "station_id", ligne["station_id"], deja_importees
        ),
        "nom": verifier_obligatoire("nom", ligne["nom"]),
        "commune": verifier_obligatoire("commune", ligne["commune"]),
        "capacite": verifier_capacite(ligne["capacite"]),
        "latitude": convertir_decimal("latitude", ligne["latitude"]),
        "longitude": convertir_decimal("longitude", ligne["longitude"]),
        "date_mise_en_service": convertir_date(
            "date_mise_en_service", ligne["date_mise_en_service"]
        ),
    }

    # Le référentiel des stations ne comporte aucune normalisation.
    return station, []


def fiabiliser_trajet(
    ligne: dict[str, str],
    stations_connues: set[str],
    deja_importes: set[str],
) -> tuple[dict, list[Avertissement]]:
    """Contrôle une ligne de trajets.csv."""

    avertissements = []

    trajet_id = verifier_identifiant_unique(
        "trajet_id", ligne["trajet_id"], deja_importes
    )

    velo_id, avertissement = normaliser_velo_id(ligne["velo_id"])
    if avertissement:
        avertissements.append(avertissement)

    depart_horodatage, avertissement = normaliser_horodatage(
        "depart_horodatage", ligne["depart_horodatage"]
    )
    if avertissement:
        avertissements.append(avertissement)

    station_depart = verifier_station(
        "station_depart", ligne["station_depart"], stations_connues, True
    )
    station_arrivee = verifier_station(
        "station_arrivee", ligne["station_arrivee"], stations_connues, False
    )
    duree_secondes = verifier_duree(ligne["duree_secondes"])
    type_usager, usager_ref = verifier_usager(
        ligne["type_usager"], ligne["usager_ref"]
    )

    trajet = {
        "trajet_id": trajet_id,
        "velo_id": velo_id,
        "depart_horodatage": depart_horodatage,
        "station_depart": station_depart,
        "station_arrivee": station_arrivee,
        "duree_secondes": duree_secondes,
        "type_usager": type_usager,
        "usager_ref": usager_ref,
    }

    return trajet, avertissements


def fiabiliser_incident(
    ligne: dict[str, str],
    stations_connues: set[str],
    deja_importes: set[str],
) -> tuple[dict, list[Avertissement]]:
    """Contrôle une ligne de incidents.csv."""

    avertissements = []

    incident_id = verifier_identifiant_unique(
        "incident_id", ligne["incident_id"], deja_importes
    )

    date_signalement, avertissement = normaliser_horodatage(
        "date_signalement", ligne["date_signalement"]
    )
    if avertissement:
        avertissements.append(avertissement)

    # Le vélo est facultatif : il n'est normalisé que s'il est renseigné.
    velo_id = None
    if ligne["velo_id"].strip():
        velo_id, avertissement = normaliser_velo_id(ligne["velo_id"])
        if avertissement:
            avertissements.append(avertissement)

    station_id = verifier_station(
        "station_id", ligne["station_id"], stations_connues, False
    )
    cible = verifier_cible(ligne["cible"], velo_id, station_id)
    type_incident = verifier_obligatoire("type_incident", ligne["type_incident"])

    statut, avertissement = normaliser_statut(ligne["statut"])
    if avertissement:
        avertissements.append(avertissement)

    # La date de résolution est facultative : vide donne None.
    date_resolution = None
    if ligne["date_resolution"].strip():
        date_resolution, avertissement = normaliser_horodatage(
            "date_resolution", ligne["date_resolution"]
        )
        if avertissement:
            avertissements.append(avertissement)

    verifier_resolution(statut, date_signalement, date_resolution)

    avertissement = signaler_technicien_absent(statut, ligne["technicien"])
    if avertissement:
        avertissements.append(avertissement)

    incident = {
        "incident_id": incident_id,
        "date_signalement": date_signalement,
        "cible": cible,
        "velo_id": velo_id,
        "station_id": station_id,
        "type_incident": type_incident,
        "statut": statut,
        "date_resolution": date_resolution,
        "technicien": ligne["technicien"].strip() or None,
    }

    return incident, avertissements


# Journal de l'import

def journal_line(fichier, identifiant, colonne, valeur, motif, decision) -> list[str]:
    """Prépare une ligne du journal de l'import.

    Une information vide est écrite « (vide) » : chaque ligne porte ainsi
    les six informations demandées (correction de l'anomalie ANO-001).
    """

    ligne = []
    for information in (fichier, identifiant, colonne, valeur, motif, decision):
        if information:
            ligne.append(information)
        else:
            ligne.append("(vide)")

    return ligne
