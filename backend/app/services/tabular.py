"""Lecture locale (en memoire) des ressources tabulaires pour l'apercu et le profilage."""

from __future__ import annotations

import csv
import io
import json
import math
from datetime import date, datetime
from typing import Any

import httpx
import numpy as np
import pandas as pd

from ..config import Settings
from ..schemas import (
    ColumnInfo,
    ColumnProfile,
    CorrelationMatrix,
    PreviewResponse,
    ProfileResponse,
    Resource,
    TopValue,
)
from .cache import AsyncTTLCache

# Formats que pandas sait lire sans dependance exotique.
_READERS: dict[str, str] = {
    "csv": "csv",
    "txt": "csv",
    "tab": "tsv",
    "tsv": "tsv",
    "xls": "excel",
    "xlsx": "excel",
    "xlsm": "excel",
    "json": "json",
    "geojson": "geojson",
    "ndjson": "ndjson",
    "jsonl": "ndjson",
    "parquet": "parquet",
}

_FRAME_CACHE = AsyncTTLCache(maxsize=8, ttl=900)


class TabularError(RuntimeError):
    """La ressource ne peut pas etre lue comme un tableau."""

    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


# --------------------------------------------------------------------------- #
# Telechargement
# --------------------------------------------------------------------------- #
async def _download(
    http: httpx.AsyncClient,
    url: str,
    max_bytes: int,
    *,
    allow_truncate: bool = False,
) -> tuple[bytes, bool]:
    """Telecharge une ressource, avec troncature optionnelle des gros fichiers texte."""
    try:
        async with http.stream("GET", url) as response:
            response.raise_for_status()
            buffer = bytearray()
            async for chunk in response.aiter_bytes(65536):
                buffer.extend(chunk)
                if len(buffer) > max_bytes:
                    if allow_truncate:
                        return bytes(buffer[:max_bytes]), True
                    raise TabularError(
                        "Fichier trop volumineux pour l'apercu "
                        f"(limite {max_bytes // 1_000_000} Mo)."
                    )
            return bytes(buffer), False
    except httpx.HTTPError as exc:
        raise TabularError(f"Telechargement du fichier impossible : {exc}") from exc


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #
def detect_format(resource: Resource) -> str | None:
    fmt = (resource.format or "").strip().lower().lstrip(".")
    fmt = fmt.split(",", 1)[0].strip()
    if fmt in _READERS:
        return fmt
    title = (resource.title or "").lower()
    if "." in title:
        ext = title.rsplit(".", 1)[-1]
        if ext in _READERS:
            return ext
    return None


def _sniff_separator(text: str) -> str:
    sample = text[:20_000]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _decode(content: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace"), "utf-8 (with replacement)"


def _read_csv(content: bytes, separator: str | None = None) -> tuple[pd.DataFrame, str]:
    text, encoding = _decode(content)
    sep = separator or _sniff_separator(text)
    try:
        frame = pd.read_csv(
            io.StringIO(text),
            sep=sep,
            on_bad_lines="skip",
            engine="python",
        )
    except pd.errors.EmptyDataError as exc:
        raise TabularError("Le fichier est vide.") from exc
    except (pd.errors.ParserError, ValueError) as exc:
        raise TabularError(f"Lecture CSV impossible : {exc}") from exc
    return frame, f"encodage {encoding}, separateur {sep!r}"


def _read_json(content: bytes, kind: str) -> tuple[pd.DataFrame, str]:
    text, encoding = _decode(content)
    try:
        if kind == "ndjson":
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            return pd.json_normalize(rows), f"encodage {encoding}, NDJSON"

        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise TabularError(f"Lecture JSON impossible : {exc}") from exc

    if isinstance(payload, dict) and isinstance(payload.get("features"), list):
        rows = [f.get("properties") or {} for f in payload["features"] if isinstance(f, dict)]
        return pd.DataFrame(rows), f"encodage {encoding}, GeoJSON"

    if isinstance(payload, list):
        return pd.json_normalize(payload), f"encodage {encoding}, JSON"

    if isinstance(payload, dict):
        lists = [value for value in payload.values() if isinstance(value, list)]
        if len(lists) == 1:
            return pd.json_normalize(lists[0]), f"encodage {encoding}, JSON"
        return pd.json_normalize([payload]), f"encodage {encoding}, JSON"

    raise TabularError("Structure JSON non reconnue.")


def _read_content(content: bytes, kind: str) -> tuple[pd.DataFrame, str]:
    if kind in {"csv", "tsv"}:
        return _read_csv(content, "\t" if kind == "tsv" else None)

    if kind == "excel":
        try:
            return pd.read_excel(io.BytesIO(content)), "fichier Excel"
        except Exception as exc:
            raise TabularError(f"Lecture Excel impossible : {exc}") from exc

    if kind in {"json", "geojson", "ndjson"}:
        return _read_json(content, kind)

    if kind == "parquet":
        try:
            return pd.read_parquet(io.BytesIO(content)), "fichier Parquet"
        except Exception as exc:
            raise TabularError(f"Lecture Parquet impossible : {exc}") from exc

    raise TabularError("Format non supporte pour l'apercu.")


# --------------------------------------------------------------------------- #
# Nettoyage du DataFrame
# --------------------------------------------------------------------------- #
def _clean_columns(frame: pd.DataFrame) -> pd.DataFrame:
    names: list[str] = []
    seen: dict[str, int] = {}
    for index, column in enumerate(frame.columns):
        name = str(column).replace("\ufeff", "").strip() or f"col_{index + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        names.append(name)
    frame.columns = names
    return frame


def _coerce_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    """Convertit les colonnes numeriques ecrites a la francaise (virgule decimale)."""
    for column in frame.columns:
        series = frame[column]
        if series.dtype != object:
            continue
        sample = series.dropna().astype(str).head(300)
        if sample.empty:
            continue
        # Ne pas casser les codes a zero initial (code INSEE, code postal...).
        if sample.str.fullmatch(r"0\d+").any():
            continue
        cleaned = (
            sample.str.replace("\u202f", "", regex=False)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        ratio = pd.to_numeric(cleaned, errors="coerce").notna().mean()
        if ratio < 0.9:
            continue
        frame[column] = pd.to_numeric(
            series.astype(str)
            .str.replace("\u202f", "", regex=False)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False),
            errors="coerce",
        )
    return frame


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return None if math.isnan(number) or math.isinf(number) else number
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, str):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int,)):
        return value
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    return str(value)


def _simple_dtype(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    return "text"


def _kind(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if series.dtype == object:
        sample = series.dropna().astype(str).head(300)
        if not sample.empty:
            try:
                parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            except (TypeError, ValueError):
                parsed = pd.to_datetime(sample, errors="coerce")
            if parsed.notna().mean() >= 0.8:
                return "date"
        return "text"
    # Categories, intervalles pandas et autres types exotiques : traites comme du texte.
    return "text"


async def get_frame(
    http: httpx.AsyncClient,
    settings: Settings,
    resource: Resource,
    max_rows: int | None = None,
) -> tuple[pd.DataFrame, str, list[str], bool]:
    """Charge (et met en cache) un DataFrame normalise depuis une ressource."""
    max_rows = max_rows or settings.profile_rows
    cache_key = f"{resource.parquet_url or resource.url}|{max_rows}"

    async def load() -> tuple[pd.DataFrame, str, list[str], bool]:
        warnings: list[str] = []
        source = "file"
        frame: pd.DataFrame | None = None

        # 1. Le parquet pre-calcule par data.gouv.fr est plus rapide et plus fiable.
        if resource.parquet_url:
            try:
                content, _ = await _download(
                    http,
                    resource.parquet_url,
                    int(settings.max_parquet_download_mb * 1_000_000),
                )
                frame = pd.read_parquet(io.BytesIO(content))
                source = "parquet data.gouv.fr"
            except Exception as exc:  # noqa: BLE001 - on retombe sur le fichier source
                warnings.append(
                    "Parquet indisponible, retour au fichier original "
                    f"({str(exc)[:160]})."
                )

        # 2. Sinon, telechargement et lecture du fichier d'origine.
        if frame is None:
            kind = detect_format(resource)
            if kind is None or kind not in _READERS:
                raise TabularError(
                    "Cette ressource n'est pas tabulaire. Formats acceptes : "
                    + ", ".join(sorted(_READERS))
                )
            if not resource.url:
                raise TabularError("Cette ressource n'a pas d'URL de telechargement.")

            text_format = _READERS[kind] in {"csv", "tsv", "json", "geojson", "ndjson"}
            content, partial = await _download(
                http,
                resource.url,
                int(settings.max_download_mb * 1_000_000),
                allow_truncate=text_format,
            )
            if partial:
                warnings.append(
                    "Fichier volumineux : seuls les premiers "
                    f"{settings.max_download_mb:.0f} Mo ont ete telecharges."
                )
            frame, detail = _read_content(content, _READERS[kind])
            source = f"fichier source ({detail})"

        frame = _clean_columns(frame)
        frame = _coerce_numeric(frame)

        truncated = len(frame) > max_rows
        if truncated:
            frame = frame.head(max_rows).copy()
            warnings.append(
                f"Analyse limitee aux {max_rows:,} premieres lignes du fichier."
                .replace(",", " ")
            )

        return frame, source, warnings, truncated

    return await _FRAME_CACHE.get_or_create(cache_key, load)


# --------------------------------------------------------------------------- #
# API publique du module
# --------------------------------------------------------------------------- #
async def build_preview(
    http: httpx.AsyncClient,
    settings: Settings,
    resource: Resource,
    dataset_id: str,
    limit: int,
) -> PreviewResponse:
    frame, source, warnings, truncated = await get_frame(http, settings, resource)
    view = frame.head(limit)

    columns = [ColumnInfo(name=str(col), dtype=_simple_dtype(view[col])) for col in view.columns]
    rows = [[_json_safe(value) for value in row] for row in view.itertuples(index=False, name=None)]

    return PreviewResponse(
        dataset_id=dataset_id,
        resource=resource,
        source=source,
        columns=columns,
        rows=rows,
        rows_loaded=len(view),
        truncated=truncated or len(frame) > len(view),
        warnings=warnings,
    )


def _number(value: Any, digits: int = 2) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def _profile_column(series: pd.Series, kind: str) -> ColumnProfile:
    non_null = int(series.notna().sum())
    missing = int(len(series) - non_null)
    stats: dict[str, Any] = {}
    top_values: list[TopValue] = []

    if kind == "number":
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if not numeric.empty:
            stats = {
                "min": _number(numeric.min()),
                "max": _number(numeric.max()),
                "mean": _number(numeric.mean()),
                "median": _number(numeric.median()),
                "std": _number(numeric.std()),
                "sum": _number(numeric.sum()),
            }
    elif kind == "date":
        parsed = pd.to_datetime(series, errors="coerce").dropna()
        if not parsed.empty:
            stats = {
                "min": parsed.min().isoformat(),
                "max": parsed.max().isoformat(),
            }
    elif kind in {"text", "boolean"}:
        counts = series.astype(str).value_counts().head(5)
        total = max(1, non_null)
        top_values = [
            TopValue(value=str(value), count=int(count), pct=round(count / total * 100, 1))
            for value, count in counts.items()
        ]

    unique = int(series.nunique(dropna=True))

    return ColumnProfile(
        name=str(series.name),
        kind=kind,
        dtype=str(series.dtype),
        non_null=non_null,
        missing=missing,
        missing_pct=round(missing / max(1, len(series)) * 100, 1),
        unique=unique,
        stats=stats,
        top_values=top_values,
    )


async def build_profile(
    http: httpx.AsyncClient,
    settings: Settings,
    resource: Resource,
    dataset_id: str,
    limit: int,
) -> ProfileResponse:
    frame, source, warnings, truncated = await get_frame(
        http, settings, resource, max_rows=limit
    )

    columns: list[ColumnProfile] = []
    numeric_summary: list[dict[str, Any]] = []
    numeric_frames: dict[str, pd.Series] = {}

    for name in frame.columns:
        series = frame[name]
        kind = _kind(series)
        profile = _profile_column(series, kind)
        columns.append(profile)

        if kind == "number":
            numeric_summary.append({"column": str(name), **profile.stats})
            numeric_frames[str(name)] = pd.to_numeric(series, errors="coerce")

    correlation: CorrelationMatrix | None = None
    if len(numeric_frames) >= 2:
        selected = list(numeric_frames)[:15]
        matrix = pd.DataFrame({name: numeric_frames[name] for name in selected}).corr()
        correlation = CorrelationMatrix(
            columns=selected,
            values=[
                [None if pd.isna(value) else round(float(value), 3) for value in row]
                for row in matrix.to_numpy()
            ],
        )

    return ProfileResponse(
        dataset_id=dataset_id,
        resource=resource,
        source=source,
        rows_analyzed=len(frame),
        truncated=truncated,
        columns=columns,
        numeric_summary=numeric_summary,
        correlation=correlation,
        warnings=warnings,
    )
