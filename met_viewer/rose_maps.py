"""Mapas de rosas de viento por zona (vista por variable del visor).

Cada zona es un gráfico cartesiano en Web Mercator con las teselas incrustadas como imagen de
fondo, como en sarallenque_wind/build_report.py: no depende de WebGL ni de cargar teselas al
abrir el HTML. Las teselas se guardan en tiles_cache/ para no volver a descargarlas.

Rosa = frecuencia de procedencia (% de las horas con dato de la franja) por sector de 22.5°,
apilada por clase de velocidad; el radio es proporcional a la raíz de la frecuencia, así que el
área de cada pétalo es proporcional a su frecuencia. Dentro de una zona, día y noche comparten
escala. Botones: día / noche y fondo topográfico / satélite.
"""
from __future__ import annotations

import base64
import time
import urllib.request
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from PIL import Image
from pyproj import Transformer

import data
import wind
from stations import STATIONS, sensor_at

# petalo_m: longitud en el terreno del pétalo de referencia (ver REF_PERCENTIL); zoom: nivel de las teselas.
ZONAS: dict[str, dict] = {
    "Mina": dict(petalo_m=650, zoom=14, estaciones=[
        "Alto_Quellaveco", "Altarani", "Alto_Tala", "Camp_Quellaveco", "Cerro_Salviani",
        "Chancado_primario", "Charaque", "Dique_pie_botadero", "Mina_Norte", "Minas_Sur", "Papujune",
        "Planta_Concentradora", "Sarallenque", "Sarallenque_MQG-15-02", "Tala-1", "Tala_Legal"]),
    "Sur": dict(petalo_m=1300, zoom=13, estaciones=[
        "Apacheta", "Calacaja", "Calientes1", "Chalsos", "Cortadera", "DME3_Cortadera"]),
    "Altiplano": dict(petalo_m=2000, zoom=13, estaciones=["Huachunta", "Titire", "Vizcachas"]),
}
MARGEN_M = 1200
# El pétalo de referencia es este percentil de los pétalos máximos de cada estación: con el máximo
# absoluto, una estación con el viento siempre del mismo sector (100 %) encogía todas las demás.
REF_PERCENTIL = 75
ANCHO_PX = 1240                  # ancho útil de la sección en una pantalla de 1300 px
ALTO_MIN, ALTO_MAX = 560, 980
TILE_CACHE = Path(__file__).parent / "tiles_cache"
MERC_R = 20037508.342789244
FONDOS = {
    "Topográfico": ("https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
                    "Mapa: © OpenTopoMap (CC-BY-SA), © colaboradores de OpenStreetMap"),
    "Satélite": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                 "Imagen: Esri World Imagery"),
}
# Rampa azul ordinal de la paleta de referencia (skill dataviz), de la clase más floja a la más fuerte.
COLORES_VEL = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
INK, INK_2, MUTED, GRID, SUPERFICIE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
FONDO_ETIQUETA = "rgba(252,252,251,0.85)"
A_MERC = Transformer.from_crs(32719, 3857, always_xy=True)   # UTM 19S → Web Mercator


def _teselas(nombre: str, zoom: int, bbox: tuple[float, float, float, float]) -> dict:
    """Une las teselas que cubren bbox (Web Mercator) en una imagen JPEG incrustable."""
    url, _ = FONDOS[nombre]
    lado = 2 * MERC_R / 2 ** zoom
    xmin, ymin, xmax, ymax = bbox
    tx0, tx1 = int((xmin + MERC_R) // lado), int((xmax + MERC_R) // lado)
    ty0, ty1 = int((MERC_R - ymax) // lado), int((MERC_R - ymin) // lado)
    mosaico = Image.new("RGB", (256 * (tx1 - tx0 + 1), 256 * (ty1 - ty0 + 1)))
    carpeta = TILE_CACHE / {"Topográfico": "topo", "Satélite": "satellite"}[nombre]
    carpeta.mkdir(parents=True, exist_ok=True)
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            f = carpeta / f"{zoom}_{tx}_{ty}.img"
            if not f.exists():
                req = urllib.request.Request(url.format(z=zoom, x=tx, y=ty),
                                             headers={"User-Agent": "explorar-qaqc-visor/1.0"})
                for intento in range(3):      # los servidores de teselas cortan conexiones sueltas
                    try:
                        f.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                        break
                    except OSError:
                        if intento == 2:
                            raise
                        time.sleep(3)
                time.sleep(0.3)
            mosaico.paste(Image.open(f).convert("RGB").resize((256, 256)), (256 * (tx - tx0), 256 * (ty - ty0)))
    buf = BytesIO()
    mosaico.save(buf, format="JPEG", quality=80)
    return dict(source="data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(),
                xref="x", yref="y", x=-MERC_R + tx0 * lado, y=MERC_R - ty0 * lado,
                sizex=(tx1 - tx0 + 1) * lado, sizey=(ty1 - ty0 + 1) * lado,
                sizing="stretch", layer="below")


def _cunas(x0: float, y0: float, frec: np.ndarray, escala: float) -> tuple[list, list]:
    """Contorno de una rosa (una cuña por sector, radio ∝ √frecuencia) en Web Mercator; las
    cuñas van separadas por None para rellenarlas todas en una sola traza."""
    xs, ys, ancho = [], [], 360 / wind.SECTORES
    for k, f in enumerate(frec):
        if f <= 0:
            continue
        r = escala * np.sqrt(f)
        arco = np.deg2rad(np.linspace(k * ancho - ancho / 2, k * ancho + ancho / 2, 6))
        mx, my = A_MERC.transform(np.r_[x0, x0 + r * np.sin(arco), x0], np.r_[y0, y0 + r * np.cos(arco), y0])
        xs += list(mx) + [None]
        ys += list(my) + [None]
    return xs, ys


def _escala_grafica(largo_m: float) -> float:
    """Longitud redonda (1, 2 o 5 × 10^n m) cercana a largo_m."""
    base = 10 ** np.floor(np.log10(largo_m))
    return max(m * base for m in (1, 2, 5) if m * base <= largo_m)


def mapa_zona(zona: str, limpio: dict[str, pd.DataFrame], fin: pd.Timestamp) -> go.Figure | None:
    cfg = ZONAS[zona]
    con_dato = [e for e in cfg["estaciones"] if e in limpio and {data.WS, data.WD} <= set(limpio[e])
                and limpio[e][[data.WS, data.WD]].notna().all(axis=1).any()]
    if not con_dato:
        return None
    rosas = {(e, fr): wind.rosa(limpio[e], fr) for e in con_dato for fr in wind.FRANJAS}
    maximos = [max(rosas[(e, fr)][0].sum(axis=1).max() for fr in wind.FRANJAS) for e in con_dato]
    ref = float(np.percentile(maximos, REF_PERCENTIL))
    escala = cfg["petalo_m"] / np.sqrt(ref)

    fig = go.Figure()
    franja_de_traza: list[str | None] = []
    for fr in wind.FRANJAS:
        # de la clase acumulada mayor a la menor, para que las más flojas queden dentro
        for k in reversed(range(len(wind.ETIQUETAS_VEL))):
            xs, ys = [], []
            for e in con_dato:
                acumulada = rosas[(e, fr)][0].iloc[:, :k + 1].sum(axis=1).to_numpy()
                cx, cy = _cunas(STATIONS[e].easting, STATIONS[e].northing, acumulada, escala)
                xs += cx; ys += cy
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines", fill="toself", fillcolor=COLORES_VEL[k],
                line=dict(color=SUPERFICIE, width=0.6), name=wind.ETIQUETAS_VEL[k],
                legendgroup=wind.ETIQUETAS_VEL[k], legendrank=k, showlegend=fr == "día",
                hoverinfo="skip", visible=fr == "día"))
            franja_de_traza.append(fr)

    # puntos de las estaciones, con sensor y calmas en el hover
    todas = cfg["estaciones"]
    ux = np.array([STATIONS[e].easting for e in todas]); uy = np.array([STATIONS[e].northing for e in todas])
    mx, my = A_MERC.transform(ux, uy)
    hover = []
    for e in todas:
        s = sensor_at(e, "viento", f"{fin:%Y-%m-%d}")
        sensor = f"{s.kind} ~{s.height_m:g} m" if s and s.height_m else (s.kind if s else "sensor s/d")
        if e in con_dato:
            (_, cd, nd), (_, cn, nn) = rosas[(e, "día")], rosas[(e, "noche")]
            hover.append(f"<b>{e}</b><br>{sensor}<br>calma: día {cd:.0f} % ({nd} h) · noche {cn:.0f} % ({nn} h)")
        else:
            hover.append(f"<b>{e}</b><br>{sensor}<br>sin datos de viento en la ventana")
    fig.add_trace(go.Scatter(x=mx, y=my, mode="markers", hovertext=hover, hoverinfo="text", showlegend=False,
                             marker=dict(size=8, color=[INK if e in con_dato else MUTED for e in todas],
                                         line=dict(color=SUPERFICIE, width=1.5))))
    franja_de_traza.append(None)

    # Encuadre ajustado al ancho de la página: se elige el alto y se amplía el lado corto del
    # recuadro hasta la proporción del gráfico, así el mapa llena todo el ancho sin franjas vacías.
    alto = int(np.clip(ANCHO_PX * (np.ptp(uy) + 2 * MARGEN_M) / (np.ptp(ux) + 2 * MARGEN_M), ALTO_MIN, ALTO_MAX))
    cx, cy = (ux.min() + ux.max()) / 2, (uy.min() + uy.max()) / 2
    semi_x, semi_y = np.ptp(ux) / 2 + MARGEN_M, np.ptp(uy) / 2 + MARGEN_M
    if semi_y / semi_x < alto / ANCHO_PX:
        semi_y = semi_x * alto / ANCHO_PX
    else:
        semi_x = semi_y * ANCHO_PX / alto
    x0, y0 = A_MERC.transform(cx - semi_x, cy - semi_y)
    x1, y1 = A_MERC.transform(cx + semi_x, cy + semi_y)
    # teselas un 10 % más allá del encuadre: si la ventana es más estrecha o más ancha que
    # ANCHO_PX, plotly amplía el rango para mantener la escala y el fondo sigue cubriéndolo
    ex, ey = (x1 - x0) * 0.10, (y1 - y0) * 0.10
    imagenes = [_teselas(n, cfg["zoom"], (x0 - ex, y0 - ey, x1 + ex, y1 + ey)) | {"visible": i == 0}
                for i, n in enumerate(FONDOS)]

    anotaciones = [dict(text=FONDOS["Topográfico"][1], x=1, y=0, xref="paper", yref="paper", xanchor="right",
                        yanchor="bottom", showarrow=False, font=dict(size=10, color=INK_2), bgcolor=FONDO_ETIQUETA)]
    for e, lx, ly in zip(todas, mx, my):
        anotaciones.append(dict(x=lx, y=ly, text=e, showarrow=False, yshift=-11, yanchor="top",
                                font=dict(size=10, color=INK), bgcolor=FONDO_ETIQUETA, borderpad=1))
    anotaciones.append(dict(
        text=f"<b>Zona {zona}</b> · pétalo de {cfg['petalo_m']:g} m = {ref:.0f} % de las horas de la franja",
        x=0, y=0, xref="paper", yref="paper", xanchor="left", yanchor="bottom", showarrow=False,
        font=dict(size=12, color=INK), bgcolor=FONDO_ETIQUETA, borderpad=3))
    # barra de escala abajo a la izquierda, sobre el rótulo de la zona
    largo = _escala_grafica(2 * semi_x / 8)
    bx0, by = A_MERC.transform(cx - semi_x * 0.95, cy - semi_y * 0.88)
    bx1, _ = A_MERC.transform(cx - semi_x * 0.95 + largo, cy - semi_y * 0.88)
    formas = [dict(type="line", x0=bx0, x1=bx1, y0=by, y1=by, line=dict(color=INK, width=3), layer="above")]
    anotaciones.append(dict(x=(bx0 + bx1) / 2, y=by, text=f"{largo / 1000:g} km", showarrow=False, yshift=10,
                            font=dict(size=11, color=INK), bgcolor=FONDO_ETIQUETA))

    def visibles(fr: str) -> list[bool]:
        return [f is None or f == fr for f in franja_de_traza]

    # botones y leyenda sobre el propio mapa, sin márgenes alrededor
    estilo = dict(type="buttons", direction="right", yanchor="top", y=0.99, bgcolor=SUPERFICIE,
                  bordercolor=MUTED, font=dict(size=12, color=INK), showactive=True, pad=dict(t=4, l=4, r=4))
    horas = {"día": "10–18 h", "noche": "22–06 h"}
    fig.update_layout(
        height=alto, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE,
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color=INK_2),
        images=imagenes, shapes=formas, annotations=anotaciones,
        xaxis=dict(visible=False, range=[x0, x1]),
        yaxis=dict(visible=False, range=[y0, y1], scaleanchor="x", scaleratio=1),
        legend=dict(title=dict(text="Velocidad"), x=0.99, y=0.92, xanchor="right", yanchor="top",
                    bgcolor="rgba(252,252,251,0.9)", bordercolor=GRID, borderwidth=1, font=dict(size=11, color=INK)),
        hoverlabel=dict(bgcolor=SUPERFICIE, font=dict(color=INK)),
        updatemenus=[
            estilo | dict(x=0.01, xanchor="left", buttons=[
                dict(label=f"{fr.capitalize()} ({horas[fr]})", method="restyle", args=[{"visible": visibles(fr)}])
                for fr in wind.FRANJAS]),
            estilo | dict(x=0.99, xanchor="right", buttons=[
                dict(label=n, method="relayout",
                     args=[{**{f"images[{j}].visible": j == i for j in range(len(FONDOS))},
                            "annotations[0].text": FONDOS[n][1]}])
                for i, n in enumerate(FONDOS)]),
        ],
    )
    return fig
