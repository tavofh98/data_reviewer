"""Dirección horaria vectorial de una estación sin D1, reconstruida desde sus registros de 5 min.

Aplica north_mixture en la configuración de su validación externa: σ, etapa 1 y etapa 2 entrenadas con
las tres estaciones con D1 (analyze.STATIONS); la etapa 2, con probabilidades de la etapa 1 fuera de
muestra. Cada registro de 5 min entra en la hora como vector blando P(H1)·u(μ) + (1 − P(H1))·u(A).
La estación reconstruida no tiene D1, así que el error no se mide aquí (ver INFORME.md, sección 3.8).

Salida: output/rescue_<estación>.csv.gz, una fila por hora (etiqueta al final, como la base) con al menos
MIN_RECORDS registros con viento. Columnas: direction (reconstruida), v1 (media de vectores unitarios de
WindDir_Avg sin corregir), resultant (longitud del vector medio), frac_h1 (fracción de registros tomados
como mezcla del norte), ws (velocidad media de 5 min) y records.
corrections/build_corrections.py lee ese fichero (tipo "vector_rescue"); al llegar 5 min nuevos hay que
regenerarlo antes de reconstruir corrections.db.

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.rescue Chalsos
"""
from __future__ import annotations

import gc
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from wind_vector.analyze import OUT, STATIONS
from wind_vector.north_mixture import (BASE, NEAR_NORTH, ROLL, SIGMA_FEATURES, Store, abs_diff, build_base,
                                       build_physics, features, fit_classifier, mixture_direction, others,
                                       rolling, stage2_matrix, training_matrix)

REFERENCES = Path(__file__).resolve().parents[2] / "references"
# Table3 (5 min) de las estaciones que se reconstruyen.
SOURCES = {"Chalsos": REFERENCES / "AAQ_Est_Chalsos_CR310_Table3.dat"}
MIN_RECORDS = 9   # de 12 registros de 5 min por hora, igual que corrections/build_corrections.py
SIGMA_COLS = [BASE.index(c) for c in SIGMA_FEATURES]


def output_path(station: str) -> Path:
    return OUT / f"rescue_{station.lower()}.csv.gz"


def read_5min(path: Path) -> pd.DataFrame:
    """Serie regular de 5 min con A (WindDir_Avg), ws y wsmax; gana el último registro duplicado."""
    cols = ["TIMESTAMP", "WS_ms_Avg", "WS_ms_Max", "WindDir_Avg"]
    raw = pd.read_csv(path, skiprows=[0, 2, 3], na_values=["NAN"], usecols=cols, dtype=str)
    raw["TIMESTAMP"] = pd.to_datetime(raw["TIMESTAMP"])
    for c in cols[1:]:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw = raw.drop_duplicates("TIMESTAMP", keep="last").sort_values("TIMESTAMP").set_index("TIMESTAMP")
    raw = raw[raw.index.minute % 5 == 0]
    return pd.DataFrame({"A": raw["WindDir_Avg"], "ws": raw["WS_ms_Avg"], "wsmax": raw["WS_ms_Max"]}).asfreq("5min")


def train_models(store: Store):
    """σ, etapa 1 y etapa 2 entrenadas con las tres estaciones con D1 (como en north_mixture.main)."""

    def sigma_model(train):
        xs, ys = [], []
        for st in train:
            b = store.load(st, "base")
            ok = b["labeled"] & ~np.isnan(b["SD1"])
            xs.append(b["F"][ok][:, SIGMA_COLS]); ys.append(b["SD1"][ok])
        return HistGradientBoostingRegressor(max_iter=300, random_state=0).fit(np.vstack(xs), np.concatenate(ys))

    for st in STATIONS:
        build_base(store, st)
        gc.collect()
    for st in STATIONS:
        sigma = np.clip(sigma_model(others(st)).predict(store.load(st, "base")["F"][:, SIGMA_COLS]), 1.0, 120.0)
        build_physics(store, st, sigma)
        gc.collect()
    p1_pair = {st: fit_classifier(*training_matrix(store, others(st))).predict_proba(store.load(st, "phys")["F1"])[:, 1]
               for st in STATIONS}
    train = list(STATIONS)
    return sigma_model(train), fit_classifier(*training_matrix(store, train)), \
        fit_classifier(*training_matrix(store, train, p1_pair))


def reconstruct(s: pd.DataFrame, sigma_reg, stage1, stage2) -> pd.DataFrame:
    """Probabilidad de mezcla del norte por registro y dirección horaria (mismas covariables que build_physics)."""
    F = features(s)[BASE].to_numpy(np.float32)
    sigma = np.clip(sigma_reg.predict(F[:, SIGMA_COLS]), 1.0, 120.0)
    a = s["A"].to_numpy(float)
    moving = ((s["ws"] > 0) & s["A"].notna()).to_numpy()
    mu = mixture_direction(a, sigma)
    cand = np.where(moving, np.where(abs_diff(a, 0.0) < abs_diff(mu, 0.0), a, mu), np.nan)
    near = (abs_diff(cand, 0.0) <= NEAR_NORTH).astype(float)
    bigjump = (F[:, BASE.index("jump_prev")] > 60).astype(float)
    extra = [sigma, abs_diff(mu, 0.0) / sigma] + [rolling(near, w) for w in ROLL] + [rolling(bigjump, w) for w in ROLL]
    F1 = np.column_stack([F] + [np.asarray(e, np.float32) for e in extra])
    p = np.where(moving, stage2.predict_proba(stage2_matrix(F1, stage1.predict_proba(F1)[:, 1]))[:, 1], np.nan)

    ra, rm = np.deg2rad(a), np.deg2rad(mu)
    rec = pd.DataFrame({
        "x": p * np.cos(rm) + (1 - p) * np.cos(ra), "y": p * np.sin(rm) + (1 - p) * np.sin(ra),
        "x1": np.where(moving, np.cos(ra), np.nan), "y1": np.where(moving, np.sin(ra), np.nan),
        "h1": np.where(moving, (p > 0.5).astype(float), np.nan), "ws": s["ws"].to_numpy(),
        "records": moving.astype(float)}, index=s.index)
    h = rec.resample("h", label="right", closed="right").agg(
        {"x": "mean", "y": "mean", "x1": "mean", "y1": "mean", "h1": "mean", "ws": "mean", "records": "sum"})
    h = h[h["records"] >= MIN_RECORDS]
    return pd.DataFrame({
        "direction": np.rad2deg(np.arctan2(h["y"], h["x"])) % 360,
        "v1": np.rad2deg(np.arctan2(h["y1"], h["x1"])) % 360,
        "resultant": np.hypot(h["x"], h["y"]),
        "frac_h1": h["h1"], "ws": h["ws"], "records": h["records"].astype(int)}).rename_axis("TIMESTAMP")


def main(stations: list[str]) -> None:
    unknown = [st for st in stations if st not in SOURCES]
    if unknown:
        raise SystemExit(f"Sin Table3 registrado en SOURCES: {', '.join(unknown)}")
    with tempfile.TemporaryDirectory() as tmp:
        models = train_models(Store(Path(tmp)))
    print("modelos entrenados con", ", ".join(STATIONS))
    for st in stations:
        hourly = reconstruct(read_5min(SOURCES[st]), *models)
        path = output_path(st)
        hourly.to_csv(path, float_format="%.3f")
        d = abs_diff(hourly["direction"].to_numpy(), hourly["v1"].to_numpy())
        print(f"{st}: {len(hourly)} h ({hourly.index.min()} → {hourly.index.max()}), "
              f"{(hourly['frac_h1'] > 0).mean() * 100:.1f} % con algún registro corregido, "
              f"{(d > 30).mean() * 100:.1f} % con más de 30° frente a V1 → {path}")


if __name__ == "__main__":
    main(sys.argv[1:] or list(SOURCES))
