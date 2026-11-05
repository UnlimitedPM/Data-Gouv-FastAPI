"""Page « Visualiser » : apercu, graphiques automatiques et profil d'un jeu de donnees."""

from __future__ import annotations

from typing import Any

import api_client as api
import pandas as pd
import streamlit as st
from components.cards import (
    dataset_banner_html,
    empty_state,
    render_dataset_card,
    resource_label,
)
from components.charts import (
    auto_figures,
    build_custom_figure,
    categorical_columns,
    correlation_heatmap,
    numeric_columns,
)
from components.formatting import (
    format_date,
    frequency_label,
    human_number,
    human_size,
    license_label,
)


def _frame_from_preview(payload: dict[str, Any]) -> pd.DataFrame:
    columns = [column.get("name", "") for column in payload.get("columns") or []]
    rows = payload.get("rows") or []
    return pd.DataFrame(rows, columns=columns)


def _render_empty_state() -> None:
    st.info(
        "Choisissez un jeu de données dans « Explorer » ou saisissez son identifiant "
        "ci-dessus. Vous pouvez aussi partir d'une publication récente :"
    )
    try:
        overview = api.get_overview()
        latest = overview.get("latest_datasets") or []
    except api.ApiError as exc:
        st.error(str(exc))
        return

    if not latest:
        empty_state("Aucun jeu de données récent à proposer.")
        return

    left, right = st.columns(2)
    for index, dataset in enumerate(latest[:6]):
        with (left if index % 2 == 0 else right):
            render_dataset_card(
                dataset,
                key=f"visualize-latest-{dataset.get('id')}",
                button_label="Analyser →",
                target_page="Visualiser",
            )


def _render_preview_tab(frame: pd.DataFrame, payload: dict[str, Any], dataset_id: str) -> None:
    source = str(payload.get("source", "") or "")
    source_label = "Parquet" if source.startswith("parquet") else "Fichier"
    info = st.columns(4)
    info[0].metric("Lignes affichées", human_number(payload.get("rows_loaded")))
    info[1].metric("Colonnes", human_number(len(frame.columns)))
    info[2].metric("Source", source_label, help=source)
    info[3].metric("Tronqué", "Oui" if payload.get("truncated") else "Non")

    for warning in payload.get("warnings") or []:
        st.warning(warning)

    st.dataframe(frame, width="stretch", height=420)

    csv_bytes = frame.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Télécharger cet aperçu (CSV)",
        data=csv_bytes,
        file_name=f"{dataset_id}-apercu.csv",
        mime="text/csv",
    )


def _render_charts_tab(frame: pd.DataFrame) -> None:
    figures = auto_figures(frame)
    if not figures:
        st.info(
            "Aucun graphique automatique pertinent : le fichier ne contient pas assez "
            "de colonnes numériques, dates ou catégorielles."
        )
    else:
        for index in range(0, len(figures), 2):
            columns = st.columns(2)
            for offset in range(2):
                if index + offset < len(figures):
                    with columns[offset]:
                        st.plotly_chart(figures[index + offset], width="stretch")

    st.markdown("#### Graphique personnalisé")
    kinds = [
        "Histogramme",
        "Barres (comptage)",
        "Barres",
        "Ligne",
        "Nuage de points",
        "Boîte à moustaches",
    ]
    controls = st.columns(4)
    kind = controls[0].selectbox("Type", kinds, key="custom_kind")
    all_columns = [str(column) for column in frame.columns]
    x_column = controls[1].selectbox("Axe X / catégorie", all_columns, key="custom_x")

    numeric = numeric_columns(frame)
    needs_y = kind in {"Barres", "Ligne", "Nuage de points", "Boîte à moustaches"}
    y_column = None
    if needs_y:
        if not numeric:
            st.warning("Ce type de graphique nécessite au moins une colonne numérique.")
            return
        y_column = controls[2].selectbox("Axe Y (numérique)", numeric, key="custom_y")

    color = None
    if kind in {"Nuage de points", "Ligne", "Boîte à moustaches"}:
        groups = ["Aucun"] + categorical_columns(frame)
        choice = controls[3].selectbox("Couleur / groupe", groups, key="custom_color")
        color = None if choice == "Aucun" else choice

    figure = build_custom_figure(frame, kind, x_column, y_column, color)
    if figure is not None:
        st.plotly_chart(figure, width="stretch")


def _render_correlation_tab(frame: pd.DataFrame) -> None:
    numeric = numeric_columns(frame)
    if len(numeric) < 2:
        st.info("Il faut au moins deux colonnes numériques pour calculer des corrélations.")
        return
    if len(frame) < 3:
        st.info(
            "Le fichier ne contient que quelques lignes : les corrélations ne seraient "
            "pas significatives. Chargez davantage de lignes ou choisissez un autre fichier."
        )
        return

    selected = numeric[:15]
    numeric_frame = frame[selected].apply(pd.to_numeric, errors="coerce")
    matrix = numeric_frame.corr()
    values = [
        [None if pd.isna(value) else round(float(value), 3) for value in row]
        for row in matrix.to_numpy()
    ]
    st.plotly_chart(correlation_heatmap(selected, values), width="stretch")

    st.markdown("#### Nuage de points")
    controls = st.columns(2)
    x_column = controls[0].selectbox("X", selected, key="corr_x")
    y_column = controls[1].selectbox("Y", selected, index=min(1, len(selected) - 1), key="corr_y")
    figure = build_custom_figure(frame, "Nuage de points", x_column, y_column)
    if figure is not None:
        st.plotly_chart(figure, width="stretch")

    st.caption(
        "La corrélation de Pearson mesure un lien linéaire entre deux variables, "
        "pas une causalité."
    )


def _display_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:,.4f}".replace(",", " ").replace(".", ",")
    return str(value)


def _render_profile_tab(dataset_id: str, resource_id: str) -> None:
    st.caption(
        "Le profil est calculé côté backend sur un échantillon large (20 000 lignes "
        "par défaut) : valeurs manquantes, unicité, statistiques et valeurs fréquentes."
    )
    if not st.checkbox("Calculer le profil statistique", key=f"profile-toggle-{resource_id}"):
        return

    try:
        with st.spinner("Calcul du profil…"):
            profile = api.get_profile(dataset_id, resource_id, 20_000)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    st.caption(
        f"Source : {profile.get('source')} · "
        f"{human_number(profile.get('rows_analyzed'))} lignes analysées."
    )
    for warning in profile.get("warnings") or []:
        st.warning(warning)

    rows = []
    for column in profile.get("columns") or []:
        stats = column.get("stats") or {}
        rows.append(
            {
                "Colonne": column.get("name"),
                "Type": column.get("kind"),
                "Non nulles": column.get("non_null"),
                "Manquantes %": column.get("missing_pct"),
                "Uniques": column.get("unique"),
                "Min": _display_value(stats.get("min")),
                "Moyenne": _display_value(stats.get("mean")),
                "Médiane": _display_value(stats.get("median")),
                "Max": _display_value(stats.get("max")),
            }
        )

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=360)

    with_values = [column for column in profile.get("columns") or [] if column.get("top_values")]
    if with_values:
        st.markdown("#### Valeurs les plus fréquentes")
        for column in with_values[:8]:
            with st.expander(f"{column['name']} · {column.get('unique')} valeurs uniques"):
                top = pd.DataFrame(column["top_values"])
                top["value"] = top["value"].astype(str)
                st.dataframe(
                    top.rename(
                        columns={"value": "Valeur", "count": "Occurrences", "pct": "%"}
                    ),
                    width="stretch",
                    hide_index=True,
                )


def _render_metadata_tab(dataset: dict[str, Any]) -> None:
    details = [
        ("Identifiant", dataset.get("id")),
        ("Slug", dataset.get("slug")),
        ("Licence", license_label(dataset.get("license"))),
        ("Fréquence", frequency_label(dataset.get("frequency"))),
        ("Créé le", format_date(dataset.get("created_at"))),
        ("Dernière mise à jour", format_date(dataset.get("last_update"), with_time=True)),
        ("Couverture temporelle", f"{dataset.get('temporal_start') or '—'} → {dataset.get('temporal_end') or '—'}"),
        ("Granularité spatiale", dataset.get("spatial_granularity") or "—"),
        ("Zones", ", ".join(dataset.get("spatial_zones") or []) or "—"),
        ("Score de qualité", dataset.get("quality_score")),
        ("Type d'accès", dataset.get("access_type") or "—"),
    ]
    st.dataframe(
        pd.DataFrame(details, columns=["Champ", "Valeur"]),
        width="stretch",
        hide_index=True,
    )

    resources = dataset.get("resources") or []
    if resources:
        st.markdown("#### Fichiers disponibles")
        table = pd.DataFrame(
            [
                {
                    "Titre": resource.get("title") or resource.get("id"),
                    "Format": (resource.get("format") or "?").upper(),
                    "Taille": human_size(resource.get("filesize")),
                    "Type": resource.get("type") or "—",
                    "Lien": resource.get("url"),
                }
                for resource in resources
            ]
        )
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
            column_config={"Lien": st.column_config.LinkColumn("Lien")},
        )

    with st.expander("Métadonnées brutes (JSON)"):
        st.json(dataset)


def render() -> None:
    st.markdown("## Visualiser un jeu de données")
    st.caption(
        "Chargez un jeu de données, choisissez une ressource tabulaire : "
        "l'aperçu, les graphiques et le profil statistique sont générés automatiquement."
    )

    dataset_id = st.session_state.get("selected_dataset_id", "")
    row = st.columns([4, 1, 1])
    typed = row[0].text_input(
        "Identifiant ou slug du jeu de données",
        value=dataset_id,
        placeholder="ex : 6aec4a5e2f9ad56a51d37e7c",
    )
    if row[1].button("Charger", width="stretch") and typed.strip():
        st.session_state["selected_dataset_id"] = typed.strip()
        st.rerun()
    if row[2].button("Réinitialiser", width="stretch"):
        st.session_state.pop("selected_dataset_id", None)
        st.rerun()

    dataset_id = (st.session_state.get("selected_dataset_id") or "").strip()
    if not dataset_id:
        _render_empty_state()
        return

    try:
        with st.spinner("Chargement du jeu de données…"):
            dataset = api.get_dataset(dataset_id)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    st.markdown(dataset_banner_html(dataset), unsafe_allow_html=True)

    resources = dataset.get("resources") or []
    tabular = [resource for resource in resources if resource.get("is_tabular")]
    if not tabular:
        st.warning(
            "Ce jeu de données ne contient aucun fichier tabulaire "
            "(CSV, JSON, Excel, Parquet) exploitable par l'aperçu."
        )
        _render_metadata_tab(dataset)
        return

    options: dict[str, dict[str, Any]] = {}
    for index, resource in enumerate(tabular, start=1):
        label = f"{resource_label(resource)} — fichier {index}"
        options[label] = resource
    choice = st.selectbox("Fichier à analyser", list(options), key=f"resource-choice-{dataset_id}")
    resource = options[choice]
    resource_id = resource.get("id") or ""

    controls = st.columns([2, 2])
    limit = controls[0].slider(
        "Lignes à charger pour l'aperçu",
        min_value=100,
        max_value=5_000,
        value=500,
        step=100,
        key=f"preview-limit-{dataset_id}",
    )
    if resource.get("url") or resource.get("parquet_url"):
        controls[1].caption(
            f"Fichier : {resource.get('format', '?').upper()} · "
            f"{human_size(resource.get('filesize'))} · "
            f"{'lecture Parquet optimisée' if resource.get('parquet_url') else 'lecture directe'}"
        )

    try:
        with st.spinner("Lecture du fichier…"):
            preview = api.get_preview(dataset_id, resource_id, limit)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    frame = _frame_from_preview(preview)
    tabs = st.tabs(
        ["📋 Aperçu", "📊 Graphiques", "🔗 Corrélations", "🧮 Profil des colonnes", "ℹ️ Métadonnées"]
    )
    with tabs[0]:
        _render_preview_tab(frame, preview, dataset_id)
    with tabs[1]:
        _render_charts_tab(frame)
    with tabs[2]:
        _render_correlation_tab(frame)
    with tabs[3]:
        _render_profile_tab(dataset_id, resource_id)
    with tabs[4]:
        _render_metadata_tab(dataset)

    st.caption(
        "Astuce : les lignes chargées servent uniquement à l'exploration visuelle. "
        "Les statistiques du profil utilisent un échantillon plus large côté serveur."
    )
