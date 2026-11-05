"""Page « Organisations » : annuaire et fiche producteur."""

from __future__ import annotations

from typing import Any

import api_client as api
import streamlit as st
from components.cards import (
    description_block,
    empty_state,
    render_dataset_card,
    render_organization_card,
)
from components.charts import bar_facets
from components.formatting import (
    badge_label,
    compact_html,
    esc,
    format_date,
    human_number,
    initials,
)
from streamlit_searchbox import st_searchbox


def _org_banner_html(organization: dict[str, Any]) -> str:
    name = organization.get("name") or "Organisation"
    logo = organization.get("logo_thumbnail") or organization.get("logo")
    avatar = (
        f'<img class="dfe-org__logo" src="{esc(logo)}" alt="" loading="lazy" />'
        if logo
        else f'<div class="dfe-org__avatar">{esc(initials(name))}</div>'
    )
    page = organization.get("page") or "https://www.data.gouv.fr"
    badges = "".join(
        f'<span class="dfe-pill dfe-pill--green">{esc(badge_label(badge))}</span>'
        for badge in (organization.get("badges") or [])[:4]
    )
    description, more = description_block(
        organization.get("description"), 620, "Pas de description fournie."
    )
    return compact_html(
        f"""
    <div class="dfe-card dfe-card--flat">
      <div class="dfe-org" style="align-items:flex-start;gap:16px">
        {avatar}
        <div style="flex:1;min-width:0">
          <h2 class="dfe-card__title" style="font-size:1.3rem;margin-bottom:4px">{esc(name)}</h2>
          <p class="dfe-card__meta">
            {esc(organization.get('acronym') or '')} · créée le {esc(format_date(organization.get('created_at')))}
          </p>
          <p class="dfe-card__desc">{description}</p>
          {more}
          <div class="dfe-tags">{badges}</div>
          <div class="dfe-metrics">
            <div>
              <div class="dfe-metric__value">{esc(human_number(organization.get('datasets_count')))}</div>
              <div class="dfe-metric__label">jeux de données</div>
            </div>
            <div>
              <div class="dfe-metric__value">{esc(human_number(organization.get('reuses_count')))}</div>
              <div class="dfe-metric__label">réutilisations</div>
            </div>
            <div>
              <div class="dfe-metric__value">{esc(human_number(organization.get('followers')))}</div>
              <div class="dfe-metric__label">suiveurs</div>
            </div>
            <div>
              <div class="dfe-metric__value">{esc(human_number(organization.get('views')))}</div>
              <div class="dfe-metric__label">vues</div>
            </div>
          </div>
          <p style="margin:14px 0 0">
            <a class="dfe-card__link" href="{esc(page)}" target="_blank" rel="noopener">
              Voir la fiche officielle sur data.gouv.fr ↗
            </a>
          </p>
        </div>
      </div>
    </div>
    """
    )


def _render_detail(organization_id: str) -> None:
    try:
        with st.spinner("Chargement de l'organisation…"):
            payload = api.get_organization(organization_id)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    organization = payload.get("organization") or {}
    datasets = payload.get("datasets") or []
    total = int(payload.get("datasets_total") or 0)

    if st.button("← Toutes les organisations"):
        st.session_state.pop("selected_org_id", None)
        st.rerun()

    st.markdown(_org_banner_html(organization), unsafe_allow_html=True)

    st.markdown("#### Derniers jeux de données publiés")
    st.caption(f"{human_number(total)} jeux de données au total — les 10 plus récents sont affichés.")

    if not datasets:
        empty_state("Cette organisation n'a publié aucun jeu de données public.")
        return

    left, right = st.columns(2)
    for index, dataset in enumerate(datasets):
        with (left if index % 2 == 0 else right):
            render_dataset_card(
                dataset,
                key=f"org-{organization_id}-{dataset.get('id')}",
                button_label="Analyser →",
            )


def _render_list() -> None:
    row = st.columns([3, 1])
    with row[0]:
        query = st_searchbox(
            api.suggest_organizations,
            label="Recherche en direct",
            placeholder="ex : ministère, commune, biodiversité…",
            default_use_searchterm=True,
            debounce=300,
            key="org_searchbox",
        ) or ""
    query = str(query).strip()
    sort_label = row[1].selectbox(
        "Trier par", ["Plus de jeux de données", "Plus récentes", "Plus suivies"], key="org_sort"
    )
    sort = {
        "Plus de jeux de données": "-datasets",
        "Plus récentes": "-created",
        "Plus suivies": "-followers",
    }.get(sort_label)

    if query and len(query) < 2:
        st.info("Tapez au moins deux caractères pour lancer la recherche.")
        return

    try:
        with st.spinner("Recherche d'organisations…"):
            result = api.search_organizations(q=query or None, page=1, page_size=12, sort=sort)
    except api.ApiError as exc:
        st.error(str(exc))
        return

    organizations = result.get("data") or []
    st.markdown(
        f"**{human_number(result.get('total'))}** organisations trouvées"
    )

    if not query and not organizations:
        empty_state("Aucune organisation disponible.")
        return

    if not organizations:
        empty_state("Aucune organisation ne correspond à cette recherche.")
        return

    left, right = st.columns(2)
    for index, organization in enumerate(organizations):
        with (left if index % 2 == 0 else right):
            render_organization_card(organization, key=f"{query}-{organization.get('id')}")

    try:
        overview = api.get_overview()
        facets = (overview.get("facets") or {}).get("organization_id_with_name") or []
    except api.ApiError:
        facets = []
    if facets:
        figure = bar_facets(
            facets,
            "Organisations les plus prolifiques",
            color="#1212ff",
            limit=12,
            height=400,
        )
        if figure:
            st.plotly_chart(figure, width="stretch")


def render() -> None:
    st.markdown("## Organisations")
    st.caption(
        "Découvrez les producteurs de données publiques : ministères, collectivités, "
        "établissements publics, entreprises et contributeurs."
    )

    selected = st.session_state.get("selected_org_id")
    if selected:
        _render_detail(str(selected))
    else:
        _render_list()
