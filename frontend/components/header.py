"""Header et footer communs a toutes les pages Streamlit."""

from __future__ import annotations

import streamlit as st

from .formatting import compact_html

APP_VERSION = "0.1.0"


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
              <span class="dfe-chip">API data.gouv.fr · v2</span>
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


def render_sidebar_status(ok: bool, detail: str = "") -> None:
    dot = "dfe-dot" if ok else "dfe-dot dfe-dot--down"
    label = "API connectée" if ok else "API hors ligne"
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
                Première ébauche d'un explorateur de données publiques :
                recherche, aperçu, statistiques et visualisations générées
                automatiquement à partir de l'API officielle data.gouv.fr.
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
                <li>Backend : FastAPI, httpx, pandas</li>
                <li>Frontend : Streamlit, Plotly</li>
                <li>Cache mémoire TTL côté backend</li>
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
