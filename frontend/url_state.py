"""Synchronisation de la vue courante avec les paramètres d'URL.

Permet de partager un lien qui rouvre le même jeu de données, le même fichier
et les mêmes filtres de lignes.
"""

from __future__ import annotations

import base64
import json
from datetime import date
from typing import Any
from urllib.parse import urlencode

import streamlit as st


def _encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(value: str) -> dict[str, Any]:
    padding = "=" * (-len(value) % 4)
    try:
        raw = base64.urlsafe_b64decode(value + padding)
        payload = json.loads(raw)
    except (ValueError, TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def serialize_filters(active: dict[str, Any]) -> dict[str, Any]:
    items: list[list[Any]] = []
    for column, spec in active.items():
        if isinstance(spec, tuple) and len(spec) == 2 and spec[0] == "contains":
            items.append([column, "contains", str(spec[1])])
        elif isinstance(spec, list):
            items.append([column, "in", [str(value) for value in spec]])
        elif isinstance(spec, tuple) and len(spec) == 2 and hasattr(spec[0], "isoformat"):
            items.append([column, "date", [spec[0].isoformat(), spec[1].isoformat()]])
        elif isinstance(spec, tuple) and len(spec) == 2:
            items.append([column, "range", [float(spec[0]), float(spec[1])]])
    return {"v": 1, "items": items} if items else {}


def deserialize_filters(payload: dict[str, Any]) -> dict[str, Any]:
    active: dict[str, Any] = {}
    for item in payload.get("items") or []:
        if not isinstance(item, list) or len(item) != 3:
            continue
        column, kind, value = item
        try:
            if kind == "contains":
                active[str(column)] = ("contains", str(value))
            elif kind == "in":
                active[str(column)] = [str(entry) for entry in value]
            elif kind == "date":
                active[str(column)] = (date.fromisoformat(value[0]), date.fromisoformat(value[1]))
            elif kind == "range":
                active[str(column)] = (float(value[0]), float(value[1]))
        except (TypeError, ValueError, IndexError):
            continue
    return active


def read_view() -> dict[str, Any]:
    """Lit la vue demandée dans l'URL."""
    params = st.query_params
    filter_param = params.get("filters")
    filters = deserialize_filters(_decode(filter_param)) if filter_param else {}
    return {
        "dataset": params.get("dataset"),
        "resource": params.get("resource"),
        "filters": filters,
    }


def sync_view(
    dataset_id: str | None,
    resource_id: str | None = None,
    filters: dict[str, Any] | None = None,
) -> None:
    """Ecrit la vue courante dans l'URL (sans recharger la page)."""
    params = dict(st.query_params)
    if dataset_id:
        params["dataset"] = dataset_id
    else:
        params.pop("dataset", None)

    if resource_id:
        params["resource"] = resource_id
    else:
        params.pop("resource", None)

    encoded = serialize_filters(filters or {})
    if encoded:
        params["filters"] = _encode(encoded)
    else:
        params.pop("filters", None)

    if dict(st.query_params) != params:
        st.query_params.from_dict(params)


def clear_view() -> None:
    """Retire les paramètres de vue de l'URL."""
    st.query_params.clear()


def share_url() -> str:
    """Construit l'URL complète de la vue courante."""
    base = str(getattr(st.context, "url", "") or "http://localhost:8501").split("?")[0]
    params = dict(st.query_params)
    if not params:
        return base
    return f"{base}?{urlencode(params)}"
