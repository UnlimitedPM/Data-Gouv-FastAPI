"""Client HTTP du frontend vers le backend FastAPI."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
# URL de l'API telle que vue par le navigateur du visiteur. Vide par defaut :
# le lien vers la documentation est alors relatif (/docs), ce qui fonctionne
# quand le site et l'API sont servis sur le meme domaine par un reverse proxy.
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "").rstrip("/")
TIMEOUT = float(os.getenv("API_TIMEOUT", "90"))


def docs_url() -> str:
    """Lien vers la documentation interactive generee par FastAPI (Swagger UI)."""
    return f"{PUBLIC_API_URL}/docs" if PUBLIC_API_URL else "/docs"


class ApiError(RuntimeError):
    """Le backend est injoignable ou renvoie une erreur."""


def _request(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{API_URL}{path}"
    cleaned = {
        key: value
        for key, value in (params or {}).items()
        if value is not None and value != ""
    }
    try:
        response = requests.get(url, params=cleaned, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ApiError(
            "Backend injoignable. Démarrez-le avec : "
            "`uvicorn app.main:app --reload` dans le dossier `backend/`. "
            f"Détail : {exc}"
        ) from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(f"Erreur API {response.status_code} — {detail}")

    try:
        return response.json()
    except ValueError as exc:
        raise ApiError("Réponse non JSON du backend.") from exc


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=300, show_spinner=False)
def get_overview() -> dict[str, Any]:
    return _request("/api/stats/overview")


@st.cache_data(ttl=120, show_spinner=False)
def search_datasets(**params: Any) -> dict[str, Any]:
    return _request("/api/search/datasets", params)


@st.cache_data(ttl=180, show_spinner=False)
def search_organizations(**params: Any) -> dict[str, Any]:
    return _request("/api/search/organizations", params)


@st.cache_data(ttl=300, show_spinner=False)
def suggest_datasets(term: str, limit: int = 8) -> list[str]:
    """Suggestions de titres pour la recherche en direct."""
    term = (term or "").strip()
    if len(term) < 2:
        return []
    payload = _request("/api/search/datasets", {"q": term, "page_size": limit})
    titles: list[str] = []
    for row in payload.get("data") or []:
        title = (row.get("title") or "").strip()
        if title and title not in titles:
            titles.append(title)
    return titles


@st.cache_data(ttl=300, show_spinner=False)
def suggest_dataset_choices(term: str, limit: int = 8) -> list[str]:
    """Suggestions « titre · id » pour la page de comparaison."""
    term = (term or "").strip()
    params: dict[str, Any] = {"page_size": limit}
    if len(term) >= 2:
        params["q"] = term
    else:
        params["sort"] = "-created"
    payload = _request("/api/search/datasets", params)
    choices: list[str] = []
    for row in payload.get("data") or []:
        title = (row.get("title") or "").strip()
        dataset_id = row.get("id") or ""
        if title and dataset_id:
            choice = f"{title}  ·  {dataset_id}"
            if choice not in choices:
                choices.append(choice)
    return choices


@st.cache_data(ttl=300, show_spinner=False)
def suggest_organizations(term: str, limit: int = 8) -> list[str]:
    """Suggestions de noms pour la recherche d'organisations en direct."""
    term = (term or "").strip()
    if len(term) < 2:
        return []
    payload = _request("/api/search/organizations", {"q": term, "page_size": limit})
    names: list[str] = []
    for row in payload.get("data") or []:
        name = (row.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


@st.cache_data(ttl=300, show_spinner=False)
def get_dataset(dataset_id: str) -> dict[str, Any]:
    return _request(f"/api/datasets/{dataset_id}")


@st.cache_data(ttl=300, show_spinner=False)
def get_preview(dataset_id: str, resource_id: str | None = None, limit: int = 500) -> dict[str, Any]:
    return _request(
        f"/api/datasets/{dataset_id}/preview",
        {"resource_id": resource_id, "limit": limit},
    )


@st.cache_data(ttl=600, show_spinner=False)
def get_profile(dataset_id: str, resource_id: str | None = None, limit: int = 20_000) -> dict[str, Any]:
    return _request(
        f"/api/datasets/{dataset_id}/profile",
        {"resource_id": resource_id, "limit": limit},
    )


@st.cache_data(ttl=600, show_spinner=False)
def get_geo(dataset_id: str, resource_id: str | None = None, limit: int = 800) -> dict[str, Any]:
    return _request(
        f"/api/datasets/{dataset_id}/geo",
        {"resource_id": resource_id, "limit": limit},
    )


@st.cache_data(ttl=180, show_spinner=False)
def get_organization(organization_id: str) -> dict[str, Any]:
    return _request(f"/api/organizations/{organization_id}")


@st.cache_data(ttl=30, show_spinner=False)
def health() -> dict[str, Any]:
    try:
        return _request("/api/health")
    except ApiError as exc:
        return {"status": "down", "detail": str(exc)}
