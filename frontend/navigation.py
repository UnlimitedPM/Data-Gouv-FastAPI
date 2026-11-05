"""Navigation differee entre pages Streamlit.

Streamlit interdit de modifier l'etat d'un widget apres sa creation. Les vues
deposent donc une intention dans ``pending_page`` ; ``app.py`` l'applique avant
de reconstruire la barre laterale.
"""

from __future__ import annotations

import streamlit as st


def go_to(page: str) -> None:
    """Demande le passage a une page puis relance le script."""
    st.session_state["pending_page"] = page
    st.rerun()
