"""Fonctions communes aux écrans : barre latérale et contrôle de connexion."""

import streamlit as st


def show_sidebar():
    """Affiche l'utilisateur connecté, son rôle et le bouton de déconnexion."""

    if "access_token" not in st.session_state:
        return

    st.sidebar.write(f"Connecté : {st.session_state['username']}")
    st.sidebar.write(f"Rôle : {st.session_state['role']}")

    if st.sidebar.button("Se déconnecter"):
        # On oublie le jeton, le rôle et l'identifiant.
        st.session_state.clear()
        st.switch_page("app.py")


def require_login():
    """Retourne le jeton de l'utilisateur connecté.

    Sans jeton, affiche « Veuillez vous connecter » et arrête la page :
    l'API n'est pas appelée.
    """

    if "access_token" not in st.session_state:
        st.warning("Veuillez vous connecter.")
        st.page_link("app.py", label="Aller à la page de connexion")
        st.stop()

    show_sidebar()

    return st.session_state["access_token"]
