"""DataFrance Explorer — application Streamlit."""

from __future__ import annotations

import api_client as api
import streamlit as st
from components.header import (
    render_footer,
    render_header,
    render_sidebar_brand,
    render_sidebar_status,
)
from styles import inject_css
from views import about, dashboard, explore, organizations, visualize

st.set_page_config(
    page_title="DataFrance Explorer",
    page_icon="🇫🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

PAGES = {
    "Tableau de bord": dashboard.render,
    "Explorer les données": explore.render,
    "Visualiser": visualize.render,
    "Organisations": organizations.render,
    "À propos": about.render,
}

# Applique une demande de navigation avant de (re)creer le widget radio.
pending_page = st.session_state.pop("pending_page", None)
if pending_page in PAGES:
    st.session_state["nav"] = pending_page
if st.session_state.get("nav") not in PAGES:
    st.session_state["nav"] = "Tableau de bord"

with st.sidebar:
    render_sidebar_brand()
    page = st.radio(
        "Navigation",
        list(PAGES),
        key="nav",
        label_visibility="collapsed",
    )
    st.markdown("---")

    status = api.health()
    render_sidebar_status(
        ok=status.get("status") == "ok",
        detail=str(status.get("detail", "")),
    )
    st.caption(f"Backend : {api.API_URL}")

    if st.button("Rafraîchir les données", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("Prototype open source · données data.gouv.fr")

render_header()
PAGES[page]()
render_footer()
