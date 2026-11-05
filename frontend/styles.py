"""Charte graphique et injection CSS du frontend Streamlit."""

from __future__ import annotations

import streamlit as st

CSS = """
<style>
:root {
  --dfe-blue: #000091;
  --dfe-blue-light: #1212ff;
  --dfe-red: #e1000f;
  --dfe-ink: #161616;
  --dfe-muted: #666666;
  --dfe-surface: #ffffff;
  --dfe-surface-alt: #f5f5fe;
  --dfe-border: #e3e3fd;
  --dfe-radius: 16px;
}

html, body, [class*="css"] {
  font-family: "Marianne", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

.block-container {
  padding-top: 1.4rem;
  padding-bottom: 2.5rem;
  max-width: 1280px;
}

#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* ---------------------------------------------------------------- sidebar */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #000091 0%, #1a1ac5 55%, #2d2dd9 100%);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] small {
  color: #ecedff !important;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] label {
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  padding: 0.35rem 0.7rem;
  margin-bottom: 0.25rem;
  transition: background 0.15s ease;
}
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] label:hover {
  background: rgba(255, 255, 255, 0.16);
}
[data-testid="stSidebar"] hr {
  border-color: rgba(255, 255, 255, 0.18);
}

.dfe-sidebar-brand {
  color: #ffffff;
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  line-height: 1.2;
  margin: 0.2rem 0 1rem;
}
.dfe-sidebar-brand small {
  font-weight: 500;
  font-size: 0.75rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.75;
}
.dfe-sidebar-status {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  padding: 8px 12px;
  font-size: 0.78rem;
  color: #ecedff;
  margin-bottom: 0.75rem;
}
.dfe-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #27a658;
  box-shadow: 0 0 0 3px rgba(39, 166, 88, 0.25);
}
.dfe-dot--down { background: #e1000f; box-shadow: 0 0 0 3px rgba(225, 0, 15, 0.25); }

/* ----------------------------------------------------------------- header */
.dfe-header {
  background:
    radial-gradient(1200px 420px at 8% -30%, #2f2fe0 0%, rgba(47, 47, 224, 0) 60%),
    linear-gradient(118deg, #000091 0%, #1212ff 62%, #4040ff 100%);
  color: #ffffff;
  border-radius: 20px;
  padding: 26px 30px 28px;
  margin-bottom: 22px;
  box-shadow: 0 22px 48px -30px rgba(0, 0, 145, 0.7);
  position: relative;
  overflow: hidden;
}
.dfe-header::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 4px;
  background: linear-gradient(90deg, #000091 0 34%, #ffffff 34% 67%, #e1000f 67% 100%);
  opacity: 0.95;
}
.dfe-header__row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  flex-wrap: wrap;
}
.dfe-brand { display: flex; align-items: center; gap: 16px; }
.dfe-brand__mark {
  width: 48px;
  height: 48px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.28);
  display: grid;
  place-items: center;
  flex: none;
}
.dfe-flag {
  display: inline-block;
  width: 24px;
  height: 16px;
  border-radius: 2px;
  background: linear-gradient(90deg, #000091 0 33.33%, #ffffff 33.33% 66.66%, #e1000f 66.66% 100%);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.35) inset;
  vertical-align: middle;
}
.dfe-sidebar-brand .dfe-flag { width: 20px; height: 13px; margin-right: 4px; }
.dfe-brand__title {
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: -0.025em;
  margin: 0;
  color: #ffffff;
}
.dfe-brand__subtitle {
  margin: 5px 0 0;
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.92rem;
  max-width: 620px;
}
.dfe-header__chips { display: flex; gap: 8px; flex-wrap: wrap; }
.dfe-chip {
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.24);
  color: #ffffff;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.76rem;
  font-weight: 600;
  white-space: nowrap;
}

/* ------------------------------------------------------------------- KPI */
.dfe-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 14px;
  margin: 6px 0 22px;
}
.dfe-kpi {
  background: linear-gradient(158deg, #ffffff 0%, #f5f5fe 100%);
  border: 1px solid var(--dfe-border);
  border-radius: var(--dfe-radius);
  padding: 16px 18px;
  box-shadow: 0 12px 26px -26px rgba(0, 0, 145, 0.55);
}
.dfe-kpi__value {
  font-size: 1.9rem;
  font-weight: 800;
  color: var(--dfe-blue);
  line-height: 1.08;
  letter-spacing: -0.02em;
}
.dfe-kpi__label { color: #555555; font-size: 0.83rem; margin-top: 4px; }
.dfe-kpi__hint { color: #8a8a8a; font-size: 0.72rem; margin-top: 6px; }

/* ----------------------------------------------------------------- cards */
.dfe-card {
  background: #ffffff;
  border: 1px solid var(--dfe-border);
  border-radius: var(--dfe-radius);
  padding: 18px 20px;
  margin-bottom: 8px;
  box-shadow: 0 12px 26px -26px rgba(0, 0, 145, 0.55);
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.dfe-card:hover {
  transform: translateY(-2px);
  border-color: #c9c9f7;
  box-shadow: 0 18px 34px -26px rgba(0, 0, 145, 0.6);
}
.dfe-card--flat { transition: none; }
.dfe-card--flat:hover { transform: none; }
.dfe-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.dfe-card__date { color: #8a8a8a; font-size: 0.74rem; }
.dfe-card__title {
  font-size: 1.03rem;
  font-weight: 700;
  color: var(--dfe-ink);
  margin: 0 0 8px;
  line-height: 1.35;
}
.dfe-card__title a { color: var(--dfe-ink); text-decoration: none; }
.dfe-card__title a:hover { color: var(--dfe-blue); text-decoration: underline; }
.dfe-card__meta { color: #666666; font-size: 0.8rem; margin: 0 0 8px; }
.dfe-card__desc {
  color: #3a3a3a;
  font-size: 0.88rem;
  line-height: 1.55;
  margin: 0 0 8px;
}
.dfe-more { margin: 0 0 12px; }
.dfe-more summary {
  cursor: pointer;
  list-style: none;
  display: block;
  user-select: none;
}
.dfe-more summary::-webkit-details-marker { display: none; }
.dfe-more__preview {
  display: block;
  color: #3a3a3a;
  font-size: 0.88rem;
  line-height: 1.55;
}
.dfe-more__toggle {
  display: inline-block;
  margin-top: 5px;
  color: var(--dfe-blue);
  font-size: 0.8rem;
  font-weight: 700;
}
.dfe-more__toggle:hover { text-decoration: underline; }
.dfe-more__less { display: none; }
.dfe-more[open] .dfe-more__preview { display: none; }
.dfe-more[open] .dfe-more__more { display: none; }
.dfe-more[open] .dfe-more__less { display: inline-block; }
.dfe-more__text {
  margin-top: 6px;
  color: #3a3a3a;
  font-size: 0.88rem;
  line-height: 1.55;
}
.dfe-card__link { font-size: 0.8rem; font-weight: 600; color: var(--dfe-blue); text-decoration: none; }
.dfe-card__link:hover { text-decoration: underline; }
.dfe-metrics { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 12px; }
.dfe-metric__value { font-size: 1.05rem; font-weight: 800; color: var(--dfe-blue); line-height: 1.1; }
.dfe-metric__label {
  font-size: 0.68rem;
  color: #7a7a7a;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
.dfe-card__footer { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }

.dfe-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.dfe-pill {
  background: var(--dfe-surface-alt);
  color: var(--dfe-blue);
  border: 1px solid var(--dfe-border);
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}
.dfe-pill--red { background: #fff1f2; color: #b3000c; border-color: #ffd7da; }
.dfe-pill--green { background: #eafaf1; color: #0f7a4d; border-color: #c9f0dc; }
.dfe-pill--dark { background: #161616; color: #ffffff; border-color: #161616; }

/* ------------------------------------------------------------------ orgs */
.dfe-org { display: flex; gap: 14px; align-items: flex-start; }
.dfe-org__logo {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  object-fit: contain;
  background: #ffffff;
  border: 1px solid var(--dfe-border);
  flex: none;
}
.dfe-org__avatar {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: var(--dfe-blue);
  color: #ffffff;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 0.95rem;
  flex: none;
}

/* --------------------------------------------------------------- sections */
.dfe-section-title { display: flex; align-items: center; gap: 10px; margin: 22px 0 12px; }
.dfe-section-title::before {
  content: "";
  width: 4px;
  height: 20px;
  border-radius: 2px;
  background: var(--dfe-blue);
}
.dfe-section-title h2 { font-size: 1.15rem; margin: 0; color: var(--dfe-ink); font-weight: 700; }
.dfe-section-title span { color: #8a8a8a; font-size: 0.8rem; }

.dfe-empty {
  border: 1px dashed #c9c9f7;
  border-radius: var(--dfe-radius);
  background: #fbfbff;
  padding: 26px;
  text-align: center;
  color: #666666;
  font-size: 0.9rem;
}

/* --------------------------------------------------------------- widgets */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 999px;
  border: 1px solid var(--dfe-blue);
  background: var(--dfe-blue);
  color: #ffffff;
  font-weight: 600;
  padding: 0.42rem 1.1rem;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
  background: var(--dfe-blue-light);
  border-color: var(--dfe-blue-light);
  color: #ffffff;
}
.stButton > button:disabled { opacity: 0.45; }

[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: var(--dfe-radius);
  border-color: var(--dfe-border);
}

div[data-testid="stExpander"] {
  border: 1px solid var(--dfe-border);
  border-radius: 12px;
  background: #ffffff;
}

/* ---------------------------------------------------------------- footer */
.dfe-footer {
  margin-top: 44px;
  background: #161616;
  color: #dcdcdc;
  border-radius: 20px;
  padding: 28px 30px 18px;
}
.dfe-footer__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 24px;
}
.dfe-footer h4 { color: #ffffff; font-size: 0.88rem; margin: 0 0 8px; font-weight: 700; }
.dfe-footer p { color: #bdbdbd; font-size: 0.8rem; line-height: 1.65; margin: 0; }
.dfe-footer ul { margin: 0; padding-left: 1.05rem; }
.dfe-footer li { color: #bdbdbd; font-size: 0.8rem; line-height: 1.75; }
.dfe-footer a { color: #9f9fff; text-decoration: none; }
.dfe-footer a:hover { text-decoration: underline; }
.dfe-footer__bottom {
  border-top: 1px solid #2b2b2b;
  margin-top: 22px;
  padding-top: 12px;
  color: #8a8a8a;
  font-size: 0.74rem;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
"""


def inject_css() -> None:
    """Injecte la feuille de style de l'application."""
    st.markdown(CSS, unsafe_allow_html=True)
