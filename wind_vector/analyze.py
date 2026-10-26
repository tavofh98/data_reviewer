"""Error de la dirección horaria derivada de registros de 5 min frente al Θ1 del logger.

Verdad: WindDir_D1_WVT de la tabla de 60 min (Θ1 sobre 720 muestras de 5 s).
Variantes que se evalúan, todas calculadas con los 12 registros de 5 min de cada hora:
  V0  WindDir_Avg horario del logger (media aritmética; es lo que hoy usa anglo_reporte)
  V1  vectores unitarios de WindDir_Avg 5 min, peso 1 (sin calmas)
  V2  vectores de WindDir_Avg 5 min ponderados por velocidad
  V3  vectores unitarios de D1 5 min, peso 1 (sin calmas)
  V4  vectores de D1 5 min ponderados por R (recuperada de SD1 con Yamartino inverso)
  V5  vectores de D1 5 min ponderados por velocidad y R: aproxima Θu, NO es una variante
      de Θ1; sirve para medir cuánto separa Θ1 de Θu.

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.analyze

Salida: wind_vector/output/RESULTADOS.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
STATIONS = ("cortadera", "papujune", "quellaveco")
BLOCKS = [f"m{i:02d}" for i in range(1, 13)]
R_MIN = 0.05  # misma resultante mínima que anglo_reporte/main.py
MIN_COVERAGE = 0.8

# Yamartino: σ = asin(ε)·[1 + (2/√3 − 1)·ε³], con ε = sqrt(1 − R²). Monótona en ε,
# así que se invierte por interpolación sobre una malla fina.
_EPS = np.linspace(0.0, 1.0, 20001)
_SIGMA = np.degrees(np.arcsin(_EPS) * (1.0 + (2.0 / np.sqrt(3.0) - 1.0) * _EPS**3))

VARIANTS = {
    "V0": "WindDir_Avg horario (lo actual)",
    "V1": "unitarios de Avg 5 min",
    "V2": "Avg 5 min ponderado por velocidad",
    "V3": "unitarios de D1 5 min",
    "V4": "D1 5 min ponderado por R",
    "V5": "D1 5 min por velocidad y R (≈Θu)",
}


def circ_diff(a, b):
    """Diferencia circular a − b en grados, en (−180, 180]."""
    return (np.asarray(a, float) - np.asarray(b, float) + 180.0) % 360.0 - 180.0


def sigma_to_r(sigma_deg):
    """Longitud resultante R a partir de la desviación de Yamartino (grados)."""
    sigma = np.clip(np.asarray(sigma_deg, float), 0.0, _SIGMA[-1])
    eps = np.interp(sigma, _SIGMA, _EPS)
    return np.sqrt(1.0 - eps**2)


def block(df: pd.DataFrame, var: str) -> np.ndarray:
    return df[[f"{var}_{b}" for b in BLOCKS]].to_numpy(float)


def vector_direction(theta_deg: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """Dirección (0–360) de la suma de vectores unitarios ponderados; NaN si el peso es 0."""
    w = np.where(np.isnan(theta_deg) | np.isnan(weight), 0.0, weight)
    rad = np.deg2rad(np.nan_to_num(theta_deg))
    s, c = (w * np.sin(rad)).sum(axis=1), (w * np.cos(rad)).sum(axis=1)
    out = np.rad2deg(np.arctan2(s, c)) % 360.0
    return np.where(w.sum(axis=1) > 0, out, np.nan)


def build_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Una columna por variante más la verdad ('truth') y las covariables de cada hora."""
    ws = block(df, "WS_ms_Avg")
    avg, d1, sd1 = block(df, "WindDir_Avg"), block(df, "WindDir_D1_WVT"), block(df, "WindDir_SD1_WVT")
    moving = (ws > 0).astype(float)
    r = sigma_to_r(sd1)
    res = pd.DataFrame(index=df.index)
    res["truth"] = df["WindDir_D1_WVT_h"].to_numpy(float)
    res["V0"] = df["WindDir_Avg_h"].to_numpy(float)
    res["V1"] = vector_direction(avg, moving)
    res["V2"] = vector_direction(avg, ws)
    res["V3"] = vector_direction(d1, moving)
    res["V4"] = vector_direction(d1, r * moving)
    res["V5"] = vector_direction(d1, ws * r)
    res["ws_h"] = df["WS_ms_S_WVT_h"].to_numpy(float)
    res["sd1_h"] = df["WindDir_SD1_WVT_h"].to_numpy(float)
    res["complete"] = df["n_5min"].to_numpy() == 12
    return res


def valid_mask(h: pd.DataFrame) -> pd.Series:
    """Horas completas, con viento (no calma) y con todas las variantes definidas."""
    cols = ["truth"] + list(VARIANTS)
    return h["complete"] & (h["ws_h"] > 0) & h[cols].notna().all(axis=1)


def error_table(h: pd.DataFrame, mask: pd.Series, groups: pd.Series | None = None) -> pd.DataFrame:
    rows = []
    sel = h[mask]
    keys = [("todas", slice(None))] if groups is None else [(k, groups[mask] == k) for k in groups[mask].dropna().unique()]
    for label, cond in keys:
        sub = sel if isinstance(cond, slice) else sel[cond]
        for v in VARIANTS:
            e = np.abs(circ_diff(sub[v], sub["truth"]))
            if len(e) == 0:
                continue
            rows.append({
                "grupo": label, "variante": v, "n": len(e), "media": e.mean(), "mediana": np.median(e),
                "p95": np.quantile(e, 0.95), "p99": np.quantile(e, 0.99), "max": e.max(),
                "%>5°": (e > 5).mean() * 100, "%>10°": (e > 10).mean() * 100, "%>30°": (e > 30).mean() * 100,
            })
    return pd.DataFrame(rows)


def circular_stats(theta: pd.Series) -> tuple[float, float]:
    """Media y desviación circulares como en anglo_reporte/main.py::_stats_circular (NaN si R < R_MIN)."""
    rad = np.deg2rad(theta.to_numpy(float))
    s, c = np.sin(rad).mean(), np.cos(rad).mean()
    r = float(np.hypot(s, c))
    if r < R_MIN:
        return np.nan, np.nan
    return float(np.rad2deg(np.arctan2(s, c)) % 360.0), float(np.rad2deg(np.sqrt(-2.0 * np.log(r))))


def window_table(h: pd.DataFrame, mask: pd.Series, ts: pd.Series) -> pd.DataFrame:
    """Error de la media circular del periodo (lo que entrega el reporte) frente a la hecha con la verdad."""
    sel = h[mask].set_index(pd.DatetimeIndex(ts[mask]))
    rows = []
    for label, freq in (("día", "D"), ("semana", "W"), ("mes", "MS")):
        for key, g in sel.groupby(pd.Grouper(freq=freq)):
            expected = {"D": 24, "W": 168, "MS": key.days_in_month * 24}[freq]
            if len(g) < MIN_COVERAGE * expected:
                continue
            t_mean, t_sd = circular_stats(g["truth"])
            for v in VARIANTS:
                m, sd = circular_stats(g[v])
                rows.append({"ventana": label, "variante": v, "t_mean": t_mean, "mean": m,
                             "t_sd": t_sd, "sd": sd})
    w = pd.DataFrame(rows)
    w["err"] = np.abs(circ_diff(w["mean"], w["t_mean"]))
    w["err_sd"] = np.abs(w["sd"] - w["t_sd"])
    w["blank_mismatch"] = w["mean"].isna() != w["t_mean"].isna()
    out = []
    for (win, v), g in w.groupby(["ventana", "variante"], sort=False):
        e = g["err"].dropna()
        out.append({"ventana": win, "variante": v, "n": len(g), "media": e.mean(), "mediana": e.median(),
                    "p95": e.quantile(0.95), "max": e.max(), "%>5°": (e > 5).mean() * 100,
                    "%>10°": (e > 10).mean() * 100, "err σ medio": g["err_sd"].mean(),
                    "blanco distinto": int(g["blank_mismatch"].sum())})
    return pd.DataFrame(out)


def to_md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    fmt = lambda x: f"{x:.2f}" if isinstance(x, (float, np.floating)) else str(x)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(fmt(x) for x in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def main() -> None:
    parts = ["# Resultados: dirección horaria derivada de 5 min frente a Θ1 del logger\n",
             "Variantes: " + "; ".join(f"**{k}** {v}" for k, v in VARIANTS.items()) + ".\n",
             "Errores en grados, circulares. Horas evaluadas: completas (12/12), sin calma horaria "
             "(WS_S_WVT > 0) y con todas las variantes definidas.\n"]
    for st in STATIONS:
        df = pd.read_csv(OUT / f"aligned_{st}.csv.gz", parse_dates=["TIMESTAMP"])
        h = build_hourly(df)
        mask = valid_mask(h)
        north = np.abs(circ_diff(h["truth"], 0.0)) <= 45
        h["sector"] = np.where(north, "norte (±45°)", "resto")
        h["variabilidad"] = pd.cut(h["sd1_h"], [-1, 15, 30, 50, 200], labels=["SD1<15", "15-30", "30-50", ">50"])
        h["año"] = df["TIMESTAMP"].dt.year.astype(str)
        parts.append(f"\n## {st}\n")
        parts.append(f"Horas en la tabla de 60 min: {len(h)}; evaluadas: {int(mask.sum())}; "
                     f"calmas horarias excluidas: {int((h['complete'] & (h['ws_h'] <= 0)).sum())}.\n")
        parts.append("### Error por hora\n\n" + to_md(error_table(h, mask)) + "\n")
        parts.append("### Por sector del viento real\n\n" + to_md(error_table(h, mask, h["sector"])) + "\n")
        parts.append("### Por variabilidad intra-hora (SD1 horaria)\n\n"
                     + to_md(error_table(h, mask, h["variabilidad"].astype(object))) + "\n")
        parts.append("### Por año (solo V0, V1, V4)\n\n"
                     + to_md(error_table(h, mask, h["año"]).query("variante in ['V0','V1','V4']")) + "\n")
        parts.append("### Media del periodo (como la entrega el reporte)\n\n"
                     + to_md(window_table(h, mask, df["TIMESTAMP"])) + "\n")
        print(f"{st}: {int(mask.sum())} horas evaluadas")
    (OUT / "RESULTADOS.md").write_text("\n".join(parts), encoding="utf-8")
    print("->", OUT / "RESULTADOS.md")


if __name__ == "__main__":
    main()
