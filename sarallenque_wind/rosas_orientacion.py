"""Rosas de viento de Sarallenque en cuatro configuraciones del sensor, con selector día / noche.

    (1,1) antes del traslado de julio de 2025      (1,2) después de la reorientación del 2026-09-25
    (2,1) después del traslado de julio de 2025    (2,2) igual que (2,1), dirección + 180°

Uso (desde explorar_qaqc/):
    uv run python sarallenque_wind/rosas_orientacion.py

Salida: sarallenque_wind/rosas_orientacion_sarallenque.html (plotly.js por CDN).
Mismos datos (QC de met_viewer), franjas, sectores y clases de velocidad que build_report.py.
"""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

import build_report as br
from build_report import data, qc

OUTPUT = br.HERE / "rosas_orientacion_sarallenque.html"

REORIENTACION = pd.Timestamp("2026-09-25 20:00")   # primera hora limpia tras la visita (11–19 h: transición)
# (fila, columna), título, inicio, fin, grados a sumar a la dirección
PANELES = [
    ((1, 1), "Antes del traslado de julio de 2025", pd.Timestamp("2024-07-14"), br.CHANGE, 0),
    ((1, 2), "Después de la reorientación del 25-09-2026", REORIENTACION, None, 0),
    # Tramo estable tras el traslado (FINDINGS §9); 2025-07-14 → 11-16 tuvo giros intermedios.
    ((2, 1), "Después del traslado de julio de 2025", pd.Timestamp("2025-11-17"), pd.Timestamp("2026-09-25 10:00"), 0),
    ((2, 2), "Después del traslado, dirección + 180°", pd.Timestamp("2025-11-17"), pd.Timestamp("2026-09-25 10:00"), 180),
]
FRANJAS = {"día": "Día (10–17 h)", "noche": "Noche (22–06 h)"}


def cargar() -> pd.DataFrame:
    """Viento horario de Sarallenque con QC, desde el inicio del primer panel hasta hoy."""
    ini, fin = PANELES[0][2], pd.Timestamp.now().ceil("h")
    limpio, _, _ = qc.apply_qc(data.load(ini - pd.Timedelta(days=2), fin))
    df = limpio[br.TARGET][[data.WS, data.WD]].dropna()
    return df[df.index >= ini]


def tramo(df: pd.DataFrame, ini, fin, giro: float, franja: str) -> pd.DataFrame:
    sel = df[(df.index >= ini) & ((df.index < fin) if fin is not None else True)]
    sel = sel[sel.index.hour.isin(br.SHIFTS[franja])].copy()
    sel[data.WD] = (sel[data.WD] + giro) % 360
    return sel


def direccion_mediana(df: pd.DataFrame) -> float:
    """Dirección vectorial: mediana de las componentes del vector unitario de procedencia, sin calmas."""
    rad = np.deg2rad(df.loc[df[data.WS] >= qc.CALM_WS, data.WD])
    if rad.empty:
        return np.nan
    return float(np.rad2deg(np.arctan2(np.median(np.sin(rad)), np.median(np.cos(rad)))) % 360)


def _fecha(t: pd.Timestamp | None, df: pd.DataFrame) -> str:
    return f"{(t if t is not None else df.index.max()):%Y-%m-%d}"


def figura(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=2, cols=2, specs=[[{"type": "polar"}] * 2] * 2,
                        subplot_titles=[p[1] for p in PANELES], horizontal_spacing=0.12, vertical_spacing=0.16)
    theta = np.arange(br.SECTORS) * 360 / br.SECTORS
    visibles, titulos, rmax = {}, {}, {}
    for franja in FRANJAS:
        visibles[franja], titulos[franja], maximos = [], [], []
        for (fila, col), titulo, ini, fin, giro in PANELES:
            sel = tramo(df, ini, fin, giro, franja)
            tabla, calma = br.rose_table(sel)
            maximos.append(tabla.sum(axis=1).max())
            titulos[franja].append(
                f"{titulo}<br><span style='font-size:11px;color:{br.MUTED}'>{ini:%Y-%m-%d} → {_fecha(fin, df)}"
                f" · {len(sel)} h · calma {calma:.0f} % · dirección mediana {direccion_mediana(sel):.0f}°</span>")
            for k, clase in enumerate(br.SPEED_LABELS):
                fig.add_trace(go.Barpolar(
                    r=tabla[clase].round(2), theta=theta, name=clase, legendgroup=clase,
                    marker_color=br.SPEED_COLORS[k], marker_line=dict(color=br.SURFACE, width=1),
                    showlegend=((fila, col) == (1, 1)), visible=(franja == "día"),
                    hovertemplate=f"{html.escape(titulo)} · {franja}<br>desde %{{theta}}°<br>{clase}: %{{r:.1f}} %<extra></extra>"),
                    row=fila, col=col)
        rmax[franja] = max(maximos) * 1.05
    n = len(fig.data) // 2
    for franja, i in zip(FRANJAS, range(2)):
        visibles[franja] = [i * n <= j < (i + 1) * n for j in range(2 * n)]

    fig.update_polars(
        bgcolor=br.SURFACE, barmode="stack",
        angularaxis=dict(direction="clockwise", rotation=90, tickvals=list(range(0, 360, 45)),
                         ticktext=["N", "NE", "E", "SE", "S", "SO", "O", "NO"], gridcolor=br.GRID,
                         linecolor=br.BASELINE, tickfont=dict(size=10, color=br.MUTED)),
        radialaxis=dict(range=[0, rmax["día"]], gridcolor=br.GRID, showline=False, nticks=4, ticksuffix=" %",
                        angle=45, tickangle=45, tickfont=dict(size=9, color=br.MUTED)),
    )
    for a, texto in zip(fig.layout.annotations, titulos["día"]):
        a.text, a.font, a.yshift = texto, dict(size=13, color=br.INK), 16

    def relayout(franja: str) -> dict:
        cambios = {f"annotations[{i}].text": t for i, t in enumerate(titulos[franja])}
        cambios.update({f"polar{k if k > 1 else ''}.radialaxis.range": [0, rmax[franja]] for k in range(1, 5)})
        return cambios

    fig.update_layout(
        height=900, paper_bgcolor=br.SURFACE, plot_bgcolor=br.SURFACE,
        font=dict(family=br.FONT, size=12, color=br.INK_2), margin=dict(l=40, r=40, t=170, b=40),
        title=dict(text="Sarallenque · rosas de viento según la orientación del sensor", x=0.01,
                   y=0.985, yanchor="top", font=dict(size=17, color=br.INK)),
        legend=dict(orientation="h", x=1, xanchor="right", y=1.10, yanchor="bottom", title_text="Velocidad "),
        updatemenus=[dict(
            type="buttons", direction="right", x=0, xanchor="left", y=1.10, yanchor="bottom", showactive=True,
            bgcolor=br.SURFACE, bordercolor=br.MUTED, font=dict(color=br.INK),
            buttons=[dict(label=etiqueta, method="update", args=[{"visible": visibles[f]}, relayout(f)])
                     for f, etiqueta in FRANJAS.items()])],
    )
    return fig


NOTA = (
    "Frecuencia en % de todas las horas de la franja, apilada por velocidad; las calmas (&lt; 0.5 m/s) "
    "no tienen pétalo. Las cuatro rosas comparten escala dentro de cada franja. Dirección mediana: "
    "calculada vectorialmente, con la mediana de las componentes del vector unitario de procedencia "
    "(sin calmas). Datos horarios con el QC "
    "de met_viewer. El 25-09-2026 de 11 a 19 h (transición de la visita) queda fuera. El panel (2,1) usa "
    "el tramo estable tras el traslado (desde 2025-11-17); del 2025-07-14 al 2025-11-16 hubo giros "
    "intermedios (met_viewer/FINDINGS.md §9).")


def main() -> None:
    df = cargar()
    fig = figura(df)
    cuerpo = fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False})
    OUTPUT.write_text(
        f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Rosas de Sarallenque</title>
<style>body{{font-family:{br.FONT};background:{br.PAGE};color:{br.INK};margin:0;padding:16px}}
main{{max-width:1000px;margin:auto;background:{br.SURFACE};border:1px solid rgba(11,11,11,.1);border-radius:8px;padding:12px}}
p{{color:{br.INK_2};font-size:13px}}</style></head><body><main>{cuerpo}<p>{NOTA}</p></main></body></html>""",
        encoding="utf-8")
    for franja in FRANJAS:
        for p in PANELES:
            sel = tramo(df, p[2], p[3], p[4], franja)
            print(f"{franja:5s} {p[1]:45s} {len(sel):5d} h  dirección mediana {direccion_mediana(sel):5.0f}°")
    print(f"HTML: {OUTPUT}")


if __name__ == "__main__":
    main()
