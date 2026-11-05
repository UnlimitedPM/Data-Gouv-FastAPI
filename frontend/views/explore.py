"""Page « Explorer » : recherche filtree dans le catalogue data.gouv.fr."""

from __future__ import annotations

from typing import Any

import api_client as api
import streamlit as st
from components.cards import empty_state, render_dataset_card
from components.formatting import (
    family_label,
    human_number,
    license_label,
    producer_label,
)
from streamlit_searchbox import st_searchbox

SORT_OPTIONS: dict[str, str | None] = {
    "Pertinence": None,
    "Plus récents": "-created",
    "Mise à jour récente": "-last_update",
    "Plus consultés": "-views",
    "Plus suivis": "-followers",
}


def _facet_options(overview: dict[str, Any], key: str) -> list[str]:
    facets = overview.get("facets") or {}
    return [str(item.get("name")) for item in facets.get(key) or [] if item.get("name")]


def _load_facet_options() -> dict[str, list[str]]:
    try:
        overview = api.get_overview()
    except api.ApiError:
        return {"format_family": [], "producer_type": [], "license": []}
    return {
        "format_family": _facet_options(overview, "format_family"),
        "producer_type": _facet_options(overview, "producer_type"),
        "license": _facet_options(overview, "license"),
    }


def render() -> None:
    st.markdown("## Explorer les jeux de données")
    st.caption(
        "Recherchez parmi les dizaines de milliers de jeux de données publics, "
        "filtrez par format, producteur ou licence, puis lancez l'analyse."
    )

    options = _load_facet_options()

    with st.container(border=True):
        row1 = st.columns([2.4, 1.2, 1])
        with row1[0]:
            query = st_searchbox(
                api.suggest_datasets,
                label="Recherche en direct",
                placeholder="ex : transport, logement, énergie, communes…",
                default_use_searchterm=True,
                debounce=300,
                key="explore_searchbox",
            ) or ""
        sort_label = row1[1].selectbox("Trier par", list(SORT_OPTIONS), key="explore_sort")
        page_size = row1[2].selectbox("Par page", [12, 24, 48], index=1, key="explore_size")

        row2 = st.columns(3)
        family = row2[0].selectbox(
            "Famille de formats",
            ["Toutes"] + options["format_family"],
            format_func=lambda value: "Toutes" if value == "Toutes" else family_label(value),
            key="explore_family",
        )
        producer = row2[1].selectbox(
            "Type de producteur",
            ["Tous"] + options["producer_type"],
            format_func=lambda value: "Tous" if value == "Tous" else producer_label(value),
            key="explore_producer",
        )
        license_value = row2[2].selectbox(
            "Licence",
            ["Toutes"] + options["license"],
            format_func=lambda value: "Toutes" if value == "Toutes" else license_label(value),
            key="explore_license",
        )

    query = str(query).strip()
    if query and len(query) < 2:
        st.info("Tapez au moins deux caractères pour lancer la recherche.")
        return

    signature = (query, sort_label, page_size, family, producer, license_value)
    if st.session_state.get("explore_signature") != signature:
        st.session_state["explore_signature"] = signature
        st.session_state["explore_page"] = 1

    page = int(st.session_state.get("explore_page", 1))

    try:
        with st.spinner("Recherche en cours…"):
            result = api.search_datasets(
                q=query or None,
                page=page,
                page_size=page_size,
                sort=SORT_OPTIONS[sort_label],
                format_family=None if family == "Toutes" else family,
                producer_type=None if producer == "Tous" else producer,
                license=None if license_value == "Toutes" else license_value,
            )
    except api.ApiError as exc:
        st.error(str(exc))
        return

    total = int(result.get("total") or 0)
    pages = int(result.get("pages") or 1)
    datasets = result.get("data") or []
    total_label = human_number(total) + ("+" if result.get("total_capped") else "")

    st.markdown(
        f"**{total_label}** jeux de données trouvés · "
        f"page **{result.get('page', page)}** sur **{human_number(pages)}**"
    )
    if result.get("total_capped"):
        st.caption(
            "Le filtrage par famille de formats ou type de producteur utilise l'API v2, "
            "qui plafonne l'affichage à 10 000 résultats."
        )

    if not datasets:
        empty_state("Aucun jeu de données ne correspond à ces critères. Essayez d'élargir la recherche.")
        return

    left, right = st.columns(2)
    for index, dataset in enumerate(datasets):
        with (left if index % 2 == 0 else right):
            render_dataset_card(
                dataset,
                key=f"explore-{page}-{dataset.get('id')}",
                button_label="Analyser ce jeu de données →",
            )

    nav_left, nav_center, nav_right = st.columns([1, 3, 1])
    if nav_left.button("← Précédent", disabled=page <= 1, width="stretch"):
        st.session_state["explore_page"] = page - 1
        st.rerun()
    nav_center.markdown(
        f"<div style='text-align:center;color:#666;padding-top:6px'>"
        f"Page {page} / {pages}</div>",
        unsafe_allow_html=True,
    )
    if nav_right.button("Suivant →", disabled=page >= pages, width="stretch"):
        st.session_state["explore_page"] = page + 1
        st.rerun()
