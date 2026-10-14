"""Écran Indicateurs : trois métriques et trois tableaux. Aucun graphique."""

from datetime import date

import pandas as pd
import streamlit as st

from api_client import (
    ErreurApi,
    get_active_stations,
    get_daily_activity,
    get_incidents_by_status,
)
from session import require_login

st.set_page_config(page_title="Indicateurs - VéloVille", layout="wide")

st.title("Indicateurs")

jeton = require_login()

# Paramètres : appliqués seulement au clic sur « Actualiser ».
with st.form("parametres"):
    col1, col2, col3 = st.columns(3)
    date_debut = col1.date_input("Du", value=date(2026, 8, 24))
    date_fin = col2.date_input("Au", value=date(2026, 8, 30))
    limite = col3.number_input("Stations", min_value=1, max_value=50, value=10, step=1)
    st.form_submit_button("Actualiser")

if date_debut > date_fin:
    st.error("La date de début doit être antérieure ou égale à la date de fin.")
    st.stop()

# Appels de l'API
try:
    with st.spinner("Chargement..."):
        activite = get_daily_activity(jeton, str(date_debut), str(date_fin))["donnees"]
        stations = get_active_stations(jeton, limite)["donnees"]
        reponse_incidents = get_incidents_by_status(jeton)
except ErreurApi as erreur:
    st.error(erreur.message)
    st.stop()

incidents = reponse_incidents["donnees"]
delai = reponse_incidents["delai_moyen_resolution_heures"]

# Métriques
nb_trajets = sum(jour["nb_trajets"] for jour in activite)

if delai is None:
    delai_affiche = "n. d."
else:
    delai_affiche = f"{delai:.1f}".replace(".", ",")

col1, col2, col3 = st.columns(3)
col1.metric("Trajets sur la période", f"{nb_trajets:,}".replace(",", " "))
col2.metric("Stations actives", len(stations))
col3.metric("Délai moyen de résolution (h)", delai_affiche)

# Tableau 1 : activité par jour
st.subheader("Activité par jour")

if not activite:
    st.info("Aucun résultat pour ces critères.")
else:
    tableau = pd.DataFrame(activite)
    tableau = tableau.rename(columns={"jour": "Jour", "nb_trajets": "Nombre de trajets"})
    st.dataframe(tableau, hide_index=True, width="stretch")

# Tableau 2 : stations les plus actives
st.subheader("Stations les plus actives")

if not stations:
    st.info("Aucun résultat pour ces critères.")
else:
    tableau = pd.DataFrame(stations)
    tableau["total"] = tableau["nb_departs"] + tableau["nb_arrivees"]
    tableau = tableau.rename(columns={
        "station_id": "Identifiant",
        "nom": "Nom",
        "nb_departs": "Départs",
        "nb_arrivees": "Arrivées",
        "total": "Total",
    })
    st.dataframe(tableau, hide_index=True, width="stretch")

# Tableau 3 : incidents par statut
st.subheader("Incidents par statut")

if not incidents:
    st.info("Aucun résultat pour ces critères.")
else:
    tableau = pd.DataFrame(incidents)
    tableau = tableau.rename(columns={"statut": "Statut", "nb_incidents": "Nombre d'incidents"})
    st.dataframe(tableau, hide_index=True, width="stretch")
