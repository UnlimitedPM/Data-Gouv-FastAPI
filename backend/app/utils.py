"""Utilitaires texte partages."""

from __future__ import annotations

import unicodedata
from typing import Any


def normalize_text(value: Any) -> str:
    """Minuscule sans accents, pour une recherche tolerante."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()
