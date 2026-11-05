"""Petites fonctions de formatage partagees par les composants Streamlit."""

from __future__ import annotations

import html
import math
import re
from datetime import UTC, datetime

FRENCH_MONTHS = [
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
]

LICENSE_LABELS = {
    "lov2": "Licence Ouverte 2.0",
    "odbl": "Open Database License",
    "cc-by": "Creative Commons BY",
    "cc-by-sa": "Creative Commons BY-SA",
    "cc-zero": "CC0 (domaine public)",
    "notspecified": "Licence non précisée",
    "other-open": "Autre licence ouverte",
}

FREQUENCY_LABELS = {
    "annual": "Annuelle",
    "semi-annual": "Semestrielle",
    "semiannual": "Semestrielle",
    "bimonthly": "Bimestrielle",
    "biweekly": "Bimensuelle",
    "quarterly": "Trimestrielle",
    "monthly": "Mensuelle",
    "weekly": "Hebdomadaire",
    "daily": "Quotidienne",
    "hourly": "Horaire",
    "irregular": "Irrégulière",
    "continuous": "Continue",
    "punctual": "Ponctuelle",
    "unknown": "Inconnue",
}

FAMILY_LABELS = {
    "tabular": "Tableur",
    "geographical": "Géographique",
    "documents": "Documents",
    "machine_readable": "Lisible par machine",
    "other": "Autre",
}

PRODUCER_LABELS = {
    "public-service": "Service public",
    "local-authority": "Collectivité",
    "company": "Entreprise",
    "user": "Utilisateur",
    "not-specified": "Non précisé",
}

BADGE_LABELS = {
    "public-service": "Service public",
    "certified": "Certifié",
    "open-data": "Open data",
    "official": "Officiel",
}


def badge_label(value: object) -> str:
    key = str(value or "").strip().lower()
    return BADGE_LABELS.get(key, key.replace("-", " ").capitalize() if key else "")


def esc(value: object) -> str:
    """Echappe une valeur pour l'injection dans du HTML."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def compact_html(markup: str) -> str:
    """Compacte un bloc HTML pour eviter les blocs de code Markdown de Streamlit."""
    return re.sub(r"\s+", " ", markup).strip()


def human_number(value: object, digits: int = 1) -> str:
    """Formate un nombre a la francaise (1 234, 12,3 k, 4,5 M)."""
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if math.isnan(number) or math.isinf(number):
        return "—"

    absolute = abs(number)
    if absolute >= 1_000_000_000:
        text = f"{number / 1_000_000_000:.{digits}f} Md"
    elif absolute >= 1_000_000:
        text = f"{number / 1_000_000:.{digits}f} M"
    elif number.is_integer():
        text = f"{int(number):,}"
    else:
        text = f"{number:,.{digits}f}"
    return text.replace(",", " ").replace(".", ",")


def human_size(value: object) -> str:
    """Formate une taille de fichier."""
    try:
        size = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "—"
    if size <= 0:
        return "—"
    units = ["o", "Ko", "Mo", "Go", "To"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    digits = 0 if index == 0 else 1
    return f"{size:.{digits}f}".replace(".", ",") + f" {units[index]}"


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def format_date(value: object, with_time: bool = False) -> str:
    """Formate une date ISO en date francaise courte."""
    parsed = _parse_datetime(value)
    if parsed is None:
        return "—"
    text = f"{parsed.day} {FRENCH_MONTHS[parsed.month - 1]} {parsed.year}"
    if with_time:
        text += f" à {parsed.hour:02d}:{parsed.minute:02d}"
    return text


def relative_date(value: object) -> str:
    """Retourne une duree relative lisible (il y a 3 jours...)."""
    parsed = _parse_datetime(value)
    if parsed is None:
        return "—"
    delta = datetime.now(UTC) - parsed
    seconds = delta.total_seconds()
    if seconds < 0:
        return "à venir"
    days = int(seconds // 86400)
    if days == 0:
        hours = max(1, int(seconds // 3600))
        return f"il y a {hours} h"
    if days == 1:
        return "hier"
    if days < 30:
        return f"il y a {days} j"
    if days < 365:
        return f"il y a {days // 30} mois"
    return f"il y a {days // 365} an" + ("s" if days >= 730 else "")


def clean_multiline(value: object) -> str:
    """Retire le balisage Markdown en conservant les paragraphes."""
    text = str(value or "")
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[#*_`>|~]+", " ", text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    cleaned = "\n".join(lines).strip(" -\u2022")
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def clean_text(value: object) -> str:
    """Retire le balisage Markdown et compacte tout en une ligne."""
    return " ".join(clean_multiline(value).split())


def truncate(text: object, length: int = 240) -> str:
    if not text:
        return ""
    cleaned = clean_text(text)
    if len(cleaned) <= length:
        return cleaned
    cut = cleaned[: length - 1].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def license_label(value: object) -> str:
    key = str(value or "").strip().lower()
    return LICENSE_LABELS.get(key, key.replace("-", " ").title() if key else "—")


def frequency_label(value: object) -> str:
    key = str(value or "").strip().lower()
    return FREQUENCY_LABELS.get(key, key.capitalize() if key else "—")


def family_label(value: object) -> str:
    key = str(value or "").strip().lower()
    return FAMILY_LABELS.get(key, key.capitalize() if key else "—")


def producer_label(value: object) -> str:
    key = str(value or "").strip().lower()
    return PRODUCER_LABELS.get(key, key.capitalize() if key else "—")


def initials(value: object) -> str:
    words = [word for word in str(value or "").split() if word]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()
