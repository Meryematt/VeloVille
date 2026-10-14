"""Page d'accueil Streamlit : connexion."""

import streamlit as st

from api_client import ErreurApi, login
from session import show_sidebar

st.set_page_config(page_title="Connexion - VéloVille")

st.title("VéloVille - Plateforme de restitution")

if "access_token" in st.session_state:
    st.success(
        f"Connecté en tant que {st.session_state['username']} "
        f"(rôle : {st.session_state['role']})."
    )
    st.write("Utilisez le menu latéral pour accéder aux écrans.")
    show_sidebar()

else:
    st.header("Connexion")

    with st.form("connexion"):
        username = st.text_input("Identifiant")
        # type="password" : la saisie est masquée.
        password = st.text_input("Mot de passe", type="password")
        envoyer = st.form_submit_button("Se connecter")

    if envoyer:
        try:
            with st.spinner("Chargement..."):
                reponse = login(username, password)
        except ErreurApi as erreur:
            if erreur.code_http == 401:
                st.error("Identifiant ou mot de passe incorrect.")
            else:
                st.error(erreur.message)
        else:
            st.session_state["access_token"] = reponse["access_token"]
            st.session_state["role"] = reponse["role"]
            st.session_state["username"] = username
            st.rerun()
