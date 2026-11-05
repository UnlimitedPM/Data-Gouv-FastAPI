"""Composants de cartes (jeux de donnees, organisations, KPI)."""

from __future__ import annotations

from typing import Any

import navigation
import streamlit as st

from .formatting import (
    badge_label,
    clean_multiline,
    compact_html,
    esc,
    format_date,
    frequency_label,
    human_number,
    human_size,
    initials,
    license_label,
    relative_date,
    truncate,
)


def kpi_grid(items: list[dict[str, str]]) -> None:
    """Affiche une grille de cartes KPI."""
    cells = "".join(
        f"""
        <div class="dfe-kpi">
          <div class="dfe-kpi__value">{esc(item.get('value'))}</div>
          <div class="dfe-kpi__label">{esc(item.get('label'))}</div>
          <div class="dfe-kpi__hint">{esc(item.get('hint', ''))}</div>
        </div>
        """
        for item in items
    )
    st.markdown(compact_html(f'<div class="dfe-kpi-grid">{cells}</div>'), unsafe_allow_html=True)


def description_block(
    description: object, length: int, default: str
) -> tuple[str, str]:
    """Retourne (texte court échappé, bloc HTML « Lire plus » ou vide)."""
    full = clean_multiline(description or default)
    short = truncate(full, length)
    if len(full) <= length:
        return esc(short), ""

    full_html = esc(full).replace("\n", "<br />")
    more = compact_html(
        f'<details class="dfe-more"><summary>Lire plus</summary>'
        f'<div class="dfe-more__text">{full_html}</div></details>'
    )
    return esc(short), more


def _format_pills(
    formats: list[str], resources_count: int = 0, limit: int = 4
) -> str:
    if not formats:
        if resources_count:
            suffix = "s" if resources_count > 1 else ""
            return f'<span class="dfe-pill">{resources_count} fichier{suffix}</span>'
        return '<span class="dfe-pill dfe-pill--red">Aucun fichier</span>'
    return "".join(
        f'<span class="dfe-pill">{esc(fmt.upper())}</span>' for fmt in formats[:limit]
    )


def dataset_card_html(dataset: dict[str, Any]) -> str:
    """Genere le HTML d'une carte de jeu de donnees."""
    organization = dataset.get("organization") or {}
    org_name = organization.get("acronym") or organization.get("name") or "Producteur inconnu"
    metrics = dataset.get("metrics") or {}
    description, more = description_block(
        dataset.get("description"), 230, "Pas de description fournie."
    )
    page = dataset.get("page") or "https://www.data.gouv.fr"
    updated = dataset.get("last_update") or dataset.get("last_modified")
    tags = dataset.get("tags") or []
    tag_pills = "".join(
        f'<span class="dfe-pill">#{esc(tag)}</span>' for tag in tags[:4]
    )

    return compact_html(
        f"""
        <div class="dfe-card">
          <div class="dfe-card__top">
            <span class="dfe-pill dfe-pill--dark">{esc(org_name)}</span>
            <span class="dfe-card__date">Mis à jour {esc(relative_date(updated))}</span>
          </div>
          <h3 class="dfe-card__title">
            <a href="{esc(page)}" target="_blank" rel="noopener">{esc(dataset.get('title'))}</a>
          </h3>
          <p class="dfe-card__desc">{description}</p>
          {more}
          <div class="dfe-tags">{_format_pills(dataset.get('formats') or [], int(dataset.get('resources_count') or 0))}{tag_pills}</div>
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


def render_dataset_card(
    dataset: dict[str, Any],
    key: str,
    *,
    button_label: str = "Analyser →",
    target_page: str = "Visualiser",
) -> None:
    """Affiche une carte puis le bouton d'analyse associe."""
    st.markdown(dataset_card_html(dataset), unsafe_allow_html=True)
    if st.button(button_label, key=f"dataset-{key}", width="stretch"):
        st.session_state["selected_dataset_id"] = dataset["id"]
        navigation.go_to(target_page)


def organization_card_html(organization: dict[str, Any]) -> str:
    """Genere le HTML d'une carte d'organisation."""
    name = organization.get("name") or "Organisation inconnue"
    logo = organization.get("logo_thumbnail") or organization.get("logo")
    badges = organization.get("badges") or []
    badge_pills = "".join(
        f'<span class="dfe-pill dfe-pill--green">{esc(badge_label(badge))}</span>'
        for badge in badges[:3]
    )
    description, more = description_block(
        organization.get("description"), 170, "Pas de description."
    )
    page = organization.get("page") or "https://www.data.gouv.fr"

    if logo:
        avatar = f'<img class="dfe-org__logo" src="{esc(logo)}" alt="" loading="lazy" />'
    else:
        avatar = f'<div class="dfe-org__avatar">{esc(initials(name))}</div>'

    return compact_html(
        f"""
        <div class="dfe-card">
          <div class="dfe-card__top">
            <div class="dfe-org">
              {avatar}
              <div>
                <h3 class="dfe-card__title" style="margin-bottom:2px">
                  <a href="{esc(page)}" target="_blank" rel="noopener">{esc(name)}</a>
                </h3>
                <div class="dfe-card__meta">{esc(organization.get('acronym') or '')}</div>
              </div>
            </div>
            <div class="dfe-tags">{badge_pills}</div>
          </div>
          <p class="dfe-card__desc">{description}</p>
          {more}
          <div class="dfe-metrics">
            <div>
              <div class="dfe-metric__value">{esc(human_number(organization.get('datasets_count')))}</div>
              <div class="dfe-metric__label">jeux de données</div>
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
        </div>
        """
    )


def render_organization_card(organization: dict[str, Any], key: str) -> None:
    st.markdown(organization_card_html(organization), unsafe_allow_html=True)
    if st.button("Voir les jeux de données →", key=f"org-{key}", width="stretch"):
        st.session_state["selected_org_id"] = organization.get("id")
        navigation.go_to("Organisations")


def dataset_banner_html(dataset: dict[str, Any]) -> str:
    """Bandeau detaille pour la page de visualisation."""
    organization = dataset.get("organization") or {}
    metrics = dataset.get("metrics") or {}
    page = dataset.get("page") or "https://www.data.gouv.fr"
    org_name = organization.get("name") or "Producteur inconnu"
    logo = organization.get("logo_thumbnail") or organization.get("logo")
    avatar = (
        f'<img class="dfe-org__logo" src="{esc(logo)}" alt="" loading="lazy" />'
        if logo
        else f'<div class="dfe-org__avatar">{esc(initials(org_name))}</div>'
    )
    tags = "".join(f'<span class="dfe-pill">#{esc(tag)}</span>' for tag in (dataset.get("tags") or [])[:8])
    formats = _format_pills(
        dataset.get("formats") or [], int(dataset.get("resources_count") or 0)
    )
    description, more = description_block(
        dataset.get("description"), 560, "Pas de description fournie."
    )

    return compact_html(
        f"""
        <div class="dfe-card dfe-card--flat">
          <div class="dfe-org" style="align-items:flex-start;gap:16px">
            {avatar}
            <div style="flex:1;min-width:0">
              <h2 class="dfe-card__title" style="font-size:1.35rem;margin-bottom:6px">
                {esc(dataset.get('title'))}
              </h2>
              <p class="dfe-card__meta">
                {esc(org_name)} · Mis à jour {esc(format_date(dataset.get('last_update') or dataset.get('last_modified')))}
                · Fréquence {esc(frequency_label(dataset.get('frequency')))}
                · {esc(license_label(dataset.get('license')))}
              </p>
              <p class="dfe-card__desc">{description}</p>
              {more}
              <div class="dfe-tags">{formats}{tags}</div>
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


def empty_state(message: str) -> None:
    st.markdown(f'<div class="dfe-empty">{esc(message)}</div>', unsafe_allow_html=True)


def resource_label(resource: dict[str, Any]) -> str:
    title = resource.get("title") or resource.get("id") or "Sans titre"
    fmt = (resource.get("format") or "?").upper()
    size = human_size(resource.get("filesize"))
    return f"{title} · {fmt} · {size}"
