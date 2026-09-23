"""Reporte del viento de Sarallenque: cambio de régimen de 2025-07-14 frente a sus vecinas.

Uso (desde explorar_qaqc/):
    uv run python sarallenque_wind/build_report.py

Salida: sarallenque_wind/reporte_viento_sarallenque.html, autocontenido salvo plotly.js (CDN):
fotos y fondos del mapa van incrustados.

Datos: meteorología horaria de la base (solo lectura) con el QC de met_viewer. Relieve: SRTM 30 m
(OpenTopoData), guardado en dem_cache.json. Fondos del mapa: teselas de OpenTopoMap y Esri,
descargadas una vez a tiles_cache/.
"""
from __future__ import annotations

import base64
import html
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "met_viewer"))
import data  # noqa: E402
import qc  # noqa: E402
from stations import STATIONS, sensor_at  # noqa: E402

OUTPUT = HERE / "reporte_viento_sarallenque.html"
DEM_CACHE = HERE / "dem_cache.json"

TARGET = "Sarallenque"
REFERENCES = ["Altarani", "Alto_Quellaveco", "Sarallenque_MQG-15-02", "Mina_Norte"]
STATIONS_SHOWN = [TARGET] + REFERENCES

CHANGE = pd.Timestamp("2025-07-14")
# Antes: el año previo al cambio. Después: desde que el régimen nuevo se estabiliza; la
# transición (2025-07-14 → 2025-10-31) queda fuera de las rosas pero sí sale en la serie semanal.
PERIODS = {
    "antes": (pd.Timestamp("2024-07-14"), CHANGE),
    "después": (pd.Timestamp("2025-11-01"), pd.Timestamp("2026-09-23")),
}
DAY_HOURS = list(range(10, 18))                  # 10:00–17:59
NIGHT_HOURS = [22, 23, 0, 1, 2, 3, 4, 5, 6]      # 22:00–06:59
SHIFTS = {"día": DAY_HOURS, "noche": NIGHT_HOURS}
SECTORS = 16
SPEED_BINS = [0.5, 2, 4, 6, np.inf]
SPEED_LABELS = ["0.5–2 m/s", "2–4 m/s", "4–6 m/s", "≥ 6 m/s"]

# Foto de Mina_Norte del 2026-09-01: posible ubicación nueva del shelter (sin confirmar).
MINA_NORTE_PHOTO = (326497.0, 8110200.0)

# Paleta de referencia (skill dataviz): rampa azul ordinal para la velocidad, slots categóricos
# 1-2 para noche/día (validados en todos los pares), tinta y superficies.
SPEED_COLORS = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
DAY_COLOR, NIGHT_COLOR = "#eb6834", "#2a78d6"
INK, INK_2, MUTED, GRID, BASELINE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SURFACE, PAGE = "#fcfcfb", "#f9f9f7"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

TO_GEO = Transformer.from_crs(32719, 4326, always_xy=True)


# ── datos ────────────────────────────────────────────────────────────────────

def load_wind() -> dict[str, pd.DataFrame]:
    """Viento horario con QC de las estaciones del reporte, de 2024-07-14 a hoy."""
    start, end = pd.Timestamp("2024-07-14"), pd.Timestamp("2026-09-23")
    clean, _, _ = qc.apply_qc(data.load(start - pd.Timedelta(days=2), end))
    out = {}
    for est in STATIONS_SHOWN:
        df = clean[est][[data.WS, data.WD]].dropna()
        out[est] = df[(df.index >= start) & (df.index < end)]
    return out


def vector_components(df: pd.DataFrame) -> pd.DataFrame:
    """Componentes del vector de procedencia; las calmas no aportan dirección."""
    rad = np.deg2rad(df[data.WD])
    ws = df[data.WS].where(df[data.WS] >= qc.CALM_WS, 0.0)
    return pd.DataFrame({"u": ws * np.sin(rad), "v": ws * np.cos(rad), "ws": df[data.WS]})


def vector_direction(uv: pd.DataFrame) -> float:
    return float(np.rad2deg(np.arctan2(uv.u.mean(), uv.v.mean())) % 360)


def select(df: pd.DataFrame, period: str, shift: str) -> pd.DataFrame:
    a, b = PERIODS[period]
    df = df[(df.index >= a) & (df.index < b)]
    return df[df.index.hour.isin(SHIFTS[shift])]


def rose_table(df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    """Frecuencia (% de todas las horas de la franja) por sector y clase de velocidad, y % de calma."""
    n = len(df)
    windy = df[df[data.WS] >= qc.CALM_WS]
    width = 360 / SECTORS
    sector = ((windy[data.WD] + width / 2) % 360 // width).astype(int)
    speed = pd.cut(windy[data.WS], SPEED_BINS, labels=SPEED_LABELS, right=False)
    table = pd.crosstab(sector, speed).reindex(index=range(SECTORS), columns=SPEED_LABELS, fill_value=0)
    return table / n * 100, (1 - len(windy) / n) * 100


def summary(wind: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for est in STATIONS_SHOWN:
        for period in PERIODS:
            row = {"estación": est, "periodo": period}
            for shift in SHIFTS:
                sel = select(wind[est], period, shift)
                row[f"dir {shift}"] = vector_direction(vector_components(sel)) if len(sel) else np.nan
                row[f"vel {shift}"] = sel[data.WS].mean() if len(sel) else np.nan
                row[f"horas {shift}"] = len(sel)
            rows.append(row)
    return pd.DataFrame(rows)


def weekly(wind: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Dirección vectorial nocturna y velocidad media por semana."""
    dirs, speeds = {}, {}
    for est, df in wind.items():
        night = df[df.index.hour.isin(NIGHT_HOURS)]
        uv = vector_components(night)
        g = uv.groupby(pd.Grouper(freq="W-MON", label="left", closed="left"))
        d = pd.Series({k: vector_direction(x) for k, x in g if len(x) >= 24})
        dirs[est] = d
        speeds[est] = df[data.WS].resample("W-MON", label="left", closed="left").mean()
    return pd.DataFrame(dirs), pd.DataFrame(speeds)


# ── relieve ──────────────────────────────────────────────────────────────────

RADII = (90, 180, 360, 720, 1500)
AZIMUTHS = list(range(0, 360, 45))


def terrain(sites: dict[str, tuple[float, float]]) -> dict[str, dict]:
    """Anillos de SRTM alrededor de cada sitio y plano ajustado a 90–360 m (cacheado)."""
    cache = json.loads(DEM_CACHE.read_text(encoding="utf-8")) if DEM_CACHE.exists() else {}
    for name, (x0, y0) in sites.items():
        if name in cache:
            continue
        pts = [(x0, y0)] + [(x0 + r * np.sin(np.deg2rad(a)), y0 + r * np.cos(np.deg2rad(a)))
                            for r in RADII for a in AZIMUTHS]
        locs = "|".join(f"{lat:.6f},{lon:.6f}" for lon, lat in (TO_GEO.transform(x, y) for x, y in pts))
        url = "https://api.opentopodata.org/v1/srtm30m?locations=" + locs
        res = json.load(urllib.request.urlopen(url, timeout=60))["results"]
        z = [r["elevation"] for r in res]
        cache[name] = {"x": x0, "y": y0, "z": z}
        time.sleep(1.1)
    DEM_CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")

    out = {}
    for name in sites:
        c = cache[name]
        z = np.array(c["z"])
        rings = z[1:].reshape(len(RADII), len(AZIMUTHS)) - z[0]
        near = 3 * len(AZIMUTHS)
        offsets = np.array([(r * np.sin(np.deg2rad(a)), r * np.cos(np.deg2rad(a)))
                            for r in RADII[:3] for a in AZIMUTHS])
        gx, gy = np.linalg.lstsq(np.c_[offsets, np.ones(near)], z[1:1 + near], rcond=None)[0][:2]
        out[name] = {
            "z": float(z[0]),
            "slope": float(np.rad2deg(np.arctan(np.hypot(gx, gy)))),
            "uphill": float(np.rad2deg(np.arctan2(gx, gy)) % 360),
            "rings": rings,
            "tpi_360": float(rings[2].mean()),
            "tpi_1500": float(rings[4].mean()),
        }
    return out


# ── figuras ──────────────────────────────────────────────────────────────────

def _base_layout(fig: go.Figure, height: int) -> None:
    fig.update_layout(height=height, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                      font=dict(family=FONT, size=12, color=INK_2), margin=dict(l=50, r=20, t=40, b=40))


def rose_grid(wind: dict[str, pd.DataFrame]) -> go.Figure:
    """Rosas por estación (filas) y por franja y periodo (columnas).

    Escala radial común dentro de cada estación (sus cuatro rosas se comparan entre sí); entre
    estaciones cambia, porque una escala única la fijaba Altarani y aplastaba al resto.
    """
    cols = [("día", "antes"), ("día", "después"), ("noche", "antes"), ("noche", "después")]
    tables = {(e, s, p): rose_table(select(wind[e], p, s)) for e in STATIONS_SHOWN for s, p in cols}
    rmax = {e: max(tables[(e, s, p)][0].sum(axis=1).max() for s, p in cols) * 1.05 for e in STATIONS_SHOWN}
    fig = make_subplots(rows=len(STATIONS_SHOWN), cols=4, specs=[[{"type": "polar"}] * 4] * len(STATIONS_SHOWN),
                        subplot_titles=[f"{e} · {s} {p}" for e in STATIONS_SHOWN for s, p in cols],
                        horizontal_spacing=0.06, vertical_spacing=0.045)
    theta = np.arange(SECTORS) * 360 / SECTORS
    for i, est in enumerate(STATIONS_SHOWN, 1):
        for j, (shift, period) in enumerate(cols, 1):
            table, calm = tables[(est, shift, period)]
            n = len(select(wind[est], period, shift))
            for k, label in enumerate(SPEED_LABELS):
                fig.add_trace(go.Barpolar(
                    r=table[label].round(2), theta=theta, name=label, marker_color=SPEED_COLORS[k],
                    marker_line=dict(color=SURFACE, width=1), legendgroup=label, showlegend=(i == 1 and j == 1),
                    hovertemplate=f"{est} · {shift} {period}<br>desde %{{theta}}°<br>{label}: %{{r:.1f}} %<extra></extra>"),
                    row=i, col=j)
            idx = (i - 1) * 4 + j
            fig.layout.annotations[idx - 1].text += f"<br><span style='font-size:10px;color:{MUTED}'>{n} h · calma {calm:.0f} %</span>"
    polar_style = dict(
        bgcolor=SURFACE,
        angularaxis=dict(direction="clockwise", rotation=90, tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                         ticktext=["N", "NE", "E", "SE", "S", "SO", "O", "NO"], gridcolor=GRID,
                         linecolor=BASELINE, tickfont=dict(size=9, color=MUTED)),
        radialaxis=dict(gridcolor=GRID, showline=False, tickfont=dict(size=8, color=MUTED), nticks=4,
                        ticksuffix=" %", angle=45, tickangle=45),
        barmode="stack",
    )
    fig.update_polars(**polar_style)
    for i, est in enumerate(STATIONS_SHOWN):
        for j in range(4):
            n = i * 4 + j + 1
            fig.layout[f"polar{n if n > 1 else ''}"].radialaxis.range = [0, rmax[est]]
    for a in fig.layout.annotations:
        a.font = dict(size=11, color=INK)
        a.yshift = 14
    _base_layout(fig, 300 * len(STATIONS_SHOWN))
    fig.update_layout(legend=dict(orientation="h", y=1.05, x=0, yanchor="bottom", title_text="Velocidad "),
                      margin=dict(t=140))
    return fig


TO_MERC = Transformer.from_crs(32719, 3857, always_xy=True)
TILE_ZOOM = 14
TILE_CACHE = HERE / "tiles_cache"
MERC_R = 20037508.342789244
BASEMAPS = {
    "Topográfico": ("https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
                    "Mapa: © OpenTopoMap (CC-BY-SA), © colaboradores de OpenStreetMap"),
    "Satélite": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                 "Imagen: Esri World Imagery"),
}


def _merc(x, y):
    """UTM 19S → Web Mercator (m), el sistema de las teselas."""
    return TO_MERC.transform(x, y)


def _basemap(name: str, bbox: tuple[float, float, float, float]) -> dict:
    """Une las teselas que cubren bbox (Web Mercator) en una imagen JPEG incrustable.

    Las teselas se guardan en tiles_cache/ para no volver a descargarlas.
    """
    from io import BytesIO
    from PIL import Image

    url, _ = BASEMAPS[name]
    size = 2 * MERC_R / 2 ** TILE_ZOOM
    xmin, ymin, xmax, ymax = bbox
    tx0, tx1 = int((xmin + MERC_R) // size), int((xmax + MERC_R) // size)
    ty0, ty1 = int((MERC_R - ymax) // size), int((MERC_R - ymin) // size)
    mosaic = Image.new("RGB", (256 * (tx1 - tx0 + 1), 256 * (ty1 - ty0 + 1)))
    folder = TILE_CACHE / {"Topográfico": "topo", "Satélite": "satellite"}[name]
    folder.mkdir(parents=True, exist_ok=True)
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            f = folder / f"{TILE_ZOOM}_{tx}_{ty}.img"
            if not f.exists():
                req = urllib.request.Request(url.format(z=TILE_ZOOM, x=tx, y=ty),
                                             headers={"User-Agent": "explorar-qaqc-reporte/1.0"})
                f.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                time.sleep(0.3)
            tile = Image.open(f).convert("RGB").resize((256, 256))
            mosaic.paste(tile, (256 * (tx - tx0), 256 * (ty - ty0)))
    buf = BytesIO()
    mosaic.save(buf, format="JPEG", quality=82)
    return dict(source="data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
                xref="x", yref="y", x=-MERC_R + tx0 * size, y=MERC_R - ty0 * size,
                sizex=(tx1 - tx0 + 1) * size, sizey=(ty1 - ty0 + 1) * size,
                sizing="stretch", layer="below", opacity=1.0)


def _wedges(x0: float, y0: float, freq: np.ndarray, scale: float) -> tuple[list, list]:
    """Contorno de una rosa (una cuña por sector, radio ∝ √frecuencia) en Web Mercator."""
    xs, ys, width = [], [], 360 / SECTORS
    for k, f in enumerate(freq):
        r = scale * np.sqrt(f)
        arc = np.deg2rad(np.linspace(k * width - width / 2, k * width + width / 2, 6))
        xs += [x0] + list(x0 + r * np.sin(arc)) + [x0]
        ys += [y0] + list(y0 + r * np.cos(arc)) + [y0]
    mx, my = _merc(np.array(xs), np.array(ys))
    return list(mx), list(my)


def rose_map(wind: dict[str, pd.DataFrame], relief: dict[str, dict]) -> go.Figure:
    """Mapa con las rosas de día y de noche en cada estación; botones antes/después y fondo.

    Es un gráfico cartesiano en Web Mercator con las teselas incrustadas como imagen de fondo:
    no depende de WebGL ni de cargar teselas al abrir el HTML.
    """
    fig = go.Figure()
    freqs = {(e, s, p): rose_table(select(wind[e], p, s))[0].sum(axis=1).to_numpy()
             for e in STATIONS_SHOWN for s in SHIFTS for p in PERIODS}
    scale = 850 / np.sqrt(max(f.max() for f in freqs.values()))    # pétalo mayor = 850 m
    period_of_trace = []
    for period in PERIODS:
        for shift, color in (("noche", NIGHT_COLOR), ("día", DAY_COLOR)):
            for n, est in enumerate(STATIONS_SHOWN):
                s = STATIONS[est]
                mx, my = _wedges(s.easting, s.northing, freqs[(est, shift, period)], scale)
                fig.add_trace(go.Scatter(
                    x=mx, y=my, mode="lines", fill="toself", name=shift.capitalize(),
                    legendgroup=shift, showlegend=(n == 0), line=dict(color=color, width=1.5),
                    fillcolor=_rgba(color, 0.4), hoverinfo="skip", visible=(period == "antes")))
                period_of_trace.append(period)

    # estaciones
    pts = {est: (STATIONS[est].easting, STATIONS[est].northing) for est in STATIONS_SHOWN}
    pts["Mina_Norte (foto 2026-09-01)"] = MINA_NORTE_PHOTO
    hover = []
    for est in pts:
        if est in relief:
            sen = sensor_at(est, "viento", "2026-09-22")
            altura = sen.height_m or {"torre": 10, "climavue": 2}.get(sen.kind, 2)
            hover.append(f"<b>{est}</b><br>{sen.kind} ~{altura:g} m<br>z {relief[est]['z']:.0f} m · "
                         f"pendiente {relief[est]['slope']:.0f}°, sube hacia {relief[est]['uphill']:.0f}°")
        else:
            hover.append(f"<b>{est}</b><br>GPS de la foto del shelter; a 782 m de la coordenada del KMZ")
    mx, my = _merc(np.array([p[0] for p in pts.values()]), np.array([p[1] for p in pts.values()]))
    fig.add_trace(go.Scatter(
        x=mx, y=my, mode="markers", hovertext=hover, hoverinfo="text", showlegend=False,
        marker=dict(size=[11] * len(STATIONS_SHOWN) + [9], symbol=["circle"] * len(STATIONS_SHOWN) + ["circle-open"],
                    color=[INK] * len(STATIONS_SHOWN) + [INK], line=dict(color=SURFACE, width=2))))
    period_of_trace.append(None)
    # entrada de leyenda para las flechas (las flechas son anotaciones)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=INK, width=2.5),
                             name="Sube el<br>terreno (DEM)"))
    period_of_trace.append(None)

    # encuadre: todas las estaciones con 1 km de margen
    ux, uy = [p[0] for p in pts.values()], [p[1] for p in pts.values()]
    (x0, y0), (x1, y1) = _merc(min(ux) - 1000, min(uy) - 1000), _merc(max(ux) + 1000, max(uy) + 1000)
    bbox = (x0, y0, x1, y1)
    images = [_basemap(name, bbox) | {"visible": k == 0} for k, name in enumerate(BASEMAPS)]

    annotations = [dict(text=BASEMAPS["Topográfico"][1], x=1, y=0, xref="paper", yref="paper", xanchor="right",
                        yanchor="bottom", showarrow=False, font=dict(size=10, color=INK_2),
                        bgcolor="rgba(252,252,251,0.85)")]
    for est in STATIONS_SHOWN:                    # flecha de 450 m hacia donde sube el terreno
        s, up = STATIONS[est], np.deg2rad(relief[est]["uphill"])
        sx, sy = _merc(s.easting, s.northing)
        ex, ey = _merc(s.easting + 450 * np.sin(up), s.northing + 450 * np.cos(up))
        annotations.append(dict(x=ex, y=ey, ax=sx, ay=sy, xref="x", yref="y", axref="x", ayref="y", text="",
                                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2.5, arrowcolor=INK))
    for (est, _), lx, ly in zip(pts.items(), mx, my):  # etiquetas con fondo, legibles sobre el mapa
        photo = est not in relief
        annotations.append(dict(x=lx, y=ly, text=f"<b>{est}</b>", showarrow=False, font=dict(size=12, color=INK),
                                bgcolor="rgba(252,252,251,0.85)", borderpad=2,
                                xanchor="right" if photo else "center", yanchor="top" if not photo else "middle",
                                xshift=-9 if photo else 0, yshift=0 if photo else -9))
    # barra de escala de 1 km y norte
    bx, by = _merc(min(ux) - 700, min(uy) - 700)
    bx2, _ = _merc(min(ux) + 300, min(uy) - 700)
    shapes = [dict(type="line", x0=bx, x1=bx2, y0=by, y1=by, line=dict(color=INK, width=3), layer="above")]
    annotations.append(dict(x=(bx + bx2) / 2, y=by, text="1 km", showarrow=False, yshift=10,
                            font=dict(size=12, color=INK), bgcolor="rgba(252,252,251,0.85)"))
    nx, ny = _merc(max(ux) + 700, max(uy) + 300)
    _, ny2 = _merc(max(ux) + 700, max(uy) + 800)
    annotations.append(dict(x=nx, y=ny2, ax=nx, ay=ny, xref="x", yref="y", axref="x", ayref="y", text="<b>N</b>",
                            showarrow=True, arrowhead=2, arrowwidth=2.5, arrowcolor=INK, font=dict(size=14, color=INK),
                            yanchor="bottom", bgcolor="rgba(252,252,251,0.85)"))

    def visible(period: str) -> list[bool]:
        return [p is None or p == period for p in period_of_trace]

    button_style = dict(type="buttons", direction="right", yanchor="bottom", y=1.01, bgcolor=SURFACE,
                        bordercolor=MUTED, font=dict(size=12, color=INK), showactive=True, pad=dict(t=0, b=4))
    fig.update_layout(
        height=820, margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK_2), images=images, shapes=shapes, annotations=annotations,
        xaxis=dict(visible=False, range=[x0, x1], fixedrange=False),
        yaxis=dict(visible=False, range=[y0, y1], scaleanchor="x", scaleratio=1),
        legend=dict(x=0, y=0.5, xanchor="left", yanchor="middle", bgcolor="rgba(252,252,251,0.9)",
                    bordercolor=GRID, borderwidth=1, font=dict(size=12, color=INK)),
        hoverlabel=dict(bgcolor=SURFACE, font=dict(color=INK)),
        updatemenus=[
            button_style | dict(x=0, xanchor="left", buttons=[
                dict(label=f"{p.capitalize()} ({PERIODS[p][0]:%Y-%m-%d} → "
                           f"{PERIODS[p][1] - pd.Timedelta(days=1):%Y-%m-%d})",
                     method="restyle", args=[{"visible": visible(p)}]) for p in PERIODS]),
            button_style | dict(x=1, xanchor="right", buttons=[
                dict(label=name, method="relayout",
                     args=[{**{f"images[{j}].visible": j == k for j in range(len(BASEMAPS))},
                            "annotations[0].text": BASEMAPS[name][1]}])
                for k, name in enumerate(BASEMAPS)]),
        ],
    )
    return fig


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def weekly_figures(dirs: pd.DataFrame, speeds: pd.DataFrame) -> tuple[go.Figure, go.Figure]:
    """Serie semanal: Sarallenque destacada, vecinas en gris."""
    figs = []
    for frame, title, ytitle, mode in ((dirs, "Dirección nocturna semanal (media vectorial, 22–06 h)", "desde (°)", "markers"),
                                       (speeds, "Velocidad media semanal", "m/s", "lines")):
        fig = go.Figure()
        for est in REFERENCES:
            fig.add_trace(go.Scatter(x=frame.index, y=frame[est].round(2), name=est, mode=mode,
                                     line=dict(color=BASELINE, width=1.5), marker=dict(color=BASELINE, size=6),
                                     hovertemplate=f"{est}<br>%{{x|%Y-%m-%d}}: %{{y}}<extra></extra>"))
        fig.add_trace(go.Scatter(x=frame.index, y=frame[TARGET].round(2), name=TARGET, mode=mode,
                                 line=dict(color=INK, width=2.5), marker=dict(color=INK, size=8),
                                 hovertemplate=f"{TARGET}<br>%{{x|%Y-%m-%d}}: %{{y}}<extra></extra>"))
        fig.add_vline(x=CHANGE, line=dict(color=INK, width=1, dash="dot"))
        fig.add_vrect(x0=CHANGE, x1=PERIODS["después"][0], fillcolor=GRID, opacity=0.5, line_width=0)
        fig.add_annotation(x=CHANGE, y=1, yref="paper", text="2025-07-14", showarrow=False, xanchor="right",
                           yanchor="bottom", font=dict(size=11, color=INK))
        _base_layout(fig, 340)
        fig.update_layout(title=dict(text=title, x=0.01, font=dict(size=15, color=INK)), hovermode="closest",
                          legend=dict(orientation="h", y=-0.18),
                          xaxis=dict(gridcolor=GRID, linecolor=BASELINE, tickfont=dict(color=MUTED)),
                          yaxis=dict(title=ytitle, gridcolor=GRID, linecolor=BASELINE, tickfont=dict(color=MUTED),
                                     zeroline=False))
        if frame is dirs:
            fig.update_yaxes(range=[0, 360], tickvals=[0, 90, 180, 270, 360], ticktext=["N 0", "E 90", "S 180", "O 270", "N 360"])
        figs.append(fig)
    return figs[0], figs[1]


# ── HTML ─────────────────────────────────────────────────────────────────────

def _img(path: Path, caption: str) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode()
    return (f'<figure><img src="data:image/jpeg;base64,{b64}" alt="{html.escape(caption)}">'
            f"<figcaption>{html.escape(caption)}</figcaption></figure>")


def _fmt_dir(v: float) -> str:
    if pd.isna(v):
        return "—"
    names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]
    return f"{v:.0f}° {names[int((v + 11.25) % 360 // 22.5)]}"


def summary_table(summ: pd.DataFrame, relief: dict[str, dict]) -> str:
    head = ("<tr><th>Estación</th><th>Terreno sube hacia</th><th>Esperado día / noche</th><th>Periodo</th>"
            "<th>Día: desde</th><th>Noche: desde</th><th>Vel. día</th><th>Vel. noche</th><th>Horas día / noche</th></tr>")
    rows = []
    for est in STATIONS_SHOWN:
        up = relief[est]["uphill"]
        sub = summ[summ["estación"] == est]
        for k, (_, r) in enumerate(sub.iterrows()):
            first = (f'<td rowspan="{len(sub)}"><b>{html.escape(est)}</b></td>'
                     f'<td rowspan="{len(sub)}">{_fmt_dir(up)} ({relief[est]["slope"]:.0f}°)</td>'
                     f'<td rowspan="{len(sub)}">{_fmt_dir((up + 180) % 360)} / {_fmt_dir(up)}</td>') if k == 0 else ""
            rows.append(f"<tr>{first}<td>{r['periodo']}</td><td>{_fmt_dir(r['dir día'])}</td>"
                        f"<td>{_fmt_dir(r['dir noche'])}</td><td class='num'>{r['vel día']:.1f}</td>"
                        f"<td class='num'>{r['vel noche']:.1f}</td>"
                        f"<td class='num'>{r['horas día']} / {r['horas noche']}</td></tr>")
    return f'<table class="data">{head}{"".join(rows)}</table>'


def relief_table(relief: dict[str, dict]) -> str:
    head = "<tr><th>Sitio</th><th>Radio</th>" + "".join(
        f"<th>{n}</th>" for n in ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]) + "</tr>"
    rows = []
    for name, r in relief.items():
        for k, radius in enumerate(RADII):
            first = (f'<td rowspan="{len(RADII)}"><b>{html.escape(name)}</b><br>'
                     f'<span class="muted">z {r["z"]:.0f} m · sube {r["slope"]:.0f}° hacia {r["uphill"]:.0f}°<br>'
                     f'entorno a 1.5 km: {r["tpi_1500"]:+.0f} m</span></td>') if k == 0 else ""
            cells = "".join(f"<td class='num {'up' if v > 0 else 'down'}'>{v:+.0f}</td>" for v in r["rings"][k])
            rows.append(f"<tr>{first}<td class='num'>{radius} m</td>{cells}</tr>")
    return f'<table class="data">{head}{"".join(rows)}</table>'


class _Divs:
    def __init__(self) -> None:
        self.first = True

    def __call__(self, fig: go.Figure) -> str:
        out = pio.to_html(fig, full_html=False, include_plotlyjs="cdn" if self.first else False,
                          config={"displaylogo": False, "scrollZoom": True})
        self.first = False
        return out


def build() -> None:
    wind = load_wind()
    sites = {est: (STATIONS[est].easting, STATIONS[est].northing) for est in STATIONS_SHOWN}
    sites["Mina_Norte (foto)"] = MINA_NORTE_PHOTO
    relief = terrain(sites)
    summ = summary(wind)
    dirs, speeds = weekly(wind)

    s = summ.set_index(["estación", "periodo"])
    sar_b, sar_a = s.loc[(TARGET, "antes")], s.loc[(TARGET, "después")]
    print(summ.round(1).to_string())
    print({k: (round(v["slope"]), round(v["uphill"]), round(v["tpi_1500"])) for k, v in relief.items()})

    div = _Divs()
    fig_dir, fig_speed = weekly_figures(dirs, speeds)
    body = TEXT.format(
        change=f"{CHANGE:%Y-%m-%d}",
        antes=f"{PERIODS['antes'][0]:%Y-%m-%d} → {PERIODS['antes'][1] - pd.Timedelta(days=1):%Y-%m-%d}",
        despues=f"{PERIODS['después'][0]:%Y-%m-%d} → {PERIODS['después'][1] - pd.Timedelta(days=1):%Y-%m-%d}",
        sar_up=_fmt_dir(relief[TARGET]["uphill"]), sar_slope=f"{relief[TARGET]['slope']:.0f}",
        sar_day_b=_fmt_dir(sar_b["dir día"]), sar_night_b=_fmt_dir(sar_b["dir noche"]),
        sar_day_a=_fmt_dir(sar_a["dir día"]), sar_night_a=_fmt_dir(sar_a["dir noche"]),
        sar_vd_b=f"{sar_b['vel día']:.1f}", sar_vd_a=f"{sar_a['vel día']:.1f}",
        sar_vn_b=f"{sar_b['vel noche']:.1f}", sar_vn_a=f"{sar_a['vel noche']:.1f}",
        map=div(rose_map(wind, relief)),
        summary=summary_table(summ, relief),
        weekly_dir=div(fig_dir), weekly_speed=div(fig_speed),
        roses=div(rose_grid(wind)),
        relief=relief_table(relief),
        photo_f1=_img(HERE / "photos" / "sarallenque_shelter_f1.jpeg",
                      "Sarallenque, foto f1 (2026-05-09), mirando casi al norte: shelter inclinado, "
                      "enmallado a la derecha (este), quebrada al fondo."),
        photo_f2=_img(HERE / "photos" / "sarallenque_shelter_f2.jpeg",
                      "Sarallenque, foto f2 (2026-08-18), mirando casi al sur: enmallado a la izquierda (este), "
                      "talud cortado detrás, poste y torre de alta tensión. GPS 17.09854 S, 70.61307 W."),
        photo_mn=_img(HERE / "photos" / "minas_norte_shelter.jpeg",
                      "Mina_Norte (2026-09-01): Shelter 05 sobre remolque, ClimaVUE en mástil a 3.9–4.1 m. "
                      "GPS 326497 E, 8110200 N."),
    )
    OUTPUT.write_text(PAGE_HTML.format(body=body, generated=f"{pd.Timestamp.now():%Y-%m-%d %H:%M}"), encoding="utf-8")
    print(f"Reporte: {OUTPUT}")


PAGE_HTML = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Viento de Sarallenque</title>
<style>
 :root{{--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--surface:#fcfcfb;--page:#f9f9f7;--accent:#2a78d6}}
 body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--page);color:var(--ink);margin:0;line-height:1.5}}
 main{{max-width:1180px;margin:0 auto;padding:16px}}
 h1{{font-size:24px;margin:8px 0 4px}} h2{{font-size:19px;margin:28px 0 8px}} h3{{font-size:16px;margin:18px 0 6px}}
 p,li{{max-width:78ch}} .muted{{color:var(--muted);font-size:13px}}
 section{{background:var(--surface);border:1px solid rgba(11,11,11,.1);border-radius:8px;padding:12px 16px;margin:16px 0}}
 .lead{{font-size:16px;color:var(--ink2)}}
 table.data{{border-collapse:collapse;font-size:13px;margin:8px 0;width:100%}}
 table.data th,table.data td{{border-bottom:1px solid var(--grid);padding:4px 8px;text-align:left;vertical-align:top}}
 table.data th{{color:var(--ink2);font-weight:600}}
 td.num{{text-align:right;font-variant-numeric:tabular-nums}} td.up{{color:#8a4a1f}} td.down{{color:#1c5cab}}
 .tag{{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:10px;border:1px solid var(--muted);margin-right:6px}}
 .photos{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}}
 figure{{margin:0}} figure img{{width:100%;height:340px;object-fit:cover;border-radius:6px;border:1px solid var(--grid)}}
 figcaption{{font-size:12px;color:var(--ink2);margin-top:4px}}
 .scroll{{overflow-x:auto}}
</style></head><body><main>
{body}
<p class="muted">Generado el {generated} con sarallenque_wind/build_report.py.</p>
</main></body></html>"""


TEXT = """
<h1>Viento de Sarallenque: cambio de régimen desde el {change}</h1>
<p class="lead">Desde el {change}, la dirección y la velocidad del viento de Sarallenque cambian
<b>a la vez</b>. Antes, el viento seguía la ladera como el de sus vecinas; después, sopla casi al
revés. Sus vecinas no cambian en esas fechas. La causa más probable es un cambio en el montaje del
sensor: el shelter o el mástil se giraron, o el sensor se remontó. Hasta confirmarlo, la
dirección de Sarallenque desde el {change} no es fiable.</p>

<section>
<h2>1. Mapa: rosas de día y de noche en cada estación</h2>
<p>Cada rosa está dibujada en la posición de su estación. Los pétalos apuntan <b>hacia donde viene</b>
el viento y su radio es proporcional a la raíz de la frecuencia (el área, a la frecuencia). Naranja:
día (10–17 h). Azul: noche (22–06 h). La línea negra marca hacia dónde sube el terreno según el
DEM (plano ajustado entre 90 y 360 m). Con los botones se cambia entre <b>antes</b> ({antes}) y
<b>después</b> ({despues}), y entre el fondo topográfico y el satélite.</p>
<p class="muted">Lectura esperada en ladera: de día el aire sube la pendiente, así que el pétalo
naranja sale del lado contrario a la línea negra; de noche el aire baja, así que el pétalo azul
sale del mismo lado que la línea. Mina_Norte se dibuja en la coordenada del KMZ; su posible
ubicación nueva (foto del 2026-09-01) está en gris.</p>
{map}
</section>

<section>
<h2>2. Hallazgos verificados</h2>
<ol>
<li><b>El cambio es simultáneo en dirección y velocidad.</b> Antes: de día el viento venía de
{sar_day_b} y de noche de {sar_night_b}. Después: de día viene de {sar_day_a} y de noche de
{sar_night_a}. La velocidad media sube de {sar_vd_b} a {sar_vd_a} m/s de día y de {sar_vn_b} a
{sar_vn_a} m/s de noche. En la serie semanal (abajo), la dirección nocturna se sale de su rango
habitual la semana del {change}, deriva hasta octubre y se estabiliza desde noviembre de 2025.</li>
<li><b>Ninguna vecina cambia en julio de 2025.</b> Las dos más cercanas, Sarallenque_MQG-15-02
(2.2 km) y Altarani (2.7 km), mantienen su régimen con menos de 12° de diferencia entre periodos.
Lo de Sarallenque es local; no es un cambio regional ni estacional. Alto_Quellaveco y Mina_Norte
sí cambian, pero en otras fechas y por otros motivos (§4).</li>
<li><b>El sitio no se ha movido.</b> El GPS de la foto f2 (2026-08-18) cae a 11 m de la coordenada
de <code>stations.py</code>, que viene del KMZ.</li>
<li><b>El DEM confirma el relieve que se ve en las fotos.</b> El terreno sube hacia {sar_up} con
{sar_slope}° de pendiente y cae al S, al SO y al O (de −18 a −30 m a 90 m; de −91 a −144 m a
360 m). Al norte hay una quebrada: −17 m a 180 m y +244 m a 720 m, que es el acantilado del fondo
de la foto f1. Con celdas de 30 m, SRTM ve la subida hacia el este, pero no el enmallado ni el
talud de 10 m.</li>
<li><b>Las vecinas siguen su ladera.</b> En Altarani (fondo de valle abierto al NO, en los dos
periodos) y en Alto_Quellaveco (se sube desde el NO; desde abr-2025), el viento de día viene del
lado bajo y el de noche del lado alto, a pocos grados de lo esperado. Sarallenque también lo cumplía <i>antes</i> del cambio.
<i>Después</i>, lo contradice.</li>
</ol>
</section>

<section>
<h2>3. Hipótesis</h2>
<p><span class="tag">más probable</span><b>Cambio de montaje u orientación del sensor en julio de
2025.</b> Un WindSonic mide la dirección respecto a su marca de norte: si se gira el mástil o el
shelter, que va sobre remolque, gira toda la rosa. Un remontaje a otra altura o posición sobre el
shelter cambia además la exposición, y con ella la velocidad. Es la única hipótesis que explica
el salto simultáneo de dirección y velocidad con el sitio en la misma coordenada. Lo que no
encaja del todo: el desfase no es constante (≈110° de día, ≈185° de noche), así que el giro no
basta por sí solo. La distorsión de los obstáculos próximos podría explicar el resto.</p>
<p><span class="tag">contribuye, no explica</span><b>Obstáculos: enmallado contiguo al este y
talud a ~10 m.</b> Frenan y desvían el viento del este, que aquí es el nocturno, y dejan el flujo
más abierto desde el oeste. Pero un obstáculo al este no puede crear viento del SE de día ni
invertir el régimen. Si el enmallado o el corte del talud se hicieron en julio de 2025, pesarían
más en el cambio de velocidad.</p>
<p><span class="tag">por verificar</span><b>El tajo y las obras de la mina, que el DEM no ve.</b> En la
vista satélite del mapa, el tajo de Quellaveco queda a unos cientos de metros al oeste y suroeste
de Sarallenque, y Mina_Norte está en su borde norte. SRTM es del año 2000, anterior al tajo, así
que el relieve real al O y al SO es hoy mucho más profundo que el de la tabla §9. El avance de una
fase del tajo o un corte cerca de la estación (el talud «calado» de las fotos) cambia el flujo
local y podría producir un salto en una fecha concreta. No se ve por qué invertiría el régimen
diario, pero no puede descartarse sin las fechas de avance del tajo cerca de la estación en
julio de 2025. La fecha de la imagen de Esri no se conoce.</p>
<p><span class="tag">menor</span><b>Inclinación del shelter.</b> Con pocos grados, un sónico
inclinado subestima algo la velocidad horizontal y apenas cambia la dirección. No explica un giro
de más de 100°.</p>
<p><span class="tag">descartada</span><b>Fallo de veleta.</b> El WindSonic no tiene partes móviles.
Además, la velocidad cambió a la vez que la dirección.</p>
</section>

<section>
<h2>4. Otras anomalías en las estaciones de referencia</h2>
<p>Salieron al comparar y no tienen que ver con Sarallenque, pero afectan a su uso como referencia.
Medias vectoriales mensuales:</p>
<ul>
<li><b>Alto_Quellaveco cambia en marzo–abril de 2025.</b> De jul-2024 a mar-2025, el viento de día
venía de 196–254° y el nocturno era inestable (de 326° a 133° según el mes). Desde abr-2025, de día
viene de 258–316° y de noche de 45–145°. Su ladera, que sube hacia 109°, predice ~289° de día y
~109° de noche, así que el régimen <i>actual</i> es el coherente y el anterior no. Por eso su rosa
«antes» se aparta de lo esperado. Causa desconocida.</li>
<li><b>Mina_Norte tiene varios episodios.</b> Oct–dic 2024: de día viene de 113–161° (normalmente
~240–260°). Dic-2025 → abr-2026: de día viene de 185–194° y de noche de 144–166°, y su velocidad
cae de ~0.75 a ~0.55 veces la de Sarallenque_MQG. May–ago 2026: de noche viene de 311–343°.
Sep-2026, ya con el ClimaVUE: de día 272°, de noche 78°. Encaja con un shelter sobre remolque
trasladado más de una vez. Sus dos periodos mezclan ubicaciones, así que no sirve como referencia
hasta tener las fechas de traslado.</li>
</ul>
</section>

<section>
<h2>5. Qué hace falta para cerrarlo</h2>
<ul>
<li>El registro de campo de lo que se hizo con el Shelter 04 y su mástil a mediados de julio de
2025: traslado, giro, remontaje o cambio de sensor.</li>
<li>Comprobar en sitio hacia dónde apunta la marca de norte del WindSonic, con brújula corregida
por declinación.</li>
<li>La fecha de construcción del enmallado y del corte del talud, y las fechas de avance del tajo
cerca de Sarallenque en 2025.</li>
<li>Si se confirma un giro de valor conocido, puede corregirse la dirección desde el {change}.
Hasta entonces, conviene excluirla de las comparaciones.</li>
</ul>
</section>

<section>
<h2>6. Resumen por estación</h2>
<p class="muted">Dirección = media vectorial de las horas con viento ≥ 0.5 m/s. «Esperado»: de día,
desde el lado bajo de la pendiente; de noche, desde el lado alto. Velocidad media en m/s.</p>
<div class="scroll">{summary}</div>
</section>

<section>
<h2>7. Series semanales</h2>
<p class="muted">Línea punteada: {change}. Banda gris: transición excluida de las rosas.</p>
{weekly_dir}
{weekly_speed}
</section>

<section>
<h2>8. Rosas por estación</h2>
<p class="muted">Frecuencia en % de todas las horas de la franja (las calmas, &lt; 0.5 m/s, van en
el subtítulo). Escala radial común en las cuatro rosas de cada estación.</p>
{roses}
</section>

<section>
<h2>9. Relieve (SRTM 30 m)</h2>
<p class="muted">Altitud de cada anillo menos la del sitio, en m. Positivo = más alto que la
estación. «Entorno a 1.5 km»: media del anillo de 1.5 km; positivo = fondo de valle, negativo = alto.</p>
<div class="scroll">{relief}</div>
</section>

<section>
<h2>10. Fotos de campo</h2>
<div class="photos">{photo_f1}{photo_f2}{photo_mn}</div>
</section>

<section>
<h2>11. Datos y limitaciones</h2>
<ul>
<li>Datos horarios de la base de meteorología con el QC de <code>met_viewer</code>. Las horas son las
de la base.</li>
<li>Sensores: Sarallenque y Mina_Norte, WindSonic/ClimaVUE a ~4 m sobre un shelter. Sarallenque_MQG,
ClimaVUE a ~2 m. Altarani y Alto_Quellaveco, torre a 10 m. Las alturas distintas afectan a la
velocidad, no a la dirección.</li>
<li>Mina_Norte probablemente se reubicó (shelter móvil; GPS a 782 m del KMZ). Su periodo «después»
puede mezclar dos ubicaciones.</li>
<li>El DEM (SRTM, 2000) no ve obras posteriores, como el tajo, ni obstáculos menores de 30 m. Las
pendientes de las estaciones junto al tajo (Sarallenque, Mina_Norte) son las del terreno original.</li>
</ul>
</section>
"""


if __name__ == "__main__":
    build()
