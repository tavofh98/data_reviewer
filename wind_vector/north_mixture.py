"""Corrección de las mezclas del norte en WindDir_Avg de 5 min con un modelo físico del promedio y el contexto.

Física. Si las 60 muestras de 5 s se reparten alrededor de una dirección real μ con dispersión σ, la media
aritmética esperada es A = g(μ, σ) = E[(μ + σZ) mod 360]. Lejos del norte g(μ, σ) ≈ μ; en ±3σ alrededor de 0°
g decrece de ~360 a ~0 (rama de mezcla). Cada WindDir_Avg (A) tiene así dos candidatos:
  H0  dirección real = A
  H1  mezcla del norte: dirección real = μ de la rama de mezcla con g(μ, σ) = A
Etiqueta (solo para entrenar y medir): H1 si D1 de 5 min está más cerca del candidato H1 que de A.

Método, con solo A, WS_ms_Avg, WS_ms_Max y la hora (lo que guardan las estaciones sin D1):
  1. σ estimada: regresión de SD1 con velocidad, racha, hora y rasgos de vecinos.
  2. Etapa 1: clasificador de H1 con los rasgos de vecinos y los físicos (μ, |μ|/σ, candidatos de los vecinos).
  3. Etapa 2: el mismo clasificador más la probabilidad de la etapa 1 promediada en ±3, ±6 y ±12 registros.
  4. Cada registro entra en la hora como vector blando P(H1)·u(μ) + (1 − P(H1))·u(A).
Todo se entrena con dos estaciones y se mide en la tercera; la etapa 2 se entrena con probabilidades de la
etapa 1 calculadas fuera de muestra (cruzadas entre las dos estaciones de entrenamiento).
Validación externa: un modelo entrenado con las tres estaciones se aplica sin cambios a las estaciones de
loader.EXTRA_STATIONS (último año; antes hay que ejecutar ``python -m wind_vector.loader extra``).
Referencias: V1 (vectores unitarios de A 5 min) y oráculo (elige siempre bien entre A y μ con la σ real).

Memoria: cada estación se prepara por separado y sus matrices (float32) se guardan en una carpeta temporal
que se borra al terminar; cada paso carga solo lo que usa.

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.north_mixture

Salida: tabla en markdown por la consola (se copia a INFORME.md, sección 3.8) y las direcciones horarias
estimadas en wind_vector/output/north_mixture_hourly.csv.gz (una fila por hora válida y estación).
"""
from __future__ import annotations

import ctypes
import gc
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from wind_vector.analyze import BLOCKS, OUT, STATIONS, build_hourly, to_md, valid_mask
from wind_vector.loader import EXTRA_STATIONS
from wind_vector.north_sector import abs_diff

NEAR_NORTH = 30.0   # registro "cerca del norte" (grados)
WINDOW = 3          # vecinos a cada lado para la media vectorial (registros de 5 min)
BASE = ["dn", "jump_prev", "jump_next", "frac_north_3", "frac_north_6", "dist_nb", "nb_north", "r_nb",
        "ws", "gust", "hod_sin", "hod_cos"]
SIGMA_FEATURES = ["ws", "gust", "hod_sin", "hod_cos", "r_nb", "frac_north_6", "jump_prev", "jump_next"]
ROLL = (3, 6, 12)

# Rama de mezcla de g(μ, σ) tabulada por σ (1–120°): A decreciente → μ.
_MU = np.arange(-180, 180.01, 0.25)
_SIGMAS = np.arange(1, 121)
_Z = np.linspace(-5, 5, 801)
_W = norm.pdf(_Z) / norm.pdf(_Z).sum()
_BRANCH = []
for _s in _SIGMAS:
    _g = (((_MU[:, None] + _s * _Z[None, :]) % 360) * _W).sum(axis=1)
    _i0 = np.argmax(np.where(_MU <= 0, _g, -1))
    _i1 = np.argmin(np.where(_MU > 0, _g, 999))
    _BRANCH.append((_g[_i0:_i1 + 1][::-1], _MU[_i0:_i1 + 1][::-1]))


def mixture_direction(a: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """μ (0–360) de la rama de mezcla tal que g(μ, σ) = A."""
    out = np.full(len(a), np.nan)
    j = np.clip(np.round(np.nan_to_num(sigma, nan=20.0)).astype(int) - 1, 0, len(_SIGMAS) - 1)
    for k in np.unique(j):
        m = j == k
        out[m] = np.interp(a[m], *_BRANCH[k])
    return out % 360


def to_5min(df: pd.DataFrame) -> pd.DataFrame:
    """Serie regular de 5 min con la fila horaria y el bloque de origen de cada registro."""
    parts = []
    for k, b in enumerate(BLOCKS, start=1):
        parts.append(pd.DataFrame({
            "TIMESTAMP": df["TIMESTAMP"] - pd.Timedelta(minutes=5 * (len(BLOCKS) - k)),
            "row": df.index, "slot": k - 1,
            "A": df[f"WindDir_Avg_{b}"], "D1": df[f"WindDir_D1_WVT_{b}"], "SD1": df[f"WindDir_SD1_WVT_{b}"],
            "ws": df[f"WS_ms_Avg_{b}"], "wsmax": df[f"WS_ms_Max_{b}"],
        }))
    s = pd.concat(parts).sort_values("TIMESTAMP").drop_duplicates("TIMESTAMP", keep="last").set_index("TIMESTAMP")
    return s.asfreq("5min")


def rolling(x: np.ndarray, w: int) -> np.ndarray:
    """Media centrada en ±w registros (la serie es regular, así que basta la posición)."""
    return pd.Series(x).rolling(2 * w + 1, center=True, min_periods=1).mean().to_numpy(np.float32)


def features(s: pd.DataFrame) -> pd.DataFrame:
    """Covariables de cada registro a partir de sus vecinos; NaN donde falta el vecino."""
    a = s["A"].where(s["ws"] > 0)
    f = pd.DataFrame(index=s.index)
    f["dn"] = abs_diff(a, 0.0)
    f["jump_prev"] = abs_diff(a, a.shift(1))
    f["jump_next"] = abs_diff(a, a.shift(-1))
    north = (f["dn"] <= NEAR_NORTH).astype(float).where(a.notna())
    for w in (3, 6):
        nb = pd.concat([north.shift(k) for k in range(-w, w + 1) if k], axis=1)
        f[f"frac_north_{w}"] = nb.mean(axis=1)
    shifts = [k for k in range(-WINDOW, WINDOW + 1) if k]
    rad = np.deg2rad(pd.concat([a.shift(k) for k in shifts], axis=1).to_numpy())
    valid = ~np.isnan(rad)
    n = np.maximum(valid.sum(axis=1), 1)
    sn = np.where(valid, np.sin(rad), 0).sum(axis=1) / n
    cs = np.where(valid, np.cos(rad), 0).sum(axis=1) / n
    nb_dir = np.where(valid.any(axis=1), np.rad2deg(np.arctan2(sn, cs)) % 360.0, np.nan)
    f["nb_dir"] = nb_dir
    f["dist_nb"] = abs_diff(a, nb_dir)
    f["nb_north"] = abs_diff(nb_dir, 0.0)
    f["r_nb"] = np.where(valid.any(axis=1), np.hypot(sn, cs), np.nan)
    f["ws"] = s["ws"]
    f["gust"] = s["wsmax"] / s["ws"].where(s["ws"] > 0)
    hod = 2 * np.pi * (s.index.hour + s.index.minute / 60) / 24
    f["hod_sin"], f["hod_cos"] = np.sin(hod), np.cos(hod)
    return f


class Store:
    """Matrices de cada estación en disco (npz); se cargan por partes según el paso."""

    def __init__(self, root: Path):
        self.root = root

    def save(self, st: str, name: str, **arrays) -> None:
        np.savez(self.root / f"{st}_{name}.npz", **arrays)

    def load(self, st: str, name: str) -> dict[str, np.ndarray]:
        with np.load(self.root / f"{st}_{name}.npz") as z:
            return {k: z[k] for k in z.files}


def build_base(store: Store, st: str) -> None:
    """Serie de 5 min, rasgos de vecinos y verdad horaria de una estación."""
    df = pd.read_csv(OUT / f"aligned_{st}.csv.gz", parse_dates=["TIMESTAMP"])
    s = to_5min(df)
    f = features(s)
    h = build_hourly(df)
    moving = ((s["ws"] > 0) & s["A"].notna()).to_numpy()
    store.save(st, "base",
               A=s["A"].to_numpy(np.float32), D1=s["D1"].to_numpy(np.float32), SD1=s["SD1"].to_numpy(np.float32),
               row=s["row"].fillna(-1).to_numpy(np.int32), moving=moving, labeled=moving & s["D1"].notna().to_numpy(),
               F=f[BASE].to_numpy(np.float32), hour_ts=df["TIMESTAMP"].to_numpy(), truth=h["truth"].to_numpy(),
               V1=h["V1"].to_numpy(), mask=valid_mask(h).to_numpy())


def estimate_sigma(store: Store, train: list[str], test: str) -> np.ndarray:
    cols = [BASE.index(c) for c in SIGMA_FEATURES]
    xs, ys = [], []
    for st in train:
        b = store.load(st, "base")
        ok = b["labeled"] & ~np.isnan(b["SD1"])
        xs.append(b["F"][ok][:, cols]); ys.append(b["SD1"][ok])
    reg = HistGradientBoostingRegressor(max_iter=300, random_state=0).fit(np.vstack(xs), np.concatenate(ys))
    del xs, ys
    return np.clip(reg.predict(store.load(test, "base")["F"][:, cols]), 1.0, 120.0)


def build_physics(store: Store, st: str, sigma: np.ndarray) -> None:
    """Candidato H1 (μ), etiqueta y matriz de la etapa 1."""
    b = store.load(st, "base")
    a, d1 = b["A"].astype(float), b["D1"].astype(float)
    mu = mixture_direction(a, sigma)
    cand = np.where(abs_diff(a, 0.0) < abs_diff(mu, 0.0), a, mu)
    cand = np.where(b["moving"], cand, np.nan)
    near = (abs_diff(cand, 0.0) <= NEAR_NORTH).astype(float)
    bigjump = (b["F"][:, BASE.index("jump_prev")] > 60).astype(float)
    extra = [sigma, abs_diff(mu, 0.0) / sigma] + [rolling(near, w) for w in ROLL] + [rolling(bigjump, w) for w in ROLL]
    store.save(st, "phys", mu=mu.astype(np.float32), y=abs_diff(d1, mu) < abs_diff(d1, a),
               F1=np.column_stack([b["F"]] + [np.asarray(e, np.float32) for e in extra]))


def training_matrix(store: Store, sts: list[str], p1: dict[str, np.ndarray] | None = None):
    xs, ys = [], []
    for st in sts:
        lab = store.load(st, "base")["labeled"]
        ph = store.load(st, "phys")
        x = ph["F1"] if p1 is None else stage2_matrix(ph["F1"], p1[st])
        xs.append(x[lab]); ys.append(ph["y"][lab])
    return np.vstack(xs), np.concatenate(ys)


def stage2_matrix(f1: np.ndarray, p1: np.ndarray) -> np.ndarray:
    return np.column_stack([f1, p1.astype(np.float32)] + [rolling(p1, w) for w in ROLL])


def fit_classifier(x: np.ndarray, y: np.ndarray) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(max_iter=300, random_state=0).fit(x, y)


def soft_hourly(b: dict, mu: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Dirección horaria con cada registro como P(H1)·u(μ) + (1 − P(H1))·u(A)."""
    ok = b["moving"] & (b["row"] >= 0)
    ra, rm = np.deg2rad(b["A"].astype(float)), np.deg2rad(mu.astype(float))
    x = p * np.cos(rm) + (1 - p) * np.cos(ra)
    y = p * np.sin(rm) + (1 - p) * np.sin(ra)
    n, r = len(b["truth"]), b["row"][ok]
    sx, sy = np.bincount(r, x[ok], n), np.bincount(r, y[ok], n)
    return np.where(np.bincount(r, None, n) > 0, np.rad2deg(np.arctan2(sy, sx)) % 360.0, np.nan)


def oracle(b: dict) -> np.ndarray:
    """Elige siempre bien entre A y el μ de mezcla calculado con la σ real (SD1)."""
    a, d1 = b["A"].astype(float), b["D1"].astype(float)
    mu = mixture_direction(a, b["SD1"].astype(float))
    pick = (abs_diff(d1, mu) < abs_diff(d1, a)) & b["labeled"]
    return soft_hourly(b, mu, pick.astype(float))


def summarize(st: str, truth: np.ndarray, mask: np.ndarray, methods: dict[str, np.ndarray]) -> list[dict]:
    groups = {"todas": mask, "norte (real ≤ 45°)": mask & (abs_diff(truth, 0.0) <= 45),
              "resto (real > 45°)": mask & (abs_diff(truth, 0.0) > 45)}
    rows = []
    for g, sel in groups.items():
        for name, est in methods.items():
            e = abs_diff(est, truth)[sel]
            rows.append({"estación": st, "horas": g, "método": name, "n": int(sel.sum()), "media": e.mean(),
                         "mediana": np.median(e), "p95": np.quantile(e, 0.95), "% > 30°": (e > 30).mean() * 100})
    return rows


def peak_memory_mb() -> float | None:
    """Pico de memoria física del proceso (solo Windows)."""
    if sys.platform != "win32":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                           "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                                           "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]

    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    c = Counters()
    c.cb = ctypes.sizeof(c)
    if not k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
        return None
    return c.PeakWorkingSetSize / 2**20


def others(st: str) -> list[str]:
    return [s for s in STATIONS if s != st]


def evaluate(store: Store, st: str, p2: np.ndarray) -> tuple[list[dict], pd.DataFrame]:
    """Tabla de errores y direcciones horarias de una estación de prueba."""
    mu = store.load(st, "phys")["mu"]
    b = store.load(st, "base")
    methods = {"V1": b["V1"], "modelo": soft_hourly(b, mu, p2), "oráculo": oracle(b)}
    m = b["mask"]
    hourly = pd.DataFrame({"station": st, "TIMESTAMP": b["hour_ts"][m], "truth": b["truth"][m],
                           "V1": methods["V1"][m], "model": methods["modelo"][m], "oracle": methods["oráculo"][m]})
    return summarize(st, b["truth"], m, methods), hourly


def main() -> None:
    rows, hourly = [], []
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp))
        for st in STATIONS:
            build_base(store, st)
            gc.collect()
        for st in STATIONS:
            build_physics(store, st, estimate_sigma(store, others(st), st))
            gc.collect()
        # Etapa 1: cada estación predicha por un modelo de cada otra estación y por el de las otras dos juntas.
        p1_single = {st: {} for st in STATIONS}
        p1_pair = {}
        for st in STATIONS:
            f1 = store.load(st, "phys")["F1"]
            for tr in others(st):
                p1_single[st][tr] = fit_classifier(*training_matrix(store, [tr])).predict_proba(f1)[:, 1]
                gc.collect()
            p1_pair[st] = fit_classifier(*training_matrix(store, others(st))).predict_proba(f1)[:, 1]
            gc.collect()
        print("etapa 1 ok")
        # Etapa 2: entrenada con probabilidades fuera de muestra de las dos estaciones de entrenamiento.
        for test in STATIONS:
            a_, b_ = others(test)
            p1_oof = {a_: p1_single[a_][b_], b_: p1_single[b_][a_]}
            model = fit_classifier(*training_matrix(store, [a_, b_], p1_oof))
            gc.collect()
            p2 = model.predict_proba(stage2_matrix(store.load(test, "phys")["F1"], p1_pair[test]))[:, 1]
            r, h = evaluate(store, test, p2)
            rows += r
            hourly.append(h)
            del model
            gc.collect()
            print(test, "ok")
        # Validación externa: σ, etapa 1 y etapa 2 entrenadas con las tres estaciones (la etapa 2 con p1_pair,
        # que para cada una viene del modelo de las otras dos, es decir, fuera de muestra).
        train = list(STATIONS)
        stage1 = fit_classifier(*training_matrix(store, train))
        stage2 = fit_classifier(*training_matrix(store, train, p1_pair))
        gc.collect()
        for test in EXTRA_STATIONS:
            build_base(store, test)
            build_physics(store, test, estimate_sigma(store, train, test))
            f1 = store.load(test, "phys")["F1"]
            p2 = stage2.predict_proba(stage2_matrix(f1, stage1.predict_proba(f1)[:, 1]))[:, 1]
            r, h = evaluate(store, test, p2)
            rows += r
            hourly.append(h)
            gc.collect()
            print(test, "ok")
    pd.concat(hourly).to_csv(OUT / "north_mixture_hourly.csv.gz", index=False, float_format="%.2f")
    print("\n### Error horario frente al Θ1 del logger (grados)\n")
    print(to_md(pd.DataFrame(rows)))
    peak = peak_memory_mb()
    if peak is not None:
        print(f"\nPico de memoria del proceso: {peak:.0f} MB")


if __name__ == "__main__":
    main()
