"""Prueba de congruencia del viento: ¿sigue cada estación el patrón común de la red cuando el viento es regional?

Con viento fuerte y uniforme en la zona (forzamiento sinóptico), los regímenes locales (valle, ladera, drenaje)
pierden peso y todas las estaciones deberían leer lo mismo, salvo un desvío propio del sitio (encauzamiento) que
es estable en el tiempo. Para cada estación y mes, en esas horas, se compara su dirección con el consenso de sus
vecinas (sin ella):
- d = estación − consenso. Su media circular es el desvío del sitio y su resultante R mide la congruencia:
  1 = la estación sigue el patrón con un desvío constante.
- Un escalón en el desvío fecha un giro, un traslado o un obstáculo nuevo; R baja = la estación no sigue el
  patrón (sitio abrigado, régimen propio, sensor que no responde). Para distinguir giro de cambio de sitio hay que
  mirar día y noche por separado fuera de estas horas (un giro mueve las dos franjas igual).
- No distingue espejo de giro: en estas horas el consenso viene casi siempre del O (~260°, p25–p75 247–264°) y
  la pendiente estación ~ consenso no es estable ni en estaciones sanas (probado el 2026-11-13).
- Las horas regionales son casi todas de 10 a 17 h: en la práctica es una prueba diurna.

Horas "regionales": al menos MIN_REFS vecinas a ≤ RADIUS_KM con dato, la mitad o más por encima de su propio
percentil STRONG_PCT de velocidad, y sus direcciones unitarias con resultante ≥ MIN_CONSENSUS_R.
Dirección: WindDir_D1_WVT donde existe (media vectorial del logger); si no, WindDir_Avg de met_corrected. Con
viento fuerte el aritmético rara vez cruza el norte, y si lo hace la resultante del consenso descarta la hora.
Vecinas: fuera los tramos de stations.WIND_EXCLUDED, REF_EXCLUDED y las estaciones de REF_DROP.

Uso (desde explorar_qaqc):
    uv run python met_viewer/congruence.py
Salida en met_viewer/output/: congruencia_viento.csv (estación × mes) y congruencia_viento.html.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from stations import DB_PATH, STATIONS, WIND_EXCLUDED

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corrections.store import connect_corrected  # noqa: E402

OUT = Path(__file__).parent / "output"
RADIUS_KM = 10.0
MIN_REFS = 3
STRONG_PCT = 0.80
MIN_CONSENSUS_R = 0.85
MIN_HOURS = 10          # horas regionales mínimas para dar el mes
TARGET_MIN_WS = 0.5     # regla de calma de la red
# Nunca de referencia: exposición dudosa o régimen propio (FINDINGS §8-§9).
REF_DROP = {"Dique_pie_botadero", "Chalsos", "Planta_Concentradora"}
# Giros sin corregir ni excluir del agrupamiento (FINDINGS §8): fuera solo como referencia.
REF_EXCLUDED: dict[str, list[tuple[str | None, str | None]]] = {
    "Cortadera": [("2026-09-13 11:00", None)],
    "Alto_Quellaveco": [("2026-09-15 11:00", None)],
    "Alto_Tala": [("2026-08-18 05:00", None)],
}


def load_wind() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Dirección (D1 si existe, si no WindDir_Avg corregido) y velocidad, pivotadas hora × estación."""
    con = connect_corrected(DB_PATH)
    try:
        df = con.execute(
            "SELECT estacion_id AS st, timestamp AS ts, coalesce(WindDir_D1_WVT, WindDir_Avg) AS wd, WS_ms_Avg AS ws "
            "FROM met_corrected WHERE WS_ms_Avg IS NOT NULL").df()
    finally:
        con.close()
    df = df[df["st"].isin(STATIONS)].drop_duplicates(["st", "ts"], keep="last")
    return df.pivot(index="ts", columns="st", values="wd"), df.pivot(index="ts", columns="st", values="ws")


def mask_segments(frame: pd.DataFrame, segments: dict[str, list[tuple[str | None, str | None]]]) -> pd.DataFrame:
    out = frame.copy()
    for st, spans in segments.items():
        if st not in out:
            continue
        for a, b in spans:
            sel = np.ones(len(out), bool)
            if a:
                sel &= out.index >= pd.Timestamp(a)
            if b:
                sel &= out.index < pd.Timestamp(b)
            out.loc[sel, st] = np.nan
    return out


def neighbours(st: str, candidates: list[str]) -> list[str]:
    x, y = STATIONS[st].easting, STATIONS[st].northing
    return [o for o in candidates if o != st
            and np.hypot(STATIONS[o].easting - x, STATIONS[o].northing - y) / 1000 <= RADIUS_KM]


def resultant(rad: pd.Series) -> tuple[float, float]:
    """(dirección media en grados, longitud de la resultante) de ángulos en radianes."""
    s, c = np.sin(rad).mean(), np.cos(rad).mean()
    return float(np.rad2deg(np.arctan2(s, c))), float(np.hypot(s, c))


def congruence(wd: pd.DataFrame, ws: pd.DataFrame) -> pd.DataFrame:
    ref_wd = mask_segments(mask_segments(wd, WIND_EXCLUDED), REF_EXCLUDED)
    ref_wd = ref_wd.drop(columns=[c for c in REF_DROP if c in ref_wd])
    ref_wd = ref_wd.where(ws.reindex(columns=ref_wd.columns) >= TARGET_MIN_WS)
    strong = ws.ge(ws.quantile(STRONG_PCT))
    rows = []
    for st in sorted(wd.columns):
        refs = neighbours(st, list(ref_wd.columns))
        if len(refs) < MIN_REFS:
            continue
        rad = np.deg2rad(ref_wd[refs])
        n = rad.notna().sum(axis=1)
        sn, cs = np.sin(rad).sum(axis=1) / n, np.cos(rad).sum(axis=1) / n
        cons_r = np.hypot(sn, cs)
        frac_strong = (strong[refs] & rad.notna()).sum(axis=1) / n
        regional = (n >= MIN_REFS) & (frac_strong >= 0.5) & (cons_r >= MIN_CONSENSUS_R)
        target = wd[st].where(ws[st] >= TARGET_MIN_WS)
        ok = regional & target.notna()
        cons = np.arctan2(sn[ok], cs[ok])
        tgt = np.deg2rad(target[ok])
        d = tgt - cons
        month = ok[ok].index.to_period("M")
        for m, idx in pd.Series(range(len(d)), index=month).groupby(level=0):
            if len(idx) < MIN_HOURS:
                continue
            off, r_rot = resultant(d.iloc[idx.to_numpy()])
            dd = np.abs((np.rad2deg(d.iloc[idx.to_numpy()]) + 180) % 360 - 180)
            rows.append({"station": st, "month": str(m), "hours": len(idx), "refs": len(refs),
                         "offset": round(off, 1), "r_congruence": round(r_rot, 3),
                         "agree_45": round(float((dd < 45).mean() * 100), 1),
                         "consensus_dir": round(resultant(pd.Series(cons.to_numpy()[idx.to_numpy()]))[0] % 360, 1)})
    return pd.DataFrame(rows)


def heatmaps(res: pd.DataFrame) -> go.Figure:
    months = sorted(res["month"].unique())
    stations = sorted(res["station"].unique(), reverse=True)
    grid = lambda col: res.pivot(index="station", columns="month", values=col).reindex(index=stations, columns=months)
    off, rr, n, agree = grid("offset"), grid("r_congruence"), grid("hours"), grid("agree_45")
    text = [[f"{s} · {m}<br>horas: {n.loc[s, m]:.0f}<br>desvío: {off.loc[s, m]:+.0f}°<br>R: {rr.loc[s, m]:.2f}"
             f"<br>a < 45°: {agree.loc[s, m]:.0f} %" if pd.notna(n.loc[s, m]) else ""
             for m in months] for s in stations]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=("Desvío respecto al consenso (estación − consenso, °)",
                                        "Congruencia: R del desvío (1 = desvío constante)"))
    common = dict(x=months, y=stations, text=text, hoverinfo="text", xgap=1, ygap=1)
    fig.add_trace(go.Heatmap(z=off.to_numpy(), zmin=-180, zmax=180, colorscale="RdBu", zmid=0,
                             colorbar=dict(len=0.45, y=0.78, title="°"), **common), row=1, col=1)
    fig.add_trace(go.Heatmap(z=rr.to_numpy(), zmin=0, zmax=1, colorscale="Blues",
                             colorbar=dict(len=0.45, y=0.22, title="R"), **common), row=2, col=1)
    fig.update_layout(height=max(800, 2 * 22 * len(stations) + 200), template="plotly_white",
                      title=f"Congruencia del viento con la red en horas regionales (vecinas a ≤ {RADIUS_KM:.0f} km, "
                            f"≥ {MIN_REFS}, la mitad sobre su p{STRONG_PCT * 100:.0f} de velocidad, "
                            f"consenso con R ≥ {MIN_CONSENSUS_R}; meses con ≥ {MIN_HOURS} h)")
    return fig


def main() -> None:
    wd, ws = load_wind()
    res = congruence(wd, ws)
    OUT.mkdir(exist_ok=True)
    res.to_csv(OUT / "congruencia_viento.csv", index=False)
    heatmaps(res).write_html(OUT / "congruencia_viento.html", include_plotlyjs="cdn")
    summary = res.groupby("station").agg(months=("month", "size"), hours=("hours", "sum"),
                                         r_congruence=("r_congruence", "median"),
                                         agree_45=("agree_45", "median"))
    print(summary.round(2).to_string())
    print(f"\n{OUT / 'congruencia_viento.csv'}\n{OUT / 'congruencia_viento.html'}")


if __name__ == "__main__":
    main()
