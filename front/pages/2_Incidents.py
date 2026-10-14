"""Écran Incidents : tableau filtrable par statut et, pour l'exploitant,
changement de statut d'un incident."""

import math

import pandas as pd
import streamlit as st

from api_client import ErreurApi, change_incident_status, get_incidents
from session import require_login

st.set_page_config(page_title="Incidents - VéloVille", layout="wide")

st.title("Incidents")

jeton = require_login()

# Filtres
col1, col2, col3 = st.columns(3)
statut = col1.selectbox("Statut", ["Tous", "ouvert", "en_cours", "resolu"])
taille_page = col2.selectbox("Taille de page", [10, 20, 50], index=1)
page = col3.number_input("Page", min_value=1, value=1, step=1)

statut_filtre = None if statut == "Tous" else statut

# Appel de l'API
try:
    with st.spinner("Chargement..."):
        donnees = get_incidents(jeton, statut_filtre, page, taille_page)
except ErreurApi as erreur:
    st.error(erreur.message)
    st.stop()

st.write(f"{donnees['total']} incidents au total")

# Tableau
if not donnees["resultats"]:
    st.info("Aucun résultat pour ces critères.")
else:
    tableau = pd.DataFrame(donnees["resultats"])

    # « 2026-08-30T18:00:00 » devient « 2026-08-30 18:00 ».
    for colonne in ["date_signalement", "date_resolution"]:
        tableau[colonne] = tableau[colonne].str.replace("T", " ").str[:16]

    tableau = tableau[[
        "incident_id", "date_signalement", "cible", "velo_id", "station_id",
        "type_incident", "statut", "date_resolution", "technicien",
    ]]
    # Les valeurs absentes (vélo d'un incident sur une station...) restent vides.
    tableau = tableau.fillna("")
    tableau = tableau.rename(columns={
        "incident_id": "Identifiant",
        "date_signalement": "Signalé le",
        "cible": "Cible",
        "velo_id": "Vélo",
        "station_id": "Station",
        "type_incident": "Type",
        "statut": "Statut",
        "date_resolution": "Résolu le",
        "technicien": "Technicien",
    })
    st.dataframe(tableau, hide_index=True, width="stretch")

nb_pages = max(1, math.ceil(donnees["total"] / taille_page))
st.caption(f"Page {page} sur {nb_pages}")

# Changement de statut
st.subheader("Changer le statut d'un incident")

if st.session_state["role"] != "exploitant":
    # Le front n'appelle pas le PUT pour la direction.
    st.info("La modification des incidents est réservée aux exploitants.")

elif donnees["resultats"]:
    # Message de la dernière modification, conservé après le rechargement.
    if "message_incident" in st.session_state:
        st.success(st.session_state.pop("message_incident"))

    identifiants = [incident["incident_id"] for incident in donnees["resultats"]]

    with st.form("changement_statut"):
        incident_id = st.selectbox("Incident", identifiants)
        nouveau_statut = st.selectbox("Nouveau statut", ["en_cours", "resolu"])
        appliquer = st.form_submit_button("Appliquer")

    if appliquer:
        try:
            change_incident_status(jeton, incident_id, nouveau_statut)
        except ErreurApi as erreur:
            if erreur.code_http == 422:
                st.error("Transition de statut non autorisée.")
            elif erreur.code_http == 404:
                st.error("Incident introuvable.")
            elif erreur.code_http == 403:
                st.error("Vous n'avez pas le droit de modifier un incident.")
            else:
                st.error(erreur.message)
        else:
            st.session_state["message_incident"] = (
                f"Statut de l'incident {incident_id} mis à jour : {nouveau_statut}."
            )
            st.rerun()
