"""Caso completo de una estación: dirección horaria real (Θ1) frente a la estimada desde 5 min.

Estimada = V1 de analyze.py: vectores unitarios de los 12 WindDir_Avg de 5 min de la hora, sin calmas.
Genera un HTML con: rosas día/noche de ambos casos, serie de tiempo horaria con su error, un
episodio de 48 h a 5 min y la dispersión real-estimada. Solo datos y gráficos.

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.case_study

Salida: wind_vector/output/caso_<estación>.html (plotly.js por CDN).
"""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from wind_vector.analyze import BLOCKS, OUT, build_hourly, circ_diff, valid_mask

STATION = "quellaveco"
LABEL = "Alto Quellaveco"

# Misma paleta, franjas y clases de velocidad que sarallenque_wind/build_report.py.
SPEED_BINS = [0.5, 2, 4, 6, np.inf]
SPEED_LABELS = ["0.5–2 m/s", "2–4 m/s", "4–6 m/s", "≥ 6 m/s"]
SPEED_COLORS = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
REAL_COLOR, ESTIMATE_COLOR = "#2a78d6", "#eb6834"
INK, INK_2, MUTED, GRID, BASELINE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SURFACE, PAGE = "#fcfcfb", "#f9f9f7"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
SHIFTS = {"día": list(range(10, 18)), "noche": [22, 23, 0, 1, 2, 3, 4, 5, 6]}
SHIFT_TITLES = {"día": "Día (10–17 h)", "noche": "Noche (22–06 h)"}
SECTORS = 16
CALM_WS = 0.5
COMPASS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
DEG_TICKS = dict(tickvals=[0, 90, 180, 270, 360], ticktext=["N", "E", "S", "O", "N"])


def rose_table(direction: pd.Series, speed: pd.Series, n_hours: int) -> tuple[pd.DataFrame, float]:
    """Frecuencia (% de todas las horas de la franja) por sector y clase de velocidad, y % de calma."""
    windy = speed >= CALM_WS
    width = 360 / SECTORS
    sector = ((direction[windy] + width / 2) % 360 // width).astype(int)
    classes = pd.cut(speed[windy], SPEED_BINS, labels=SPEED_LABELS, right=False)
    table = pd.crosstab(sector, classes).reindex(index=range(SECTORS), columns=SPEED_LABELS, fill_value=0)
    return table / n_hours * 100, (1 - windy.sum() / n_hours) * 100


def pick_episode(h: pd.DataFrame, hour_start: pd.Series, mask: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Ventana de 48 h representativa: completa, mayormente con viento del norte y con un error
    medio de la estimada igual al error medio de las horas del norte de todo el periodo."""
    err = np.abs(circ_diff(h["V1"], h["truth"]))
    north = np.abs(circ_diff(h["truth"], 0.0)) <= 45
    target = err[mask & north].mean()
    day = hour_start.dt.normalize()
    best, best_gap = None, np.inf
    for d in day[mask].unique():
        sel = ((day == d) | (day == d + pd.Timedelta(days=1))) & mask
        if sel.sum() != 48 or (north[sel].mean() < 0.5):
            continue
        gap = abs(err[sel].mean() - target)
        if gap < best_gap:
            best, best_gap = d, gap
    return best, best + pd.Timedelta(days=2)


def rose_figure(h: pd.DataFrame, hour_start: pd.Series, mask: pd.Series) -> go.Figure:
    cases = [("truth", "Θ1 horario del logger (real)"), ("V1", "Estimada desde 5 min")]
    theta = np.arange(SECTORS) * 360 / SECTORS
    tables, titles, rmax = {}, [], 0.0
    for franja in SHIFTS:
        sel = h[mask & hour_start.dt.hour.isin(SHIFTS[franja])]
        for col, label in cases:
            table, calm = rose_table(sel[col], sel["ws_h"], len(sel))
            tables[(franja, col)] = table
            rmax = max(rmax, table.sum(axis=1).max())
            top = table.sum(axis=1).idxmax() * 360 / SECTORS
            titles.append(f"{label} · {SHIFT_TITLES[franja]}<br><span style='font-size:11px;color:{MUTED}'>"
                          f"{len(sel)} h · calma {calm:.0f} % · sector más frecuente {top:.0f}° "
                          f"({table.sum(axis=1).max():.1f} %)</span>")
    fig = make_subplots(rows=2, cols=2, specs=[[{"type": "polar"}] * 2] * 2, subplot_titles=titles,
                        horizontal_spacing=0.12, vertical_spacing=0.16)
    for franja_i, franja in enumerate(SHIFTS):
        for col_i, (col, label) in enumerate(cases):
            for k, speed_class in enumerate(SPEED_LABELS):
                fig.add_trace(go.Barpolar(
                    r=tables[(franja, col)][speed_class].round(2), theta=theta, name=speed_class,
                    legendgroup=speed_class, showlegend=(franja_i == 0 and col_i == 0),
                    marker_color=SPEED_COLORS[k], marker_line=dict(color=SURFACE, width=1),
                    hovertemplate=f"{html.escape(label)} · {franja}<br>desde %{{theta}}°<br>{speed_class}: "
                                  f"%{{r:.1f}} %<extra></extra>"), row=franja_i + 1, col=col_i + 1)
    fig.update_polars(
        bgcolor=SURFACE, barmode="stack",
        angularaxis=dict(direction="clockwise", rotation=90, tickvals=list(range(0, 360, 45)), ticktext=COMPASS,
                         gridcolor=GRID, linecolor=BASELINE, tickfont=dict(size=10, color=MUTED)),
        radialaxis=dict(range=[0, rmax * 1.05], gridcolor=GRID, showline=False, nticks=4, ticksuffix=" %",
                        angle=45, tickangle=45, tickfont=dict(size=9, color=MUTED)))
    for a in fig.layout.annotations:
        a.font, a.yshift = dict(size=12, color=INK), 16
    fig.update_layout(height=900, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
                      font=dict(family=FONT, size=12, color=INK_2), margin=dict(l=40, r=40, t=130, b=30),
                      title=dict(text=f"{LABEL} · rosas de viento: dirección real y estimada desde 5 min",
                                 x=0.01, y=0.985, yanchor="top", font=dict(size=17, color=INK)),
                      legend=dict(orientation="h", x=1, xanchor="right", y=1.10, yanchor="bottom",
                                  title_text="Velocidad "))
    return fig


def series_figure(h: pd.DataFrame, ts: pd.Series, mask: pd.Series, episode: tuple[pd.Timestamp, pd.Timestamp]):
    sel, t = h[mask], ts[mask]
    error = circ_diff(sel["V1"], sel["truth"])
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.06)
    for name, col, color, symbol in (("Θ1 horario del logger (real)", "truth", REAL_COLOR, "circle"),
                                     ("Estimada desde 5 min", "V1", ESTIMATE_COLOR, "diamond")):
        fig.add_trace(go.Scattergl(x=t, y=sel[col].round(1), mode="markers", name=name,
                                   marker=dict(size=4, color=color, symbol=symbol, opacity=0.85),
                                   hovertemplate="%{x|%Y-%m-%d %H:%M}<br>%{y:.1f}°<extra>" + name + "</extra>"),
                      row=1, col=1)
    fig.add_trace(go.Scattergl(x=t, y=pd.Series(error).round(1), mode="markers", name="Error (estimada − real)",
                               marker=dict(size=4, color=INK_2, opacity=0.6),
                               hovertemplate="%{x|%Y-%m-%d %H:%M}<br>%{y:+.1f}°<extra>error</extra>"), row=2, col=1)
    mid = episode[0] + pd.Timedelta(days=1)
    start, end = mid - pd.Timedelta(days=7), mid + pd.Timedelta(days=7)

    def rng(a, b):
        return {"xaxis2.range": [str(a), str(b)], "xaxis.range": [str(a), str(b)]}
    buttons = [dict(label="Episodio 48 h", method="relayout", args=[rng(*episode)]),
               dict(label="14 días", method="relayout", args=[rng(start, end)]),
               dict(label="90 días", method="relayout", args=[rng(mid - pd.Timedelta(days=45), mid + pd.Timedelta(days=45))]),
               dict(label="Todo", method="relayout", args=[{"xaxis.autorange": True, "xaxis2.autorange": True}])]
    fig.update_yaxes(range=[0, 360], title_text="Dirección", row=1, col=1, **DEG_TICKS)
    fig.update_yaxes(range=[-185, 185], title_text="Error (°)", tickvals=[-180, -90, 0, 90, 180], row=2, col=1)
    fig.update_xaxes(range=[str(start), str(end)], gridcolor=GRID, linecolor=BASELINE)
    fig.update_yaxes(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE)
    fig.update_layout(height=620, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, hovermode="x unified",
                      font=dict(family=FONT, size=12, color=INK_2), margin=dict(l=60, r=30, t=90, b=40),
                      title=dict(text=f"{LABEL} · serie horaria de la dirección real y la estimada", x=0.01,
                                 y=0.985, yanchor="top", font=dict(size=17, color=INK)),
                      legend=dict(orientation="h", x=1, xanchor="right", y=1.02, yanchor="bottom"),
                      updatemenus=[dict(type="buttons", direction="right", x=0, xanchor="left", y=1.02,
                                        yanchor="bottom", showactive=False, bgcolor=SURFACE, bordercolor=MUTED,
                                        font=dict(color=INK), buttons=buttons)])
    return fig


def episode_figure(df: pd.DataFrame, h: pd.DataFrame, episode: tuple[pd.Timestamp, pd.Timestamp]) -> go.Figure:
    """Los 5 min (Avg y D1) y las dos direcciones horarias, a lo largo de las 48 h del episodio."""
    hour_start = df["TIMESTAMP"] - pd.Timedelta(hours=1)
    rows = df[(hour_start >= episode[0]) & (hour_start < episode[1])]
    sub = h.loc[rows.index]
    stamps, avg, d1 = [], [], []
    for i, b in enumerate(BLOCKS):
        stamps.append(rows["TIMESTAMP"] - pd.Timedelta(minutes=5 * (11 - i)))
        avg.append(rows[f"WindDir_Avg_{b}"])
        d1.append(rows[f"WindDir_D1_WVT_{b}"])
    x5 = pd.concat(stamps).to_numpy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x5, y=pd.concat(d1).round(1), mode="markers", name="D1 a 5 min (vectorial)",
                             marker=dict(size=5, color=REAL_COLOR, opacity=0.45),
                             hovertemplate="%{x|%d %H:%M}<br>%{y:.1f}°<extra>D1 5 min</extra>"))
    fig.add_trace(go.Scatter(x=x5, y=pd.concat(avg).round(1), mode="markers", name="WindDir_Avg a 5 min",
                             marker=dict(size=5, color=ESTIMATE_COLOR, opacity=0.45, symbol="diamond"),
                             hovertemplate="%{x|%d %H:%M}<br>%{y:.1f}°<extra>Avg 5 min</extra>"))
    for name, col, color in (("Θ1 horario del logger (real)", "truth", REAL_COLOR),
                             ("Estimada horaria desde Avg 5 min", "V1", ESTIMATE_COLOR)):
        xs, ys = [], []
        for ts_end, value in zip(rows["TIMESTAMP"], sub[col]):
            xs += [ts_end - pd.Timedelta(hours=1), ts_end, None]
            ys += [value, value, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=name, line=dict(color=color, width=3),
                                 hovertemplate="%{y:.1f}°<extra>" + name + "</extra>"))
    fig.update_yaxes(range=[0, 360], title_text="Dirección", gridcolor=GRID, linecolor=BASELINE, **DEG_TICKS)
    fig.update_xaxes(gridcolor=GRID, linecolor=BASELINE)
    fig.update_layout(height=470, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, hovermode="closest",
                      font=dict(family=FONT, size=12, color=INK_2), margin=dict(l=60, r=30, t=100, b=40),
                      title=dict(text=f"{LABEL} · episodio {episode[0]:%Y-%m-%d} → {episode[1]:%Y-%m-%d}: "
                                      f"registros de 5 min y direcciones horarias", x=0.01, y=0.985,
                                 yanchor="top", font=dict(size=16, color=INK)),
                      legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom"))
    return fig


def scatter_figure(h: pd.DataFrame, mask: pd.Series) -> go.Figure:
    sel = h[mask]
    counts, edges, _ = np.histogram2d(sel["truth"], sel["V1"], bins=72, range=[[0, 360], [0, 360]])
    centers = (edges[:-1] + edges[1:]) / 2
    zmax = float(np.quantile(counts[counts > 0], 0.98))
    within = (np.abs(circ_diff(sel["V1"], sel["truth"])) <= 10).mean() * 100
    fig = go.Figure(go.Heatmap(
        x=centers, y=centers, z=counts.T, zmin=0, zmax=zmax,
        colorscale=[[0, SURFACE], [0.03, "#cfe0f7"], [0.4, "#3987e5"], [1, "#0d366b"]],
        colorbar=dict(title="horas<br>(escala al p98)", thickness=12, len=0.8),
        hovertemplate="real %{x:.0f}°<br>estimada %{y:.0f}°<br>%{z:.0f} h<extra></extra>"))
    fig.add_trace(go.Scatter(x=[0, 360], y=[0, 360], mode="lines", name="estimada = real",
                             line=dict(color=INK_2, width=1, dash="dot"), hoverinfo="skip"))
    fig.update_xaxes(range=[0, 360], title_text="Θ1 horario del logger (real)", gridcolor=GRID, linecolor=BASELINE,
                     **DEG_TICKS)
    fig.update_yaxes(range=[0, 360], title_text="Estimada desde 5 min", gridcolor=GRID, linecolor=BASELINE,
                     scaleanchor="x", **DEG_TICKS)
    fig.update_layout(height=560, width=640, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, showlegend=False,
                      font=dict(family=FONT, size=12, color=INK_2), margin=dict(l=70, r=30, t=90, b=60),
                      title=dict(text=f"{LABEL} · dirección horaria estimada frente a real", x=0.01, y=0.985,
                                 yanchor="top", font=dict(size=16, color=INK)))
    fig.add_annotation(text=f"{len(sel)} h · {within:.0f} % a ≤ 10° de la diagonal", xref="paper", yref="paper",
                       x=0, y=1.08, xanchor="left", showarrow=False, font=dict(size=11, color=MUTED))
    return fig


NOTE = (
    "Real: WindDir_D1_WVT de la tabla de 60 min (media de vectores unitarios sobre las 720 muestras de 5 s). "
    "Estimada: vectores unitarios de los 12 WindDir_Avg de 5 min de la hora, sin los registros con velocidad 0. "
    "Se usan las mismas horas en ambos casos: hora completa (12 registros), velocidad horaria &gt; 0 y ambas "
    "direcciones definidas; la velocidad de las rosas es WS_ms_S_WVT en los dos casos. Calma: &lt; 0.5 m/s, sin "
    "pétalo. Frecuencia en % de todas las horas de la franja; las cuatro rosas comparten escala. Franjas por "
    "hora de inicio del intervalo, como en sarallenque_wind. Error = estimada − real, circular, en (−180°, 180°]. "
    "En el mapa de densidad, las esquinas superior izquierda e inferior derecha son diferencias pequeñas "
    "(0° ≈ 360°), no errores. "
    "El episodio de 48 h es la ventana completa con mayoría de viento del sector norte (±45°) cuyo error medio "
    "es el más cercano al error medio de todas las horas de ese sector.")


def main() -> None:
    df = pd.read_csv(OUT / f"aligned_{STATION}.csv.gz", parse_dates=["TIMESTAMP"])
    h = build_hourly(df)
    mask = valid_mask(h)
    ts = df["TIMESTAMP"]
    hour_start = ts - pd.Timedelta(hours=1)
    episode = pick_episode(h, hour_start, mask)
    figs = [rose_figure(h, hour_start, mask), series_figure(h, ts, mask, episode),
            episode_figure(df, h, episode), scatter_figure(h, mask)]
    body = "".join("<section>" + f.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False,
                                           config={"displaylogo": False}) + "</section>"
                   for i, f in enumerate(figs))
    out = OUT / f"caso_{STATION}.html"
    out.write_text(
        f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Caso {LABEL}</title>
<style>body{{font-family:{FONT};background:{PAGE};color:{INK};margin:0;padding:16px}}
main{{max-width:1000px;margin:auto;background:{SURFACE};border:1px solid rgba(11,11,11,.1);border-radius:8px;padding:12px}}
section{{margin-bottom:28px;overflow:hidden}}p{{color:{INK_2};font-size:13px}}</style></head><body><main>{body}<p>{NOTE}</p></main></body></html>""",
        encoding="utf-8")
    err = np.abs(circ_diff(h["V1"], h["truth"]))[mask]
    print(f"{LABEL}: {int(mask.sum())} h evaluadas · error medio estimada {err.mean():.2f}° · "
          f"episodio {episode[0]:%Y-%m-%d} → {episode[1]:%Y-%m-%d}")
    print(f"HTML: {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
