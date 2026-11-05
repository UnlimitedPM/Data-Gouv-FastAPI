"""Client HTTP du frontend vers le backend FastAPI."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = float(os.getenv("API_TIMEOUT", "90"))


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


@st.cache_data(ttl=180, show_spinner=False)
def get_organization(organization_id: str) -> dict[str, Any]:
    return _request(f"/api/organizations/{organization_id}")


@st.cache_data(ttl=30, show_spinner=False)
def health() -> dict[str, Any]:
    try:
        return _request("/api/health")
    except ApiError as exc:
        return {"status": "down", "detail": str(exc)}
