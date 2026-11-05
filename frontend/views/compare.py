"""Page « Comparer » : rapprocher deux jeux de données."""

from __future__ import annotations

from typing import Any

import api_client as api
import pandas as pd
import plotly.express as px
import streamlit as st
from components.charts import (
    BLUE,
    PALETTE,
    apply_theme,
    categorical_columns,
    numeric_columns,
)
from components.formatting import (
    compact_html,
    esc,
    format_date,
    frequency_label,
    human_number,
    license_label,
)
from streamlit_searchbox import st_searchbox

COMPARE_SEPARATOR = "  ·  "


def _extract_id(value: Any) -> str:
    text = str(value or "").strip()
    if COMPARE_SEPARATOR in text:
        return text.rsplit(COMPARE_SEPARATOR, 1)[-1].strip()
    return text


def _display(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def _header_html(dataset: dict[str, Any], label: str) -> str:
    organization = dataset.get("organization") or {}
    metrics = dataset.get("metrics") or {}
    return compact_html(
        f"""
        <div class="dfe-card dfe-card--flat">
          <div class="dfe-card__top">
            <span class="dfe-pill dfe-pill--dark">{esc(label)}</span>
            <span class="dfe-card__date">{esc(relative_update(dataset))}</span>
          </div>
          <h3 class="dfe-card__title">{esc(dataset.get('title'))}</h3>
          <p class="dfe-card__meta">
            {esc(organization.get('name') or 'Producteur inconnu')} ·
            {esc(license_label(dataset.get('license')))}
          </p>
          <div class="dfe-metrics">
            <div>
              <div class="dfe-metric__value">{esc(human_number(dataset.get('resources_count')))}</div>
              <div class="dfe-metric__label">fichiers</div>
            </div>
            <div>
              <div class="dfe-metric__value">{esc(human_number(metrics.get('views')))}</div>
              <div class="dfe-metric__label">vues</div>
            </div>
            <div>
              <div class="dfe-metric__value">{esc(human_number(metrics.get('followers')))}</div>
              <div class="dfe-metric__label">suiveurs</div>
            </div>
            <div>
              <div class="dfe-metric__value">{esc(human_number(metrics.get('reuses')))}</div>
              <div class="dfe-metric__label">réutilisations</div>
            </div>
          </div>
        </div>
        """
    )


def relative_update(dataset: dict[str, Any]) -> str:
    updated = dataset.get("last_update") or dataset.get("last_modified")
    return f"Mis à jour {format_date(updated)}" if updated else "Date inconnue"


def _load_side(dataset_id: str) -> tuple[dict[str, Any], dict[str, Any] | None, pd.DataFrame | None]:
    dataset = api.get_dataset(dataset_id)
    tabular = [
        resource
        for resource in dataset.get("resources") or []
        if resource.get("is_tabular")
    ]
    if not tabular:
        return dataset, None, None

    main = [resource for resource in tabular if resource.get("type") == "main"]
    resource = (main or tabular)[0]
    preview = api.get_preview(dataset_id, resource.get("id"), 500)
    frame = pd.DataFrame(
        preview.get("rows") or [],
        columns=[column.get("name", "") for column in preview.get("columns") or []],
    )
    return dataset, resource, frame


def _metrics_table(
    left: dict[str, Any], right: dict[str, Any]
) -> pd.DataFrame:
    left_metrics = left.get("metrics") or {}
    right_metrics = right.get("metrics") or {}
    left_org = (left.get("organization") or {}).get("name")
    right_org = (right.get("organization") or {}).get("name")

    rows = [
        ("Organisation", _display(left_org), _display(right_org)),
        ("Licence", license_label(left.get("license")), license_label(right.get("license"))),
        ("Fréquence", frequency_label(left.get("frequency")), frequency_label(right.get("frequency"))),
        ("Nombre de fichiers", human_number(left.get("resources_count")), human_number(right.get("resources_count"))),
        ("Vues", human_number(left_metrics.get("views")), human_number(right_metrics.get("views"))),
        ("Suiveurs", human_number(left_metrics.get("followers")), human_number(right_metrics.get("followers"))),
        ("Réutilisations", human_number(left_metrics.get("reuses")), human_number(right_metrics.get("reuses"))),
        ("Dernière mise à jour", format_date(left.get("last_update") or left.get("last_modified")), format_date(right.get("last_update") or right.get("last_modified"))),
    ]
    return pd.DataFrame(rows, columns=["Critère", "A", "B"])


def _schema_table(
    left: pd.DataFrame, right: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for column in sorted(set(left.columns) | set(right.columns)):
        in_left = column in left.columns
        in_right = column in right.columns
        rows.append(
            {
                "Colonne": str(column),
                "A": "✓" if in_left else "",
                "B": "✓" if in_right else "",
                "Type A": str(left[column].dtype) if in_left else "—",
                "Type B": str(right[column].dtype) if in_right else "—",
                "Commune": "✓" if in_left and in_right else "",
            }
        )
    return pd.DataFrame(rows)


def _render_numeric_comparison(left: pd.DataFrame, right: pd.DataFrame) -> None:
    common = [
        column
        for column in numeric_columns(left)
        if column in right.columns and pd.api.types.is_numeric_dtype(right[column])
    ]
    if not common:
        st.info("Aucune colonne numérique commune aux deux jeux de données.")
        return

    column = st.selectbox("Colonne numérique commune", common, key="compare-numeric")
    long_frame = pd.concat(
        [
            pd.DataFrame(
                {
                    "Jeu de données": "A",
                    "Valeur": pd.to_numeric(left[column], errors="coerce"),
                }
            ),
            pd.DataFrame(
                {
                    "Jeu de données": "B",
                    "Valeur": pd.to_numeric(right[column], errors="coerce"),
                }
            ),
        ]
    ).dropna()

    figure = px.box(
        long_frame,
        x="Jeu de données",
        y="Valeur",
        color="Jeu de données",
        color_discrete_sequence=PALETTE,
        title=f"Distribution — {column}",
    )
    figure.update_layout(showlegend=False, xaxis_title=None, yaxis_title=column)
    st.plotly_chart(apply_theme(figure, 380), width="stretch")

    summary = pd.DataFrame(
        [
            {
                "Jeu de données": label,
                "Lignes": len(frame),
                "Moyenne": round(float(pd.to_numeric(frame[column], errors="coerce").mean()), 3),
                "Médiane": round(float(pd.to_numeric(frame[column], errors="coerce").median()), 3),
                "Min": round(float(pd.to_numeric(frame[column], errors="coerce").min()), 3),
                "Max": round(float(pd.to_numeric(frame[column], errors="coerce").max()), 3),
            }
            for label, frame in (("A", left), ("B", right))
        ]
    )
    st.dataframe(summary, hide_index=True, width="stretch")


def _render_categorical_comparison(left: pd.DataFrame, right: pd.DataFrame) -> None:
    numeric = set(numeric_columns(left)) | set(numeric_columns(right))
    common = [
        column
        for column in categorical_columns(left, max_cardinality=40)
        if column in right.columns and column not in numeric
    ]
    if not common:
        st.info("Aucune colonne catégorielle commune aux deux jeux de données.")
        return

    column = st.selectbox("Colonne catégorielle commune", common, key="compare-categorical")
    values = set()
    for frame in (left, right):
        values.update(frame[column].astype(str).value_counts().head(8).index.tolist())
    values = list(values)[:10]

    rows = []
    for label, frame in (("A", left), ("B", right)):
        counts = frame[column].astype(str).value_counts(normalize=True)
        for value in values:
            rows.append(
                {
                    "Valeur": value,
                    "Part (%)": round(float(counts.get(value, 0)) * 100, 2),
                    "Jeu de données": label,
                }
            )

    frame_plot = pd.DataFrame(rows)
    figure = px.bar(
        frame_plot,
        x="Valeur",
        y="Part (%)",
        color="Jeu de données",
        barmode="group",
        title=f"Répartition — {column}",
        color_discrete_sequence=[BLUE, "#e1000f"],
    )
    figure.update_layout(xaxis_title=None, yaxis_title="Part des lignes (%)")
    st.plotly_chart(apply_theme(figure, 400), width="stretch")


def render() -> None:
    st.markdown("## Comparer deux jeux de données")
    st.caption(
        "Rapprochez deux jeux de données : métadonnées, schémas, colonnes communes, "
        "distributions numériques et répartitions catégorielles. "
        "L'analyse porte sur un aperçu de 500 lignes par fichier."
    )

    left_column, right_column = st.columns(2)
    with left_column:
        left_value = st_searchbox(
            api.suggest_dataset_choices,
            label="Jeu de données A",
            placeholder="Rechercher un jeu de données…",
            default_use_searchterm=True,
            debounce=300,
            key="compare-left",
        )
    with right_column:
        right_value = st_searchbox(
            api.suggest_dataset_choices,
            label="Jeu de données B",
            placeholder="Rechercher un jeu de données…",
            default_use_searchterm=True,
            debounce=300,
            key="compare-right",
        )

    left_id = _extract_id(left_value)
    right_id = _extract_id(right_value)

    if not left_id or not right_id:
        st.info(
            "Choisissez deux jeux de données dans les champs ci-dessus. "
            "La liste se met à jour pendant la frappe ; vous pouvez aussi coller "
            "un identifiant data.gouv.fr."
        )
        return

    if left_id == right_id:
        st.warning("Choisissez deux jeux de données différents pour lancer la comparaison.")
        return

    try:
        with st.spinner("Chargement du jeu de données A…"):
            dataset_a, resource_a, frame_a = _load_side(left_id)
        with st.spinner("Chargement du jeu de données B…"):
            dataset_b, resource_b, frame_b = _load_side(right_id)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    header_left, header_right = st.columns(2)
    with header_left:
        st.markdown(_header_html(dataset_a, "A"), unsafe_allow_html=True)
        if resource_a:
            st.caption(
                f"Fichier analysé : {resource_a.get('title')} · "
                f"{(resource_a.get('format') or '?').upper()}"
            )
    with header_right:
        st.markdown(_header_html(dataset_b, "B"), unsafe_allow_html=True)
        if resource_b:
            st.caption(
                f"Fichier analysé : {resource_b.get('title')} · "
                f"{(resource_b.get('format') or '?').upper()}"
            )

    st.markdown("#### Métadonnées")
    st.dataframe(_metrics_table(dataset_a, dataset_b), hide_index=True, width="stretch")

    if frame_a is None or frame_b is None:
        st.warning(
            "La comparaison détaillée nécessite un fichier tabulaire de chaque côté. "
            "Les métadonnées restent comparables."
        )
        return

    st.markdown("#### Schémas")
    schema = _schema_table(frame_a, frame_b)
    st.dataframe(schema, hide_index=True, width="stretch", height=320)
    common_columns = int((schema["Commune"] == "✓").sum())
    st.caption(
        f"{common_columns} colonne(s) commune(s) · "
        f"A : {len(frame_a):,} lignes × {len(frame_a.columns)} colonnes · "
        f"B : {len(frame_b):,} lignes × {len(frame_b.columns)} colonnes"
        .replace(",", " ")
    )

    st.markdown("#### Comparaison statistique")
    numeric_tab, categorical_tab = st.tabs(["Numérique", "Catégoriel"])
    with numeric_tab:
        _render_numeric_comparison(frame_a, frame_b)
    with categorical_tab:
        _render_categorical_comparison(frame_a, frame_b)
