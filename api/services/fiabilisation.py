"""Règles de fiabilisation des données (module métier testé).

Fonctions pures : aucune ne lit ni n'écrit dans la base. Chacune retourne
la valeur normalisée, accompagnée d'un avertissement si elle a dû être
corrigée, ou lève Rejet avec le motif lorsque la valeur est inacceptable.
"""

import re
from dataclasses import dataclass
from datetime import datetime


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
