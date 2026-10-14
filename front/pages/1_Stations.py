"""Écran Stations : tableau filtrable par commune, avec pagination."""

import math

import pandas as pd
import streamlit as st

from api_client import ErreurApi, get_stations
from session import require_login

st.set_page_config(page_title="Stations - VéloVille", layout="wide")

st.title("Stations")

jeton = require_login()


# Les communes changent rarement : on les garde en cache une heure pour ne pas rappeler l'API à chaque interaction (écoconception).
@st.cache_data(ttl=3600)
def load_communes(jeton):
    """Retourne la liste triée des communes, lue page par page dans l'API."""

    communes = set()
    page = 1

    while True:
        donnees = get_stations(jeton, None, page, 100)
        for station in donnees["resultats"]:
            communes.add(station["commune"])
        if page * 100 >= donnees["total"]:
            break
        page += 1

    return sorted(communes)


try:
    communes = load_communes(jeton)
except ErreurApi as erreur:
    st.error(erreur.message)
    st.stop()

# Filtres
col1, col2, col3 = st.columns(3)
commune = col1.selectbox("Commune", ["Toutes"] + communes)
taille_page = col2.selectbox("Taille de page", [10, 20, 50], index=1)
page = col3.number_input("Page", min_value=1, value=1, step=1)

commune_filtre = None if commune == "Toutes" else commune

# Appel de l'API
try:
    with st.spinner("Chargement..."):
        donnees = get_stations(jeton, commune_filtre, page, taille_page)
except ErreurApi as erreur:
    st.error(erreur.message)
    st.stop()

st.write(f"{donnees['total']} stations au total")

# Tableau
if not donnees["resultats"]:
    st.info("Aucun résultat pour ces critères.")
else:
    tableau = pd.DataFrame(donnees["resultats"])
    tableau = tableau[["station_id", "nom", "commune", "capacite", "date_mise_en_service"]]
    tableau = tableau.rename(columns={
        "station_id": "Identifiant",
        "nom": "Nom",
        "commune": "Commune",
        "capacite": "Capacité",
        "date_mise_en_service": "Mise en service",
    })
    st.dataframe(tableau, hide_index=True, width="stretch")

nb_pages = max(1, math.ceil(donnees["total"] / taille_page))
st.caption(f"Page {page} sur {nb_pages}")
