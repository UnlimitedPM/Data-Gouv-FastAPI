"""Graphiques Plotly reutilisables et generation automatique de figures."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BLUE = "#000091"
BLUE_LIGHT = "#1212ff"
RED = "#e1000f"
GREEN = "#18753c"
MUTED = "#6a6af4"
PALETTE = ["#000091", "#1212ff", "#6a6af4", "#e1000f", "#18753c", "#b34000", "#8a5cf6", "#009099"]
FONT_FAMILY = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"


def apply_theme(fig: go.Figure, height: int = 340) -> go.Figure:
    """Applique le theme visuel commun."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin={"l": 8, "r": 16, "t": 44, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT_FAMILY, "size": 12, "color": "#161616"},
        title={"font": {"size": 14, "color": "#161616"}, "x": 0.01, "xanchor": "left"},
        legend={"orientation": "h", "y": -0.18, "x": 0},
        colorway=PALETTE,
        hoverlabel={"font": {"family": FONT_FAMILY, "size": 12}},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#ededf9", zeroline=False)
    return fig


# --------------------------------------------------------------------------- #
# Facettes
# --------------------------------------------------------------------------- #
def bar_facets(
    facets: list[dict[str, Any]],
    title: str,
    *,
    color: str = BLUE,
    limit: int = 10,
    height: int = 340,
    unit: str = "jeux de données",
) -> go.Figure | None:
    rows = [(item.get("name") or "?", item.get("count") or 0) for item in facets][:limit]
    rows = [(name, count) for name, count in rows if count]
    if not rows:
        return None

    frame = pd.DataFrame(rows, columns=["name", "count"]).sort_values("count")
    fig = px.bar(
        frame,
        x="count",
        y="name",
        orientation="h",
        title=title,
        text="count",
        color_discrete_sequence=[color],
    )
    fig.update_traces(
        texttemplate="%{text:,.0f}".replace(",", " "),
        textposition="outside",
        cliponaxis=False,
        hovertemplate=f"%{{y}}<br>%{{x:,.0f}} {unit}<extra></extra>",
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False)
    fig.update_xaxes(showgrid=True, gridcolor="#f2f2fb")
    fig = apply_theme(fig, height)
    fig.update_layout(margin={"l": 8, "r": 72, "t": 44, "b": 8})
    return fig


def donut_facets(
    facets: list[dict[str, Any]],
    title: str,
    *,
    limit: int = 6,
    height: int = 340,
    labels: dict[str, str] | None = None,
) -> go.Figure | None:
    rows = [(item.get("name") or "?", item.get("count") or 0) for item in facets[:limit]]
    rows = [(name, count) for name, count in rows if count]
    if not rows:
        return None

    labels_map = labels or {}
    frame = pd.DataFrame(
        [(labels_map.get(name, name), count) for name, count in rows],
        columns=["name", "count"],
    )
    fig = px.pie(
        frame,
        names="name",
        values="count",
        title=title,
        hole=0.58,
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        hovertemplate="%{label}<br>%{value:,.0f} jeux de données (%{percent})<extra></extra>",
    )
    fig.update_layout(showlegend=True)
    return apply_theme(fig, height)


def topic_bar(
    facets: list[dict[str, Any]],
    title: str = "Thématiques les plus représentées",
    *,
    limit: int = 10,
    height: int = 360,
) -> go.Figure | None:
    rows = [item for item in facets[:limit] if item.get("count")]
    if not rows:
        return None

    frame = pd.DataFrame(
        [(item.get("name") or "?", item.get("count") or 0, item.get("color") or BLUE) for item in rows],
        columns=["name", "count", "color"],
    ).sort_values("count")
    fig = go.Figure(
        go.Bar(
            x=frame["count"],
            y=frame["name"],
            orientation="h",
            marker_color=frame["color"],
            text=frame["count"],
            texttemplate="%{text:,.0f}".replace(",", " "),
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:,.0f} jeux de données<extra></extra>",
        )
    )
    fig.update_layout(title=title, xaxis_title=None, yaxis_title=None, showlegend=False)
    fig.update_xaxes(showgrid=True, gridcolor="#f2f2fb")
    return apply_theme(fig, height)


# --------------------------------------------------------------------------- #
# Detection de colonnes
# --------------------------------------------------------------------------- #
def numeric_columns(frame: pd.DataFrame) -> list[str]:
    return [str(col) for col in frame.columns if pd.api.types.is_numeric_dtype(frame[col])]


def datetime_columns(frame: pd.DataFrame) -> list[str]:
    columns: list[str] = []
    for column in frame.columns:
        series = frame[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            columns.append(str(column))
            continue
        if series.dtype != object:
            continue
        sample = series.dropna().astype(str).head(200)
        if sample.empty:
            continue
        try:
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        except (TypeError, ValueError):
            parsed = pd.to_datetime(sample, errors="coerce")
        if parsed.notna().mean() >= 0.8:
            columns.append(str(column))
    return columns


def categorical_columns(frame: pd.DataFrame, max_cardinality: int = 40) -> list[str]:
    columns: list[str] = []
    for column in frame.columns:
        series = frame[column]
        if pd.api.types.is_bool_dtype(series) or series.dtype == object:
            unique = series.nunique(dropna=True)
            if 1 < unique <= max_cardinality:
                columns.append(str(column))
    return columns


# --------------------------------------------------------------------------- #
# Figures individuelles
# --------------------------------------------------------------------------- #
def histogram(frame: pd.DataFrame, column: str) -> go.Figure:
    fig = px.histogram(
        frame,
        x=column,
        nbins=30,
        title=f"Distribution — {column}",
        color_discrete_sequence=[BLUE],
    )
    fig.update_layout(xaxis_title=None, yaxis_title="Occurrences", showlegend=False, bargap=0.05)
    return apply_theme(fig)


def category_bar(frame: pd.DataFrame, column: str, limit: int = 15) -> go.Figure | None:
    counts = (
        frame[column]
        .astype("string")
        .fillna("(vide)")
        .value_counts()
        .head(limit)
    )
    if counts.empty:
        return None
    subset = counts.reset_index()
    subset.columns = ["value", "count"]
    subset = subset.sort_values("count")
    fig = px.bar(
        subset,
        x="count",
        y="value",
        orientation="h",
        title=f"Répartition — {column}",
        text="count",
        color_discrete_sequence=[MUTED],
    )
    fig.update_traces(
        texttemplate="%{text:,.0f}".replace(",", " "),
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x:,.0f} lignes<extra></extra>",
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False)
    return apply_theme(fig)


def date_series(frame: pd.DataFrame, column: str) -> go.Figure | None:
    parsed = pd.to_datetime(frame[column], errors="coerce")
    valid = parsed.dropna()
    if valid.empty:
        return None

    span_days = (valid.max() - valid.min()).days
    if span_days > 365 * 3:
        periods = parsed.dt.to_period("Y").astype("string")
        label = "par an"
    elif span_days > 120:
        periods = parsed.dt.to_period("M").astype("string")
        label = "par mois"
    elif span_days > 3:
        periods = parsed.dt.to_period("W").astype("string")
        label = "par semaine"
    else:
        periods = parsed.dt.to_period("D").astype("string")
        label = "par jour"

    counts = periods.value_counts().sort_index()
    counts = counts[counts.index.notna()]
    if counts.empty:
        return None

    subset = counts.reset_index()
    subset.columns = ["period", "count"]
    fig = px.line(
        subset,
        x="period",
        y="count",
        title=f"Évolution — {column} ({label})",
        markers=True,
        color_discrete_sequence=[GREEN],
    )
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.0f} lignes<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title="Lignes", showlegend=False)
    return apply_theme(fig)


def _looks_like_identifier(name: str) -> bool:
    normalized = name.strip().lower().replace(" ", "_")
    return bool(
        re.match(
            r"^(id|identifiant|code|siren|siret|insee|num|numero|reference|ref|cle|key)(_|$)",
            normalized,
        )
    )


GEO_LAT_HINTS = {"lat", "latitude", "ylat"}
GEO_LON_HINTS = {"lon", "lng", "long", "longitude", "xlon"}


def _name_tokens(name: object) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", str(name).lower()) if token}


def geographic_columns(frame: pd.DataFrame) -> tuple[str, str] | None:
    """Detecte une paire latitude/longitude exploitable pour une carte."""
    lat_column: str | None = None
    lon_column: str | None = None

    for column in frame.columns:
        tokens = _name_tokens(column)
        if lat_column is None and tokens & GEO_LAT_HINTS:
            lat_column = str(column)
        elif lon_column is None and tokens & GEO_LON_HINTS:
            lon_column = str(column)

    if not lat_column or not lon_column:
        return None

    lat_values = pd.to_numeric(frame[lat_column], errors="coerce")
    lon_values = pd.to_numeric(frame[lon_column], errors="coerce")
    valid = lat_values.between(-90, 90) & lon_values.between(-180, 180)
    if int(valid.sum()) < 2:
        return None

    return lat_column, lon_column


def map_figure(
    frame: pd.DataFrame,
    lat_column: str,
    lon_column: str,
    max_points: int = 5_000,
) -> go.Figure | None:
    """Carte de points a partir de colonnes latitude/longitude."""
    subset = pd.DataFrame(
        {
            lat_column: pd.to_numeric(frame[lat_column], errors="coerce"),
            lon_column: pd.to_numeric(frame[lon_column], errors="coerce"),
        }
    )
    subset = subset.dropna()
    subset = subset[
        subset[lat_column].between(-90, 90) & subset[lon_column].between(-180, 180)
    ]
    if subset.empty:
        return None
    subset = subset.head(max_points)

    hover_column = next(
        (
            column
            for column in categorical_columns(frame, max_cardinality=30)
            if column not in {lat_column, lon_column}
        ),
        None,
    )
    columns = [lat_column, lon_column] + ([hover_column] if hover_column else [])
    plot_frame = frame.loc[subset.index, columns].copy()

    figure = px.scatter_map(
        plot_frame,
        lat=lat_column,
        lon=lon_column,
        hover_name=hover_column,
        center={
            "lat": float(subset[lat_column].mean()),
            "lon": float(subset[lon_column].mean()),
        },
        zoom=4,
        map_style="open-street-map",
        height=520,
        opacity=0.75,
        color_discrete_sequence=[BLUE],
        title=f"Carte — {len(subset):,} points géolocalisés".replace(",", " "),
    )
    figure.update_layout(margin={"l": 0, "r": 0, "t": 44, "b": 0})
    return figure


def _geojson_first_geometry_type(features: list[dict[str, Any]]) -> str:
    for feature in features:
        geometry = feature.get("geometry")
        if isinstance(geometry, dict) and geometry.get("type"):
            return str(geometry["type"])
    return ""


def geojson_point_frame(features: list[dict[str, Any]]) -> pd.DataFrame:
    """Extrait un point par entite pour les GeoJSON de type Point/MultiPoint."""
    rows: list[dict[str, Any]] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates") or []
        if geometry_type == "Point":
            points = [coordinates]
        elif geometry_type == "MultiPoint":
            points = coordinates
        else:
            points = coordinates[:1]

        properties = feature.get("properties") or {}
        for point in points:
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                continue
            longitude, latitude = point[0], point[1]
            if not isinstance(longitude, (int, float)) or not isinstance(
                latitude, (int, float)
            ):
                continue
            rows.append(
                {
                    "id": feature.get("id"),
                    "lat": float(latitude),
                    "lon": float(longitude),
                    **properties,
                }
            )
    return pd.DataFrame(rows)


def geojson_choropleth(
    geojson: dict[str, Any],
    properties: list[str],
    color_property: str | None = None,
    center: dict[str, float] | None = None,
    zoom: int = 5,
) -> go.Figure | None:
    """Carte choroplethe a partir d'une FeatureCollection GeoJSON."""
    features = geojson.get("features") or []
    if not features:
        return None

    if _geojson_first_geometry_type(features) in {"Point", "MultiPoint"}:
        plot_frame = geojson_point_frame(features)
        if plot_frame.empty:
            return None
        color_column = color_property if color_property in plot_frame.columns else None
        color_is_numeric = bool(
            color_column and pd.api.types.is_numeric_dtype(plot_frame[color_column])
        )
        figure = px.scatter_map(
            plot_frame,
            lat="lat",
            lon="lon",
            color=color_column,
            hover_name="id",
            hover_data=[column for column in properties[:6] if column in plot_frame.columns],
            center=center,
            zoom=zoom,
            map_style="open-street-map",
            height=520,
            opacity=0.8,
            color_continuous_scale="YlGnBu" if color_is_numeric else None,
            color_discrete_sequence=(
                PALETTE if color_column and not color_is_numeric else None if color_column else [BLUE]
            ),
            title=f"Carte GeoJSON — {len(plot_frame):,} points".replace(",", " "),
        )
    else:
        plot_frame = pd.DataFrame(
            [
                {"id": feature.get("id"), **(feature.get("properties") or {})}
                for feature in features
            ]
        )
        color_column = color_property if color_property in plot_frame.columns else None
        color_is_numeric = bool(
            color_column and pd.api.types.is_numeric_dtype(plot_frame[color_column])
        )
        figure = px.choropleth_map(
            plot_frame,
            geojson=geojson,
            locations="id",
            featureidkey="id",
            color=color_column,
            hover_name="id",
            hover_data=[column for column in properties[:6] if column in plot_frame.columns],
            center=center,
            zoom=zoom,
            map_style="open-street-map",
            height=520,
            opacity=0.65,
            color_continuous_scale="YlGnBu" if color_is_numeric else None,
            color_discrete_sequence=(
                PALETTE if color_column and not color_is_numeric else None if color_column else [BLUE]
            ),
            title=f"Carte GeoJSON — {len(features):,} objets".replace(",", " "),
        )

    figure.update_layout(margin={"l": 0, "r": 0, "t": 44, "b": 0})
    return figure


def auto_figures(frame: pd.DataFrame, max_figures: int = 6) -> list[go.Figure]:
    """Genere une selection de figures pertinentes pour un DataFrame."""
    if frame.empty:
        return []

    figures: list[go.Figure] = []
    dates = datetime_columns(frame)
    numbers = numeric_columns(frame)
    categories = [col for col in categorical_columns(frame) if col not in dates]

    for column in dates[:2]:
        figure = date_series(frame, column)
        if figure is not None:
            figures.append(figure)

    informative_numbers = [
        column
        for column in numbers
        if not _looks_like_identifier(column)
        and (len(frame) < 10 or frame[column].nunique(dropna=True) >= 3)
    ]
    for column in (informative_numbers or numbers)[:3]:
        figures.append(histogram(frame, column))

    for column in categories[:3]:
        figure = category_bar(frame, column)
        if figure is not None:
            figures.append(figure)

    return figures[:max_figures]


# --------------------------------------------------------------------------- #
# Graphiques personnalises
# --------------------------------------------------------------------------- #
def correlation_heatmap(columns: list[str], values: list[list[float | None]]) -> go.Figure:
    fig = go.Figure(
        go.Heatmap(
            z=values,
            x=columns,
            y=columns,
            zmin=-1,
            zmax=1,
            colorscale="RdBu",
            colorbar={"title": "r"},
            hovertemplate="%{y} × %{x}<br>r = %{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(title="Corrélations entre colonnes numériques")
    fig.update_yaxes(autorange="reversed")
    return apply_theme(fig, height=max(340, 46 * len(columns)))


def build_custom_figure(
    frame: pd.DataFrame,
    kind: str,
    x: str,
    y: str | None = None,
    color: str | None = None,
) -> go.Figure | None:
    """Construit un graphique a partir des choix de l'utilisateur."""
    plot_frame = frame.head(5_000)

    if kind == "Histogramme":
        return histogram(plot_frame, x)

    if kind == "Barres (comptage)":
        return category_bar(plot_frame, x)

    if kind == "Nuage de points":
        fig = px.scatter(
            plot_frame.sample(min(len(plot_frame), 3_000), random_state=0),
            x=x,
            y=y,
            color=color,
            title=f"{x} × {y}",
            color_discrete_sequence=PALETTE,
            opacity=0.75,
        )
        fig.update_layout(xaxis_title=x, yaxis_title=y)
        return apply_theme(fig, height=420)

    if kind == "Ligne":
        ordered = plot_frame.sort_values(x)
        fig = px.line(
            ordered,
            x=x,
            y=y,
            color=color,
            title=f"{x} → {y}",
            color_discrete_sequence=PALETTE,
        )
        fig.update_layout(xaxis_title=x, yaxis_title=y)
        return apply_theme(fig, height=420)

    if kind == "Boîte à moustaches":
        fig = px.box(
            plot_frame,
            x=color or x,
            y=y,
            title=f"{y} par {color or x}",
            color_discrete_sequence=PALETTE,
        )
        fig.update_layout(xaxis_title=None, yaxis_title=y)
        return apply_theme(fig, height=420)

    if kind == "Barres":
        grouped = (
            plot_frame.groupby(x, dropna=False)[y]
            .sum()
            .sort_values(ascending=False)
            .head(20)
            .reset_index()
        )
        fig = px.bar(
            grouped,
            x=x,
            y=y,
            title=f"{y} par {x}",
            color_discrete_sequence=[BLUE],
        )
        fig.update_layout(xaxis_title=x, yaxis_title=y)
        return apply_theme(fig, height=420)

    return None
