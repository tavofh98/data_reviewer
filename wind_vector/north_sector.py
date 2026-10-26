"""El sector norte: ¿qué se puede corregir de la dirección horaria estimada desde WindDir_Avg de 5 min?

Parte A  Dónde cae en WindDir_Avg un viento que el logger (D1) sitúa cerca del norte, por registro de 5 min.
Parte B  Heurísticas por hora para reducir el error (mediana circular, descarte de registros ruidosos).
Parte C  Precisión al excluir el sector norte: por la dirección real (optimista) y por reglas que solo
         usan los 5 min (las que se podrían aplicar en la práctica).

Verdad: WindDir_D1_WVT horario. Mismas horas válidas que analyze.py.

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.north_sector

Salida: wind_vector/output/RESULTADOS_NORTE.md
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from wind_vector.case_study import (BASELINE, ESTIMATE_COLOR, FONT, GRID, INK, INK_2, MUTED, PAGE, REAL_COLOR, SPEED_COLORS,
                                    SURFACE)
from wind_vector.analyze import OUT, STATIONS, block, build_hourly, circ_diff, to_md, valid_mask, vector_direction

THRESHOLDS = (30, 45, 60)       # descarte respecto a la mediana circular de la hora (grados)
SAFE_LOW, SAFE_HIGH = 20.0, 340.0
NORTH_HALF_WIDTH = 20.0


def abs_diff(a, b):
    """|diferencia circular|; conserva el índice si `a` es una Series."""
    out = np.abs(circ_diff(a, b))
    return pd.Series(out, index=a.index) if isinstance(a, pd.Series) else out


def medoid(avg: np.ndarray, usable: np.ndarray) -> np.ndarray:
    """Mediana circular de cada hora: el registro de 5 min que minimiza la suma de distancias circulares."""
    dist = abs_diff(avg[:, :, None], avg[:, None, :])
    dist = np.where(usable[:, None, :], dist, 0.0).sum(axis=2)
    dist = np.where(usable, dist, np.inf)
    best = dist.argmin(axis=1)
    return np.where(usable.any(axis=1), avg[np.arange(len(avg)), best], np.nan)


def error_row(label: str, err: np.ndarray) -> dict:
    if len(err) == 0:
        return {"grupo": label, "n": 0}
    return {"grupo": label, "n": len(err), "media": err.mean(), "mediana": np.median(err),
            "p95": np.quantile(err, 0.95), "%>10°": (err > 10).mean() * 100, "%>30°": (err > 30).mean() * 100}


def part_a(df: pd.DataFrame) -> str:
    avg = np.concatenate([df[f"WindDir_Avg_{b}"].to_numpy(float) for b in ("m%02d" % i for i in range(1, 13))])
    d1 = np.concatenate([df[f"WindDir_D1_WVT_{b}"].to_numpy(float) for b in ("m%02d" % i for i in range(1, 13))])
    sd1 = np.concatenate([df[f"WindDir_SD1_WVT_{b}"].to_numpy(float) for b in ("m%02d" % i for i in range(1, 13))])
    ws = np.concatenate([df[f"WS_ms_Avg_{b}"].to_numpy(float) for b in ("m%02d" % i for i in range(1, 13))])
    ok = ~np.isnan(avg) & ~np.isnan(d1) & ~np.isnan(sd1) & (ws > 0)
    avg, d1, sd1 = avg[ok], d1[ok], sd1[ok]
    off = abs_diff(avg, d1)
    dist_north = abs_diff(d1, 0.0)
    rows = []
    for label, sel in (("D1 a ≤ 20° del norte", dist_north <= 20), ("D1 a 20–45° del norte", (dist_north > 20) & (dist_north <= 45)),
                       ("D1 a > 45° del norte", dist_north > 45)):
        o = off[sel]
        rows.append({"registros de 5 min": label, "n": int(sel.sum()), "% con Avg a ≤ 10° de D1": (o <= 10).mean() * 100,
                     "% con 10–90°": ((o > 10) & (o <= 90)).mean() * 100, "% con > 90°": (o > 90).mean() * 100,
                     "SD1 mediana": float(np.median(sd1[sel]))})
    avg_north = abs_diff(avg, 0.0) <= 20
    conf = {"Avg a ≤ 20° del norte": int(avg_north.sum()), "D1 a ≤ 20° del norte": int((dist_north <= 20).sum()),
            "de los Avg cerca del norte, D1 también": f"{(dist_north[avg_north] <= 20).mean() * 100:.1f} %",
            "de los D1 cerca del norte, Avg también": f"{(avg_north[dist_north <= 20]).mean() * 100:.1f} %"}
    return to_md(pd.DataFrame(rows)) + "\n\n" + "\n".join(f"- {k}: {v}" for k, v in conf.items())


def build_variants(df: pd.DataFrame, h: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    avg, ws = block(df, "WindDir_Avg"), block(df, "WS_ms_Avg")
    usable = ~np.isnan(avg) & (np.nan_to_num(ws) > 0)
    med = medoid(avg, usable)
    out = h[["truth", "V0", "V1"]].copy()
    out["MED"] = med
    for t in THRESHOLDS:
        keep = usable & (abs_diff(avg, med[:, None]) <= t)
        out[f"R{t}"] = vector_direction(avg, keep.astype(float))
    return out, avg, usable


def part_b(h: pd.DataFrame, v: pd.DataFrame, mask: pd.Series) -> str:
    names = {"V0": "V0 WindDir_Avg horario", "V1": "V1 unitarios de Avg 5 min", "MED": "MED mediana circular de la hora",
             **{f"R{t}": f"R{t} sin registros a > {t}° de la mediana" for t in THRESHOLDS}}
    north = abs_diff(v["truth"], 0.0)
    rows = []
    for label, sel in (("todas las horas", mask), ("real a ≤ 45° del norte", mask & (north <= 45)),
                       ("real a ≤ 20° del norte", mask & (north <= 20)), ("real a > 45° del norte", mask & (north > 45))):
        for col, name in names.items():
            r = error_row(f"{label} · {name}", abs_diff(v.loc[sel, col], v.loc[sel, "truth"]).to_numpy())
            rows.append(r)
    return to_md(pd.DataFrame(rows))


def acceptance_rules(v: pd.DataFrame, avg: np.ndarray, usable: np.ndarray) -> dict[str, np.ndarray]:
    """Reglas que deciden si una hora es fiable usando solo sus 12 WindDir_Avg de 5 min (sin la verdad)."""
    med = v["MED"].to_numpy()
    all_inside = (((avg >= SAFE_LOW) & (avg <= SAFE_HIGH)) | ~usable).all(axis=1)
    spread = np.where(usable, abs_diff(avg, med[:, None]), 0.0).max(axis=1)
    both = usable[:, 1:] & usable[:, :-1]
    jump = np.where(both, abs_diff(avg[:, 1:], avg[:, :-1]), 0.0).max(axis=1)
    return {
        "R1 WindDir_Avg horario en 20–340°": ((v["V0"] >= SAFE_LOW) & (v["V0"] <= SAFE_HIGH)).to_numpy(),
        "R2 los 12 Avg de 5 min en 20–340°": all_inside,
        "R3 R2 y salto máx. entre registros ≤ 60°": all_inside & (jump <= 60),
        "R4 R2 y dispersión máx. a la mediana ≤ 45°": all_inside & (spread <= 45),
        "R5 R2 y dispersión ≤ 20°": all_inside & (spread <= 20),
    }


def part_c(h: pd.DataFrame, v: pd.DataFrame, avg: np.ndarray, usable: np.ndarray, mask: pd.Series) -> str:
    err = {c: abs_diff(v[c], v["truth"]) for c in ("V0", "V1", "R45")}
    north = abs_diff(v["truth"], 0.0)
    # A) Por la dirección real (optimista: se conoce la verdad para decidir)
    rows = []
    for label, sel in (("real fuera de ±20° del norte (20–340°)", north > 20), ("real fuera de ±30°", north > 30),
                       ("real fuera de ±45°", north > 45), ("real dentro de ±20°", north <= 20)):
        for c in ("V0", "V1", "R45"):
            rows.append({**error_row(f"{label} · {c}", err[c][mask & sel].to_numpy()), "% de las horas": (mask & sel).sum() / mask.sum() * 100})
    part1 = to_md(pd.DataFrame(rows))
    # B) Reglas aplicables con solo los 5 min
    rules = acceptance_rules(v, avg, usable)
    rows = []
    near20, near45 = (north <= 20).to_numpy(), (north <= 45).to_numpy()
    big = (err["V1"] > 30).to_numpy()
    for name, accept in rules.items():
        sel = mask.to_numpy() & accept
        e1, e7 = err["V1"].to_numpy()[sel], err["R45"].to_numpy()[sel]
        rows.append({"regla": name, "horas aceptadas %": sel.sum() / mask.sum() * 100,
                     "V1 media": e1.mean(), "V1 p95": np.quantile(e1, 0.95), "V1 %>10°": (e1 > 10).mean() * 100,
                     "V1 %>30°": (e1 > 30).mean() * 100, "R45 media": e7.mean(), "R45 %>10°": (e7 > 10).mean() * 100,
                     "aceptadas con real ≤ 20° del norte %": near20[sel].mean() * 100,
                     "aceptadas con real ≤ 45° del norte %": near45[sel].mean() * 100,
                     "% de los errores V1 > 30° que quedan dentro": (sel & big).sum() / max((mask.to_numpy() & big).sum(), 1) * 100})
    return part1 + "\n\n" + to_md(pd.DataFrame(rows))


def bin_stats(v: pd.DataFrame, mask: pd.Series, accept: np.ndarray) -> pd.DataFrame:
    """Por cada tramo de 10° de la dirección real: error medio de V0, de V1, de V1 solo en horas aceptadas y % aceptado."""
    sel = mask.to_numpy()
    truth = v["truth"].to_numpy()[sel]
    frame = pd.DataFrame({"bin": (truth // 10).astype(int) % 36,
                          "e0": abs_diff(v["V0"], v["truth"]).to_numpy()[sel],
                          "e1": abs_diff(v["V1"], v["truth"]).to_numpy()[sel], "acc": accept[sel]})
    grouped = frame.groupby("bin")
    out = pd.DataFrame({"n": grouped.size(), "V0": grouped["e0"].mean(), "V1": grouped["e1"].mean(),
                        "pct_acc": grouped["acc"].mean() * 100})
    out["V1_acc"] = frame[frame["acc"]].groupby("bin")["e1"].mean()
    return out.reindex(range(36))


def figure(stats: dict[str, pd.DataFrame]) -> go.Figure:
    centers = np.arange(36) * 10 + 5
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.08)
    specs = (("V0", "WindDir_Avg horario (V0)", INK_2, "dash"), ("V1", "Estimada desde 5 min (V1)", ESTIMATE_COLOR, "solid"),
             ("V1_acc", "V1 solo en horas aceptadas por R4", REAL_COLOR, "solid"))
    names = list(stats)
    for i, st in enumerate(names):
        s = stats[st]
        for col, label, color, dash in specs:
            fig.add_trace(go.Scatter(x=centers, y=s[col].round(2), mode="lines+markers", name=label, legendgroup=col,
                                     line=dict(color=color, width=2, dash=dash), marker=dict(size=6),
                                     showlegend=(i == 0), visible=(i == 0),
                                     hovertemplate="real %{x}°<br>%{y:.1f}°<extra>" + label + "</extra>"), row=1, col=1)
        fig.add_trace(go.Bar(x=centers, y=s["pct_acc"].round(1), name="% de horas aceptadas por R4", marker_color=SPEED_COLORS[0],
                             marker_line=dict(color=SURFACE, width=1), showlegend=(i == 0), visible=(i == 0), customdata=s["n"],
                             hovertemplate="real %{x}°<br>%{y:.0f} % aceptadas (de %{customdata} h)<extra></extra>"), row=2, col=1)
    per = len(specs) + 1
    buttons = [dict(label=st, method="update", args=[{"visible": [j // per == i for j in range(per * len(names))]}])
               for i, st in enumerate(names)]
    fig.update_xaxes(range=[0, 360], tickvals=[0, 45, 90, 135, 180, 225, 270, 315, 360],
                     ticktext=["N", "NE", "E", "SE", "S", "SO", "O", "NO", "N"], gridcolor=GRID, linecolor=BASELINE,
                     title_text="Dirección real (Θ1 horario del logger), tramos de 10°", row=2, col=1)
    fig.update_yaxes(title_text="Error medio (°)", gridcolor=GRID, linecolor=BASELINE, row=1, col=1)
    fig.update_yaxes(title_text="% aceptadas", range=[0, 100], gridcolor=GRID, linecolor=BASELINE, row=2, col=1)
    fig.update_layout(height=620, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, hovermode="x unified",
                      font=dict(family=FONT, size=12, color=INK_2), margin=dict(l=60, r=30, t=130, b=50),
                      title=dict(text="Error de la dirección horaria estimada según la dirección real", x=0.01, y=0.985,
                                 yanchor="top", font=dict(size=17, color=INK)),
                      legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom"),
                      updatemenus=[dict(type="buttons", direction="right", x=0, xanchor="left", y=1.14, yanchor="bottom",
                                        showactive=True, bgcolor=SURFACE, bordercolor=MUTED, font=dict(color=INK),
                                        buttons=buttons)])
    return fig


FIGURE_NOTE = ("Error circular medio de la dirección horaria frente al Θ1 del logger, por tramos de 10° de la dirección "
               "real. R4: los 12 WindDir_Avg de 5 min de la hora dentro de 20–340° y ninguno a más de 45° de la mediana "
               "circular de la hora. Barras: porcentaje de las horas de cada tramo que R4 acepta.")


def main() -> None:
    stats: dict[str, pd.DataFrame] = {}
    parts = ["# El sector norte: qué se puede corregir y con qué precisión\n",
             "Verdad: `WindDir_D1_WVT` horario. Errores circulares en grados. Misma selección de horas que `analyze.py`. "
             "V0 = `WindDir_Avg` horario; V1 = vectores unitarios de Avg 5 min; MED = mediana circular de los 12 "
             "registros; R*t* = vectores unitarios sin los registros a más de *t*° de la mediana de la hora.\n"]
    for st in STATIONS:
        df = pd.read_csv(OUT / f"aligned_{st}.csv.gz", parse_dates=["TIMESTAMP"])
        h = build_hourly(df)
        mask = valid_mask(h)
        v, avg, usable = build_variants(df, h)
        mask = mask & v[["MED"] + [f"R{t}" for t in THRESHOLDS]].notna().all(axis=1)
        parts += [f"\n## {st}\n", f"Horas evaluadas: {int(mask.sum())}.\n",
                  "### A. Dónde cae en WindDir_Avg el viento que D1 sitúa cerca del norte (registros de 5 min)\n\n" + part_a(df) + "\n",
                  "### B. Heurísticas por hora\n\n" + part_b(h, v, mask) + "\n",
                  "### C. Precisión al excluir el sector norte\n\n" + part_c(h, v, avg, usable, mask) + "\n"]
        stats[st] = bin_stats(v, mask, acceptance_rules(v, avg, usable)["R4 R2 y dispersión máx. a la mediana ≤ 45°"])
        print(f"{st}: {int(mask.sum())} horas")
    (OUT / "RESULTADOS_NORTE.md").write_text("\n".join(parts), encoding="utf-8")
    body = figure(stats).to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False})
    (OUT / "norte_error_por_sector.html").write_text(
        f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Error por sector</title>
<style>body{{font-family:{FONT};background:{PAGE};color:{INK};margin:0;padding:16px}}
main{{max-width:1000px;margin:auto;background:{SURFACE};border:1px solid rgba(11,11,11,.1);border-radius:8px;padding:12px}}
p{{color:{INK_2};font-size:13px}}</style></head><body><main>{body}<p>{FIGURE_NOTE}</p></main></body></html>""",
        encoding="utf-8")
    print("->", OUT / "RESULTADOS_NORTE.md", "y norte_error_por_sector.html")


if __name__ == "__main__":
    main()
