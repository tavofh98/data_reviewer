"""Protocolo de entrenamiento, validación y prueba para corregir las mezclas del norte (último año, 6 estaciones).

Partición (la misma para todos los modelos, así que las comparaciones son pareadas):
  - Cada estación se corta en semanas consecutivas; semana mod 5 = 0, 1, 2 → entrenamiento, 3 → validación,
    4 → prueba. Todas las estaciones aportan horas de las cuatro estaciones del año a cada parte.
  - Los modelos solo ven semanas de entrenamiento. La validación elige el modelo; la prueba se mira al final.
Alcance del entrenamiento (qué estaciones ve el modelo):
  - estación: solo la propia estación (cota de lo que da un modelo a medida, si la estación tuviera D1).
  - global: las seis estaciones.
  - loso: las otras cinco (lo que pasa en una estación sin D1: el caso de uso real).
Modelos, de más analítico a más caja negra:
  σ   gust     SD1 = a·(G − 1)^b, con G = racha / velocidad media (2 parámetros, ajuste log-log)
      gust_ws  log SD1 = a + b·log(G − 1) + c·log(velocidad) (3 parámetros)
      hgb      HistGradientBoosting con SIGMA_FEATURES (el de north_mixture)
  P   lr1      regresión logística con 11 rasgos físicos (coeficientes legibles)
      lr2      lr1 + su probabilidad suavizada en ±3, ±6 y ±12 registros (segunda etapa)
      hgb2     el clasificador de dos etapas de north_mixture (HistGradientBoosting)
  La segunda etapa se entrena con probabilidades de la primera fuera de muestra (se deja fuera cada semana
  módulo 5 de entrenamiento).
Referencias: V1, oráculo (σ real y elección perfecta) y «elección perfecta» con la σ estimada (separa cuánto
error viene de σ y cuánto de la clasificación).

Uso (desde explorar_qaqc/, con los aligned_*.csv.gz ya creados por wind_vector.loader):
    uv run python -m wind_vector.protocol

Salidas: output/protocol_hourly.csv.gz (una fila por hora de validación o prueba, una columna por modelo),
output/protocol_sigma.csv (error de σ por configuración) y los coeficientes de lr por consola.
Las tablas y los intervalos de confianza los calcula wind_vector.protocol_report.
"""
from __future__ import annotations

import gc
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from wind_vector.analyze import OUT, STATIONS, aligned_path, build_hourly, valid_mask
from wind_vector.loader import EXTRA_STATIONS
from wind_vector.north_mixture import (BASE, NEAR_NORTH, ROLL, SIGMA_FEATURES, features, mixture_direction,
                                       peak_memory_mb, rolling, soft_hourly, to_5min)
from wind_vector.north_sector import abs_diff

ALL = list(STATIONS) + list(EXTRA_STATIONS)
DAYS = 365
TRAIN_FOLDS = (0, 1, 2)
VAL, TEST = 3, 4
LR_FEATURES = ["mu_ratio", "dcos", "dn", "frac_north_6", "nb_north", "jump_prev", "jump_next", "r_nb",
               "north_cand_6", "bigjump_6", "log_sigma"]
# Solo la σ analítica: en la v1 (protocol_hourly_v1) rindió igual que la HGB en las 6 estaciones de prueba.
SIGMA_MODELS = ("gust_ws",)
# Fracción que se conserva (con peso 1/EASY_KEEP) de los registros triviales. Con 0.1 (v3) el pico bajó a 523 MB
# pero no el tiempo, y el error loso de validación subió de 5.04 a 5.13: se deja en 1 (sin submuestreo).
EASY_KEEP = 1.0
CLASSIFIERS = ("lr2", "hgb2")
TAUS = (0.0, 0.1, 0.25)   # P(H1) < τ pasa a 0
CONTEXT = 6               # puerta: algún A a ≤ NEAR_NORTH del norte en ±CONTEXT registros


def load(st: str) -> dict:
    """Registros de 5 min y horas del último año de una estación, con su semana módulo 5."""
    df = pd.read_csv(aligned_path(st), parse_dates=["TIMESTAMP"])
    df = df[df["TIMESTAMP"] > df["TIMESTAMP"].max() - pd.Timedelta(days=DAYS)].reset_index(drop=True)
    s = to_5min(df)
    f = features(s)
    h = build_hourly(df)
    elapsed = df["TIMESTAMP"] - df["TIMESTAMP"].min()
    fold_h = ((elapsed // pd.Timedelta(days=7)) % 5).to_numpy()
    day_h = ((elapsed // pd.Timedelta(days=1)) % 7).to_numpy()
    # Separación de un día: fuera del entrenamiento el último día antes de validación y el primero tras prueba.
    purge_h = ((fold_h == TRAIN_FOLDS[-1]) & (day_h == 6)) | ((fold_h == TRAIN_FOLDS[0]) & (day_h == 0))
    row = s["row"].fillna(-1).astype(int).to_numpy()
    moving = ((s["ws"] > 0) & s["A"].notna()).to_numpy()
    near_a = (f["dn"] <= NEAR_NORTH).to_numpy(float)
    return {"A": s["A"].to_numpy(float), "D1": s["D1"].to_numpy(float), "SD1": s["SD1"].to_numpy(float),
            "purge": np.where(row >= 0, purge_h[row.clip(0)], True),
            "context": rolling(near_a, CONTEXT) > 0,
            "ws": s["ws"].to_numpy(float), "G": (s["wsmax"] / s["ws"].where(s["ws"] > 0)).to_numpy(float),
            "F": f[BASE].to_numpy(float), "nb_dir": f["nb_dir"].to_numpy(float), "row": row,
            "fold": np.where(row >= 0, fold_h[row.clip(0)], -1), "moving": moving,
            "labeled": moving & s["D1"].notna().to_numpy() & s["SD1"].notna().to_numpy(),
            "truth": h["truth"].to_numpy(float), "V1": h["V1"].to_numpy(float), "mask": valid_mask(h).to_numpy(),
            "fold_h": fold_h, "hour_ts": df["TIMESTAMP"].to_numpy()}


# ---------- σ ----------

class SigmaLog:
    """log SD1 lineal en log(G − 1) (y en log velocidad si with_ws); fuera de dominio, la mediana."""

    def __init__(self, with_ws: bool):
        self.with_ws = with_ws

    def _x(self, d: dict) -> np.ndarray:
        cols = [np.log(np.clip(d["G"] - 1, 0.02, None))]
        if self.with_ws:
            cols.append(np.log(np.clip(d["ws"], 0.3, None)))
        return np.column_stack([np.ones(len(d["A"]))] + cols)

    def fit(self, ds: list[dict], sel: list[np.ndarray]) -> "SigmaLog":
        x = np.vstack([self._x(d)[m] for d, m in zip(ds, sel)])
        y = np.log(np.clip(np.concatenate([d["SD1"][m] for d, m in zip(ds, sel)]), 0.5, None))
        ok = np.isfinite(x).all(axis=1) & np.isfinite(y)
        self.coef, *_ = np.linalg.lstsq(x[ok], y[ok], rcond=None)
        self.median = float(np.exp(np.median(y[ok])))
        return self

    def predict(self, d: dict) -> np.ndarray:
        p = np.exp(self._x(d) @ self.coef)
        return np.clip(np.where(np.isfinite(p) & (d["ws"] > 0.3), p, self.median), 1.0, 120.0)


class SigmaHGB:
    cols = [BASE.index(c) for c in SIGMA_FEATURES]

    def fit(self, ds: list[dict], sel: list[np.ndarray]) -> "SigmaHGB":
        x = np.vstack([d["F"][m][:, self.cols] for d, m in zip(ds, sel)])
        y = np.concatenate([d["SD1"][m] for d, m in zip(ds, sel)])
        self.reg = HistGradientBoostingRegressor(max_iter=300, random_state=0).fit(x, y)
        return self

    def predict(self, d: dict) -> np.ndarray:
        return np.clip(self.reg.predict(d["F"][:, self.cols]), 1.0, 120.0)


def make_sigma(name: str):
    return {"gust": lambda: SigmaLog(False), "gust_ws": lambda: SigmaLog(True), "hgb": SigmaHGB}[name]()


# ---------- rasgos físicos y etiqueta para una σ dada ----------

def physics(d: dict, sigma: np.ndarray) -> dict:
    a, d1 = d["A"], d["D1"]
    mu = mixture_direction(a, sigma)
    cand = np.where(d["moving"], np.where(abs_diff(a, 0.0) < abs_diff(mu, 0.0), a, mu), np.nan)
    near = (abs_diff(cand, 0.0) <= NEAR_NORTH).astype(float)
    bigjump = (d["F"][:, BASE.index("jump_prev")] > 60).astype(float)
    nb = d["nb_dir"]
    # Consistencia con los vecinos: cos(μ − N) − cos(A − N) > 0 si μ encaja mejor que A con la dirección vecina N.
    dcos = np.cos(np.deg2rad(abs_diff(mu, nb))) - np.cos(np.deg2rad(abs_diff(a, nb)))
    extra = {"sigma": sigma, "log_sigma": np.log(sigma), "mu_ratio": abs_diff(mu, 0.0) / sigma, "dcos": dcos}
    extra.update({f"north_cand_{w}": rolling(near, w) for w in ROLL})
    extra.update({f"bigjump_{w}": rolling(bigjump, w) for w in ROLL})
    named = dict(zip(BASE, d["F"].T)) | extra
    hgb_cols = BASE + ["sigma", "mu_ratio", "dcos"] + [f"north_cand_{w}" for w in ROLL] + [f"bigjump_{w}" for w in ROLL]
    return {"mu": mu, "y": abs_diff(d1, mu) < abs_diff(d1, a),
            "X_lr": np.column_stack([named[c] for c in LR_FEATURES]).astype(np.float32),
            "X_hgb": np.column_stack([named[c] for c in hgb_cols]).astype(np.float32)}


# ---------- clasificadores de dos etapas ----------

def new_classifier(kind: str):
    if kind == "lr":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
    return HistGradientBoostingClassifier(max_iter=300, random_state=0)


def stage2(x: np.ndarray, p1: np.ndarray, sel: np.ndarray | None = None) -> np.ndarray:
    """Rasgos de la segunda etapa; las medias móviles se calculan en la serie completa y luego se filtra."""
    cols = [p1.astype(np.float32)] + [rolling(p1, w) for w in ROLL]
    if sel is None:
        return np.column_stack([x] + cols)
    return np.column_stack([x[sel]] + [c[sel] for c in cols])


def fit_weighted(kind: str, x: np.ndarray, y: np.ndarray, w: np.ndarray):
    model = new_classifier(kind)
    key = "logisticregression__sample_weight" if kind == "lr" else "sample_weight"
    return model.fit(x, y, **{key: w})


def fit_predict(kind: str, two_stage: bool, xs: dict, ys: dict, train: dict, evals: list[str]) -> tuple[dict, object]:
    """P(H1) en todos los registros de las estaciones de evaluación. xs/ys/train/WEIGHTS por estación."""
    tr = list(train)

    def fit(sel_fn, x_fn):
        sels = {s: sel_fn(s) for s in tr}
        return fit_weighted(kind, np.vstack([x_fn(s, sels[s]) for s in tr]),
                            np.concatenate([ys[s][sels[s]] for s in tr]),
                            np.concatenate([WEIGHTS[s][sels[s]] for s in tr]))

    m1 = fit(lambda s: train[s], lambda s, m: xs[s][m])
    p_full = {s: m1.predict_proba(xs[s])[:, 1] for s in set(tr) | set(evals)}
    if not two_stage:
        return {s: p_full[s] for s in evals}, m1
    # Primera etapa fuera de muestra en las estaciones de entrenamiento: deja fuera cada semana módulo 5.
    p_oof = {s: p_full[s].copy() for s in tr}
    for k in TRAIN_FOLDS:
        mk = fit(lambda s: train[s] & (FOLDS[s] != k), lambda s, m: xs[s][m])
        for s in tr:
            sel = train[s] & (FOLDS[s] == k)
            p_oof[s][sel] = mk.predict_proba(xs[s][sel])[:, 1]
        del mk
    m2 = fit(lambda s: train[s], lambda s, m: stage2(xs[s], p_oof[s], m))
    return {s: m2.predict_proba(stage2(xs[s], p_full[s]))[:, 1] for s in evals}, m1


FOLDS: dict[str, np.ndarray] = {}
WEIGHTS: dict[str, np.ndarray] = {}


def easy_records(d: dict) -> np.ndarray:
    """Registros triviales: A a más de 90° del norte, sin saltos de más de 20° y sin vecinos en el norte.

    En 5 estaciones su frecuencia de mezcla es < 0.2 %; en Minas Sur, 7 %: por eso se submuestrean con peso
    (estimador sin sesgo) en vez de descartarse.
    """
    c = {k: d["F"][:, BASE.index(k)] for k in ("dn", "jump_prev", "jump_next", "frac_north_6")}
    return (c["dn"] > 90) & (c["jump_prev"] < 20) & (c["jump_next"] < 20) & (c["frac_north_6"] == 0)


def main() -> None:
    t0 = time.time()
    data = {st: load(st) for st in ALL}
    FOLDS.update({st: d["fold"] for st, d in data.items()})
    rng = np.random.default_rng(0)
    train_sel = {}
    for st, d in data.items():
        easy = easy_records(d)
        keep = ~easy | (rng.random(len(easy)) < EASY_KEEP)
        train_sel[st] = d["labeled"] & np.isin(d["fold"], TRAIN_FOLDS) & ~d["purge"] & keep
        WEIGHTS[st] = np.where(easy, 1 / EASY_KEEP, 1.0)
    print(f"datos cargados ({time.time() - t0:.0f} s, pico {peak_memory_mb():.0f} MB):",
          {st: int(train_sel[st].sum()) for st in data}, "registros de entrenamiento")

    scopes = {f"estación:{st}": ([st], [st]) for st in ALL}
    scopes["global"] = (ALL, ALL)
    scopes.update({f"loso:{st}": ([s for s in ALL if s != st], [st]) for st in ALL})

    hours = {st: d["mask"] & np.isin(d["fold_h"], (VAL, TEST)) for st, d in data.items()}
    out = {st: pd.DataFrame({"station": st, "TIMESTAMP": d["hour_ts"][hours[st]], "fold": d["fold_h"][hours[st]],
                             "truth": d["truth"][hours[st]], "V1": d["V1"][hours[st]]}) for st, d in data.items()}
    for st, d in data.items():
        oracle_mu = mixture_direction(d["A"], d["SD1"])
        pick = (abs_diff(d["D1"], oracle_mu) < abs_diff(d["D1"], d["A"])) & d["labeled"]
        out[st]["oracle"] = soft_hourly(d, oracle_mu, pick.astype(float))[hours[st]]

    sigma_rows, coefs = [], {}
    for scope, (trs, evs) in scopes.items():
        name = scope.split(":")[0]
        for sm in SIGMA_MODELS:
            model = make_sigma(sm).fit([data[s] for s in trs], [train_sel[s] for s in trs])
            sig = {s: model.predict(data[s]) for s in set(trs) | set(evs)}
            for s in evs:
                d = data[s]
                for fold, lab in ((VAL, "val"), (TEST, "test")):
                    m = d["labeled"] & (d["fold"] == fold)
                    e = np.abs(sig[s][m] - d["SD1"][m])
                    sigma_rows.append({"alcance": name, "station": s, "sigma": sm, "split": lab,
                                       "MAE": e.mean(), "sesgo": (sig[s][m] - d["SD1"][m]).mean()})
            ph = {s: physics(data[s], sig[s]) for s in sig}
            for s in evs:   # elección perfecta con la σ estimada
                d = data[s]
                pick = (ph[s]["y"] & d["labeled"]).astype(float)
                out[s][f"{name}|{sm}|perfecta"] = soft_hourly(d, ph[s]["mu"], pick)[hours[s]]
            ys = {s: ph[s]["y"] for s in ph}
            train = {s: train_sel[s] for s in trs}
            for clf in CLASSIFIERS:
                kind, two = ("lr", clf == "lr2") if clf.startswith("lr") else ("hgb", True)
                xs = {s: ph[s]["X_lr" if kind == "lr" else "X_hgb"] for s in ph}
                p, m1 = fit_predict(kind, two, xs, ys, train, evs)
                for s in evs:
                    for tau in TAUS:
                        pt = np.where(p[s] >= tau, p[s], 0.0)
                        for gate in (False, True):
                            pg = np.where(data[s]["context"], pt, 0.0) if gate else pt
                            col = f"{name}|{sm}|{clf}|t{tau}" + ("|ctx" if gate else "")
                            out[s][col] = soft_hourly(data[s], ph[s]["mu"], pg)[hours[s]]
                if scope == "global" and kind == "lr":   # primera etapa de lr2
                    coefs[sm] = m1[-1].coef_[0]
            del ph, xs, ys, sig, p
            gc.collect()
            print(f"{scope:22s} σ={sm:8s} ok ({time.time() - t0:.0f} s, pico {peak_memory_mb():.0f} MB)")

    pd.concat(out.values()).to_csv(OUT / "protocol_hourly.csv.gz", index=False, float_format="%.2f")
    pd.DataFrame(sigma_rows).to_csv(OUT / "protocol_sigma.csv", index=False, float_format="%.3f")
    print("\n### Coeficientes de lr (global, primera etapa, rasgos estandarizados)\n")
    print(pd.DataFrame(coefs, index=LR_FEATURES).round(2).to_string())
    print(f"\nTotal {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
