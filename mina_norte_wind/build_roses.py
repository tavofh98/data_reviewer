"""Rosas de viento de Mina_Norte frente a Oeste 1, Charaque y Sarallenque_MQG-15-02, por tramo.

Preliminar (2026-11-12). Tramos de Mina_Norte deducidos de los datos (FINDINGS §9):
  A  2025-01-01 → 2025-11-14  en el punto del KMZ (327257, 8110014)
  B  2025-11-26 → 2026-08-26  WindSonic, junto a Oeste 1
  B+ el mismo tramo B con la dirección corregida de corrections.db (MN-B-rotation)
  C  2026-08-28 → hoy         ClimaVUE, junto a Oeste 1
En cada tramo las cuatro rosas usan solo las horas en que las cuatro estaciones tienen viento
válido, así que comparan las mismas horas. Mina_Norte y Oeste 1 están a 55 m: sus rosas se
dibujan desplazadas al norte y al sur, unidas a su punto real por una línea.

Ejecutar desde explorar_qaqc: uv run python mina_norte_wind/build_roses.py
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio

from common import HERE, OESTE1_DAT, SEGMENT_B, WD, WS, load_station, read_toa5
import qc
import rose_maps as rm
import wind
from stations import STATIONS

OESTE1_XY = (326451, 8110170)                     # KMZ «Oeste 1»
MN_KMZ_XY = (327257, 8110014)                     # punto del KMZ, tramo A
MN_XY = (STATIONS["Mina_Norte"].easting, STATIONS["Mina_Norte"].northing)
DRAW_OFFSET_M = 520                               # separación de dibujo de las rosas que se solapan
SEGMENTS = {
    "A": ("2025-01-01", "2025-11-14 00:00", "Tramo A · 2025-01-01 → 2025-11-14 · Mina_Norte en el punto del KMZ"),
    "B": ("2025-11-26 01:00", "2026-08-26 00:00", "Tramo B · 2025-11-26 → 2026-08-26 · WindSonic, sin corregir"),
    "B+": ("2025-11-26 01:00", "2026-08-26 00:00",
           f"Tramo B · mismo periodo con la dirección corregida (+{SEGMENT_B.parameter:g}°, corrections.db)"),
    "C": ("2026-08-28", "2026-12-31", "Tramo C · 2026-08-28 → hoy · ClimaVUE"),
}
NEIGHBORS = ("Charaque", "Sarallenque_MQG-15-02")


def wind_qc(df: pd.DataFrame) -> pd.DataFrame:
    """Rango y valores pegados de qc.station_rules, solo para velocidad y dirección."""
    df = df[[WS, WD]].astype("float64")
    rules = qc.station_rules(df)
    return df.mask(rules["RANGE"] | rules["STUCK"])


def load_all() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Viento crudo de las cuatro estaciones y Mina_Norte corregida, con el QC de viento aplicado."""
    start, end = pd.Timestamp("2024-12-31 23:00"), pd.Timestamp("2027-01-01")
    raw = {s: load_station(s, start, end) for s in NEIGHBORS + ("Mina_Norte",)}
    raw["Oeste 1"] = read_toa5(OESTE1_DAT)
    corrected = load_station("Mina_Norte", start, end, corrected=True)
    return {s: wind_qc(df) for s, df in raw.items()}, wind_qc(corrected)


def segment(data: dict[str, pd.DataFrame], corrected_mn: pd.DataFrame, key: str) -> dict[str, pd.DataFrame]:
    start, end, _ = SEGMENTS[key]
    d = {s: df.loc[start:end] for s, df in data.items()}
    if key == "B+":
        d["Mina_Norte"] = corrected_mn.loc[start:end]
    common_hours = None
    for df in d.values():
        valid = df.dropna().index
        common_hours = valid if common_hours is None else common_hours.intersection(valid)
    return {s: df.loc[common_hours] for s, df in d.items()}


def positions(key: str) -> dict[str, tuple[tuple[float, float], tuple[float, float]]]:
    """(punto real, centro de dibujo de la rosa) de cada estación en UTM."""
    ch = (STATIONS["Charaque"].easting, STATIONS["Charaque"].northing)
    mqg = (STATIONS["Sarallenque_MQG-15-02"].easting, STATIONS["Sarallenque_MQG-15-02"].northing)
    if key == "A":
        mn = (MN_KMZ_XY, MN_KMZ_XY)
        o1 = (OESTE1_XY, OESTE1_XY)
    else:
        mn = (MN_XY, (MN_XY[0], MN_XY[1] + DRAW_OFFSET_M))
        o1 = (OESTE1_XY, (OESTE1_XY[0], OESTE1_XY[1] - DRAW_OFFSET_M))
    return {"Charaque": (ch, ch), "Sarallenque_MQG-15-02": (mqg, mqg), "Mina_Norte": mn, "Oeste 1": o1}


def offsets(d: dict[str, pd.DataFrame], period: str) -> pd.DataFrame:
    """Mediana e IQR de la diferencia de dirección de cada estación con Oeste 1 (ambas ≥ 1 m/s)."""
    rows = []
    ref = d["Oeste 1"]
    for s, df in d.items():
        if s == "Oeste 1":
            continue
        x = df.join(ref, rsuffix="_o1")
        x = x[x.index.hour.isin(wind.FRANJAS[period]) & (x[WS] >= 1) & (x[f"{WS}_o1"] >= 1)]
        diff = ((x[WD] - x[f"{WD}_o1"] + 180) % 360) - 180
        rows.append(dict(station=s, median=diff.median(), iqr=diff.quantile(.75) - diff.quantile(.25), hours=len(diff)))
    return pd.DataFrame(rows)


def figure(key: str, d: dict[str, pd.DataFrame], scale: float, bbox) -> go.Figure:
    pos = positions(key)
    roses = {(s, p): wind.rosa(d[s], p) for s in d for p in wind.FRANJAS}
    fig = go.Figure()
    trace_period: list[str | None] = []
    for p in wind.FRANJAS:
        for k in reversed(range(len(wind.ETIQUETAS_VEL))):
            xs, ys = [], []
            for s in d:
                cumulative = roses[(s, p)][0].iloc[:, :k + 1].sum(axis=1).to_numpy()
                cx, cy = rm._cunas(*pos[s][1], cumulative, scale)
                xs += cx; ys += cy
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", fill="toself", fillcolor=rm.COLORES_VEL[k],
                                     line=dict(color=rm.SUPERFICIE, width=0.6), name=wind.ETIQUETAS_VEL[k],
                                     legendgroup=wind.ETIQUETAS_VEL[k], legendrank=k, showlegend=p == "día",
                                     hoverinfo="skip", visible=p == "día"))
            trace_period.append(p)

    # líneas de unión del punto real al centro de la rosa desplazada
    lx, ly = [], []
    for s, (real, center) in pos.items():
        if real != center:
            mx, my = rm.A_MERC.transform([real[0], center[0]], [real[1], center[1]])
            lx += list(mx) + [None]; ly += list(my) + [None]
    fig.add_trace(go.Scatter(x=lx, y=ly, mode="lines", line=dict(color=rm.INK_2, width=1, dash="dot"),
                             hoverinfo="skip", showlegend=False))
    trace_period.append(None)

    names = list(pos)
    px, py = rm.A_MERC.transform([pos[s][0][0] for s in names], [pos[s][0][1] for s in names])
    hover = []
    for s in names:
        (_, calm_d, n_d), (_, calm_n, n_n) = roses[(s, "día")], roses[(s, "noche")]
        hover.append(f"<b>{s}</b><br>calma: día {calm_d:.0f} % ({n_d} h) · noche {calm_n:.0f} % ({n_n} h)")
    if key == "A":                                # ubicación actual de Mina_Norte, como referencia
        ax, ay = rm.A_MERC.transform(*MN_XY)
        fig.add_trace(go.Scatter(x=[ax], y=[ay], mode="markers", hovertext=["Mina_Norte: ubicación actual"],
                                 hoverinfo="text", showlegend=False,
                                 marker=dict(size=8, color=rm.MUTED, line=dict(color=rm.SUPERFICIE, width=1.5))))
        trace_period.append(None)
    fig.add_trace(go.Scatter(x=px, y=py, mode="markers", hovertext=hover, hoverinfo="text", showlegend=False,
                             marker=dict(size=8, color=rm.INK, line=dict(color=rm.SUPERFICIE, width=1.5))))
    trace_period.append(None)

    notes = [dict(text=rm.FONDOS["Topográfico"][1], x=1, y=0, xref="paper", yref="paper", xanchor="right",
                  yanchor="bottom", showarrow=False, font=dict(size=10, color=rm.INK_2), bgcolor=rm.FONDO_ETIQUETA)]
    for s in names:
        cx, cy = rm.A_MERC.transform(*pos[s][1])
        shifted = pos[s][0] != pos[s][1]
        notes.append(dict(x=cx, y=cy, text=s, showarrow=False, yshift=-11, yanchor="top",
                          xshift=60 if shifted else 0, font=dict(size=11, color=rm.INK),
                          bgcolor=rm.FONDO_ETIQUETA, borderpad=1))

    x0, y0, x1, y1 = bbox
    ex, ey = (x1 - x0) * 0.10, (y1 - y0) * 0.10
    images = [rm._teselas(n, 14, (x0 - ex, y0 - ey, x1 + ex, y1 + ey)) | {"visible": i == 0}
              for i, n in enumerate(rm.FONDOS)]

    def visible(period: str) -> list[bool]:
        return [p is None or p == period for p in trace_period]

    style = dict(type="buttons", direction="right", yanchor="top", y=0.99, bgcolor=rm.SUPERFICIE,
                 bordercolor=rm.MUTED, font=dict(size=12, color=rm.INK), showactive=True, pad=dict(t=4, l=4, r=4))
    fig.update_layout(
        height=600, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=rm.SUPERFICIE, plot_bgcolor=rm.SUPERFICIE,
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', color=rm.INK_2),
        images=images, annotations=notes,
        xaxis=dict(visible=False, range=[x0, x1]),
        yaxis=dict(visible=False, range=[y0, y1], scaleanchor="x", scaleratio=1),
        legend=dict(title=dict(text="Velocidad"), x=0.99, y=0.90, xanchor="right", yanchor="top",
                    bgcolor="rgba(252,252,251,0.9)", bordercolor=rm.GRID, borderwidth=1, font=dict(size=11, color=rm.INK)),
        hoverlabel=dict(bgcolor=rm.SUPERFICIE, font=dict(color=rm.INK)),
        updatemenus=[
            style | dict(x=0.01, xanchor="left", buttons=[
                dict(label={"día": "Día (10–18 h)", "noche": "Noche (22–06 h)"}[p], method="restyle",
                     args=[{"visible": visible(p)}]) for p in wind.FRANJAS]),
            style | dict(x=0.99, xanchor="right", buttons=[
                dict(label=n, method="relayout",
                     args=[{**{f"images[{j}].visible": j == i for j in range(len(rm.FONDOS))},
                            "annotations[0].text": rm.FONDOS[n][1]}]) for i, n in enumerate(rm.FONDOS)]),
        ],
    )
    return fig


def offsets_table(d: dict[str, pd.DataFrame]) -> str:
    rows = []
    for p in wind.FRANJAS:
        for r in offsets(d, p).itertuples():
            rows.append(f"<tr><td>{p}</td><td>{r.station}</td><td class='num'>{r.median:+.0f}°</td>"
                        f"<td class='num'>{r.iqr:.0f}°</td><td class='num'>{r.hours}</td></tr>")
    return ("<table class='data'><tr><th>Franja</th><th>Estación</th><th>Dirección − Oeste 1 (mediana)</th>"
            "<th>IQR</th><th>Horas (ambas ≥ 1 m/s)</th></tr>" + "".join(rows) + "</table>")


def page(body: str) -> str:
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rosas Mina Norte</title>
<style>
 :root{{--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--surface:#fcfcfb;--page:#f9f9f7}}
 body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--page);color:var(--ink);margin:0;line-height:1.5}}
 main{{max-width:1180px;margin:0 auto;padding:16px}}
 h1{{font-size:24px;margin:8px 0 4px}} h2{{font-size:18px;margin:4px 0 4px}}
 p{{max-width:90ch}} .muted{{color:var(--muted);font-size:13px}} .lead{{font-size:15px;color:var(--ink2)}}
 section{{background:var(--surface);border:1px solid rgba(11,11,11,.1);border-radius:8px;padding:12px 16px;margin:16px 0}}
 table.data{{border-collapse:collapse;font-size:13px;margin:8px 0;width:100%}}
 table.data th,table.data td{{border-bottom:1px solid var(--grid);padding:4px 8px;text-align:left}}
 table.data th{{color:var(--ink2);font-weight:600}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
</style></head><body><main>
{body}
<p class="muted">Generado el {date.today():%Y-%m-%d} con mina_norte_wind/build_roses.py.</p>
</main></body></html>"""


def main() -> None:
    data, corrected_mn = load_all()
    by_segment = {k: segment(data, corrected_mn, k) for k in SEGMENTS}
    # escala común a todos los mapas y franjas: el pétalo de referencia es el percentil 75 de los máximos
    maxima = [wind.rosa(d[s], p)[0].sum(axis=1).max() for d in by_segment.values() for s in d for p in wind.FRANJAS]
    ref = float(np.percentile(maxima, rm.REF_PERCENTIL))
    petal_m = 480
    scale = petal_m / np.sqrt(ref)

    xs = [OESTE1_XY[0], MN_KMZ_XY[0], STATIONS["Charaque"].easting, STATIONS["Sarallenque_MQG-15-02"].easting]
    ys = [OESTE1_XY[1] - DRAW_OFFSET_M, MN_XY[1] + DRAW_OFFSET_M, STATIONS["Charaque"].northing,
          STATIONS["Sarallenque_MQG-15-02"].northing]
    margin = 900
    x0, y0 = rm.A_MERC.transform(min(xs) - margin, min(ys) - margin)
    x1, y1 = rm.A_MERC.transform(max(xs) + margin, max(ys) + margin)
    bbox = (x0, y0, x1, y1)

    sections, first = [], True
    for k, (_, _, title) in SEGMENTS.items():
        d = by_segment[k]
        html = pio.to_html(figure(k, d, scale, bbox), full_html=False, include_plotlyjs="cdn" if first else False,
                           config={"displaylogo": False, "scrollZoom": True})
        first = False
        n = len(next(iter(d.values())))
        sections.append(f"<section><h2>{title}</h2><p class='muted'>{n} horas comunes a las cuatro estaciones. "
                        f"Pétalo de {petal_m} m = {ref:.0f} % de las horas de la franja (escala común a todos los mapas).</p>"
                        f"{html}{offsets_table(d)}</section>")

    body = ("<h1>Rosas de viento de Mina_Norte frente a Oeste 1, Charaque y Sarallenque_MQG-15-02</h1>"
            "<p class='lead'>Preliminar. Frecuencia de procedencia por sector de 22.5°, apilada por velocidad; "
            "área del pétalo proporcional a la frecuencia. Mina_Norte y Oeste 1 están a 55 m: en los tramos B y C "
            "sus rosas se dibujan desplazadas 520 m al norte (Mina_Norte) y al sur (Oeste 1), unidas a su punto por "
            "una línea de puntos. En el tramo A el punto gris es la ubicación actual de Mina_Norte.</p>"
            + "".join(sections))
    out = HERE / "mina_norte_roses.html"
    out.write_text(page(body), encoding="utf-8")
    print("escrito", out, f"({out.stat().st_size / 1e6:.1f} MB)")
    for k, d in by_segment.items():
        print(f"\n[{k}] {len(next(iter(d.values())))} h comunes")
        for p in wind.FRANJAS:
            print(p, offsets(d, p).round(1).to_string(index=False), sep="\n")


if __name__ == "__main__":
    main()
