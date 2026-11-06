"""Header et footer communs a toutes les pages Streamlit."""

from __future__ import annotations

import streamlit as st

from .formatting import compact_html

APP_VERSION = "0.2.0"


def render_header(
    subtitle: str = "Explorez, comprenez et visualisez les données publiques françaises.",
) -> None:
    """Affiche le bandeau de marque en haut de page."""
    st.markdown(
        compact_html(
            f"""
        <div class="dfe-header">
          <div class="dfe-header__row">
            <div class="dfe-brand">
              <div class="dfe-brand__mark"><span class="dfe-flag"></span></div>
              <div>
                <h1 class="dfe-brand__title">DataFrance Explorer</h1>
                <p class="dfe-brand__subtitle">{subtitle}</p>
              </div>
            </div>
            <div class="dfe-header__chips">
              <span class="dfe-chip">Catalogue local</span>
              <span class="dfe-chip">FastAPI</span>
              <span class="dfe-chip">Streamlit</span>
            </div>
          </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.markdown(
        compact_html(
            """
        <div class="dfe-sidebar-brand">
          <span class="dfe-flag"></span> DataFrance<br />
          <small>Explorer</small>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def render_sidebar_status(ok: bool, detail: str = "", catalog_empty: bool = False) -> None:
    if not ok:
        dot, label = "dfe-dot dfe-dot--down", "API hors ligne"
    elif catalog_empty:
        dot, label = "dfe-dot dfe-dot--warn", "Catalogue vide"
    else:
        dot, label = "dfe-dot", "API connectée"
    st.markdown(
        compact_html(
            f"""
        <div class="dfe-sidebar-status">
          <span class="{dot}"></span>
          <span>{label}</span>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )
    if detail and not ok:
        st.caption(detail[:180])


def render_footer() -> None:
    """Affiche le pied de page commun."""
    st.markdown(
        compact_html(
            f"""
        <div class="dfe-footer">
          <div class="dfe-footer__grid">
            <div>
              <h4>DataFrance Explorer</h4>
              <p>
                Explorateur de données publiques : recherche, aperçu,
                statistiques et visualisations générées à partir d'un
                instantané du catalogue data.gouv.fr stocké en base locale.
              </p>
            </div>
            <div>
              <h4>Sources &amp; licences</h4>
              <ul>
                <li><a href="https://www.data.gouv.fr" target="_blank" rel="noopener">data.gouv.fr</a> — plateforme officielle</li>
                <li><a href="https://www.data.gouv.fr/api/1/swagger.json" target="_blank" rel="noopener">Documentation de l'API</a></li>
                <li>Données sous licences propres à chaque producteur</li>
              </ul>
            </div>
            <div>
              <h4>Stack technique</h4>
              <ul>
                <li>Backend : FastAPI, SQLAlchemy, SQLite, pandas</li>
                <li>Frontend : Streamlit, Plotly</li>
                <li>Ingestion hors ligne · cache TTL en mémoire</li>
              </ul>
            </div>
          </div>
          <div class="dfe-footer__bottom">
            <span>Version {APP_VERSION} · prototype open source</span>
            <span>Données © producteurs publics · interface non officielle</span>
          </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )
