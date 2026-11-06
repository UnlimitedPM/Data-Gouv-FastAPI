"""Page « Tableau de bord » : chiffres cles et repartitions globales."""

from __future__ import annotations

from typing import Any

import api_client as api
import streamlit as st
from components.cards import kpi_grid, render_dataset_card
from components.charts import bar_facets, donut_facets
from components.formatting import human_number


def _relabel(items: list[dict[str, Any]], mapping: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {**item, "name": mapping.get(str(item.get("name", "")).lower(), item.get("name", ""))}
        for item in items
    ]


def _section(title: str, hint: str = "") -> None:
    st.markdown(
        f'<div class="dfe-section-title"><h2>{title}</h2>'
        f'{"<span>" + hint + "</span>" if hint else ""}</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    st.markdown("## Tableau de bord")
    st.caption(
        "Vue d'ensemble du catalogue data.gouv.fr ingéré localement "
        "(instantané en base : relancez l'ingestion pour actualiser)."
    )

    try:
        with st.spinner("Lecture du catalogue local…"):
            overview = api.get_overview()
    except api.ApiError as exc:
        st.error(str(exc))
        return

    totals = overview.get("totals") or {}
    kpi_grid(
        [
            {
                "value": human_number(totals.get("datasets")),
                "label": "jeux de données",
                "hint": "datasets publiés",
            },
            {
                "value": human_number(totals.get("organizations")),
                "label": "organisations",
                "hint": "producteurs référencés",
            },
            {
                "value": human_number(totals.get("reuses")),
                "label": "réutilisations",
                "hint": "applications & analyses",
            },
            {
                "value": human_number(totals.get("dataservices")),
                "label": "API & services",
                "hint": "services de données",
            },
        ]
    )

    facets = overview.get("facets") or {}

    _section("Panorama des données", "répartition par format, producteur et licence")

    left, right = st.columns(2)
    with left:
        figure = donut_facets(
            _relabel(facets.get("format_family") or [], {k.lower(): v for k, v in {
                "tabular": "Tableur",
                "geographical": "Géographique",
                "documents": "Documents",
                "machine_readable": "Lisible par machine",
                "other": "Autre",
            }.items()}),
            "Familles de formats",
            height=360,
        )
        if figure:
            st.plotly_chart(figure, width="stretch")
        else:
            st.info("Pas de données de formats disponibles.")

    with right:
        figure = bar_facets(
            _relabel(facets.get("producer_type") or [], {k.lower(): v for k, v in {
                "public-service": "Service public",
                "local-authority": "Collectivité",
                "company": "Entreprise",
                "user": "Utilisateur",
                "not-specified": "Non précisé",
            }.items()}),
            "Types de producteurs",
            color="#1212ff",
            height=360,
        )
        if figure:
            st.plotly_chart(figure, width="stretch")
        else:
            st.info("Pas de données de producteurs disponibles.")

    left, right = st.columns(2)
    with left:
        figure = bar_facets(
            facets.get("organization_id_with_name") or [],
            "Organisations les plus prolifiques",
            color="#6a6af4",
            limit=10,
            height=380,
        )
        if figure:
            st.plotly_chart(figure, width="stretch")
        else:
            st.info("Pas d'organisations disponibles.")

    with right:
        figure = donut_facets(
            _relabel(facets.get("license") or [], {k.lower(): v for k, v in {
                "lov2": "Licence Ouverte 2.0",
                "odbl": "ODbL",
                "cc-by": "CC BY",
                "cc-by-sa": "CC BY-SA",
                "cc-zero": "CC0",
                "notspecified": "Non précisée",
            }.items()}),
            "Licences déclarées",
            limit=6,
            height=380,
        )
        if figure:
            st.plotly_chart(figure, width="stretch")
        else:
            st.info("Pas de licences disponibles.")

    tags = [
        {**item, "name": str(item.get("name", "")).replace("-", " ")}
        for item in facets.get("tag") or []
    ]
    figure = bar_facets(
        tags,
        "Thèmes et mots-clés les plus fréquents",
        color="#009099",
        limit=12,
        height=380,
    )
    if figure:
        st.plotly_chart(figure, width="stretch")

    _section("Derniers jeux de données publiés", "cliquez sur « Analyser » pour les explorer")

    latest = overview.get("latest_datasets") or []
    if not latest:
        st.info("Aucun jeu de données récent renvoyé par l'API.")
        return

    left, right = st.columns(2)
    for index, dataset in enumerate(latest):
        with (left if index % 2 == 0 else right):
            render_dataset_card(dataset, key=f"latest-{dataset.get('id')}", button_label="Analyser →")
