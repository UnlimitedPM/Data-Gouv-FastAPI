"""DataFrance Explorer — application Streamlit."""

from __future__ import annotations

import api_client as api
import streamlit as st
import url_state
from components.header import (
    render_footer,
    render_header,
    render_sidebar_brand,
    render_sidebar_status,
)
from styles import inject_css
from views import about, compare, dashboard, explore, organizations, visualize

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
    "Comparer": compare.render,
    "Organisations": organizations.render,
    "À propos": about.render,
}

# Restaure une vue partagee par URL (dataset, fichier, filtres).
initial_view = url_state.read_view()
if initial_view["dataset"] and "selected_dataset_id" not in st.session_state:
    st.session_state["selected_dataset_id"] = initial_view["dataset"]
    st.session_state["pending_page"] = "Visualiser"
if initial_view["resource"]:
    st.session_state["url_resource"] = initial_view["resource"]
if initial_view["filters"]:
    st.session_state["url_filters"] = initial_view["filters"]

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
        detail=str(status.get("database_error") or status.get("detail", "")),
        catalog_empty=bool(status.get("catalog_empty")),
    )
    st.caption(f"Backend : {api.API_URL}")
    if status.get("catalog_empty"):
        st.caption("Base vide : lancez `python -m app.ingest` dans backend/.")

    # Documentation Swagger generee automatiquement par FastAPI (aucune page a
    # maintenir cote frontend).
    st.link_button(
        "Documentation de l'API",
        api.docs_url(),
        icon=":material/menu_book:",
        width="stretch",
        help="Interface Swagger generee par FastAPI (/docs) — endpoints et essais en direct.",
    )

    if st.button("Rafraîchir les données", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("Prototype open source · données data.gouv.fr")

render_header()
PAGES[page]()
render_footer()
