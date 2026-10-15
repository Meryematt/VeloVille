"""Client HTTP centralisé vers l'API VéloVille.

Toutes les pages du front passent par ce fichier : elles n'appellent
jamais requests directement.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

# 127.0.0.1 et non localhost : sous Windows, localhost ajoute environ
# 2 secondes à chaque appel (anomalie ANO-002).
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_TIMEOUT_SECONDES = float(os.getenv("API_TIMEOUT_SECONDES", "5"))

# Message affiché pour chaque code HTTP d'erreur.
# Les pages peuvent afficher un message plus précis à partir du code.
MESSAGES_ERREUR = {
    401: "Votre session a expiré. Veuillez vous reconnecter.",
    403: "Vous n'avez pas le droit d'effectuer cette action.",
    404: "Élément introuvable.",
    422: "La demande est invalide.",
}


class ErreurApi(Exception):
    """Erreur levée lorsque l'API est injoignable ou répond en erreur."""

    def __init__(self, message: str, code_http: int | None = None):
        super().__init__(message)
        self.message = message
        self.code_http = code_http


def call_api(method, path, token=None, params=None, json=None):
    """Appelle l'API et retourne la réponse JSON, ou lève ErreurApi."""

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(
            method,
            API_URL + path,
            headers=headers,
            params=params,
            json=json,
            timeout=API_TIMEOUT_SECONDES,
        )
    except requests.exceptions.Timeout:
        raise ErreurApi("L'API met trop de temps à répondre. Réessayez plus tard.")
    except requests.exceptions.ConnectionError:
        raise ErreurApi("L'API est injoignable. Vérifiez qu'elle est démarrée.")

    if response.status_code >= 400:
        message = MESSAGES_ERREUR.get(
            response.status_code,
            "L'API a répondu par une erreur. Réessayez plus tard.",
        )
        raise ErreurApi(message, response.status_code)

    return response.json()


# Une fonction par route utilisée par le front.

def login(username, password):
    return call_api("POST", "/auth/login", json={"username": username, "password": password})


def get_stations(token, commune, page, taille_page):
    params = {"commune": commune, "page": page, "taille_page": taille_page}
    return call_api("GET", "/stations", token, params=params)


def get_incidents(token, statut, page, taille_page):
    params = {"statut": statut, "page": page, "taille_page": taille_page}
    return call_api("GET", "/incidents", token, params=params)


def change_incident_status(token, incident_id, statut):
    return call_api("PUT", f"/incidents/{incident_id}/statut", token, json={"statut": statut})


def get_daily_activity(token, date_debut, date_fin):
    params = {"date_debut": date_debut, "date_fin": date_fin}
    return call_api("GET", "/indicateurs/activite-par-jour", token, params=params)


def get_active_stations(token, limite):
    return call_api("GET", "/indicateurs/stations-actives", token, params={"limite": limite})


def get_incidents_by_status(token):
    return call_api("GET", "/indicateurs/incidents-par-statut", token)
