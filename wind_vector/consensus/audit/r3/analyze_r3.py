"""Evaluación del encargo r3: ¿sirve el consenso de vecinas para detectar las mezclas del norte en 5 min?

Mide en Cortadera, Papujune y Tala-1 (y adicionalmente Alto Quellaveco y Tala Legal):
1. En los registros de 5 min con A en 150-300° (zona ambigua), separación entre H1 (D1 <= 45° del norte)
   y H0 (D1 >= 90° del norte) usando el consenso horario por pares (consensus_pairs.py --limpio):
   AUC y razones de verosimilitud (LR) según la distancia del consenso al norte.
2. Comparación con los rasgos propios de north_mixture.features (y rasgos físicos de etapa 1 y 2):
   AUC univariado y de regresión logística / HGB con y sin consenso, validado fuera de muestra por semanas,
   así como el impacto en el error angular horario final (grados).
3. Análisis de casos críticos (horas nocturnas, episodios sin ningún registro cercano al norte en ±30 min,
   calibración sin D1 usando horas limpias R4 y validación LOSO entre estaciones).
"""
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from wind_vector.analyze import BLOCKS, aligned_path, build_hourly, valid_mask
from wind_vector.north_mixture import (
    BASE,
    NEAR_NORTH,
    ROLL,
     features,
    mixture_direction,
    rolling,
    soft_hourly,
    to_5min,
)
from wind_vector.north_sector import abs_diff

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[4]
DB_PATH = ROOT.parents[1] / "database_duck" / "anglo_ambiental.db"
STATIONS_FILE = ROOT / "met_viewer" / "stations.py"

TARGET_MAP = {
    "cortadera": "Cortadera",
    "papujune": "Papujune",
    "tala1": "Tala-1",
    "quellaveco": "Alto_Quellaveco",
    "tala_legal": "Tala_Legal",
}

MAIN_TARGETS = ["cortadera", "papujune", "tala1"]


def angular_dist(a, b):
    """Distancia angular absoluta en [0, 180]."""
    d = np.abs((a - b) % 360.0)
    return np.minimum(d, 360.0 - d)


def signed_diff(a, b):
    """Diferencia angular con signo en (-180, 180]."""
    return (a - b + 180.0) % 360.0 - 180.0


def load_hourly_network():
    """Carga la tabla horaria desde DuckDB aplicando las exclusiones del contexto (--limpio)."""
    src = STATIONS_FILE.read_text(encoding="utf-8")
    xy = {
        m[0]: (float(m[1]), float(m[2]))
        for m in re.findall(r'"([^"]+)":\s+Station\((\d+), (\d+)', src)
    }
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(
        """
        SELECT estacion_id AS st, timestamp AS ts,
               WindDir_D1_WVT AS d1, WindDir_Avg AS a, WS_ms_Avg AS ws
        FROM meteorologia
        WHERE timestamp >= '2025-11-01' AND timestamp <= '2026-11-03 23:59:59'
          AND WindDir_Avg IS NOT NULL
        """
    ).df()
    con.close()

    drop = {
        "Dique_pie_botadero",
        "Chalsos",
        "Mina_Norte",
        "Planta_Concentradora",
        "Ilo",
        "Huachunta",
        "Vizcachas",
        "Titire",
    }
    df = df[df["st"].isin(xy) & ~df["st"].isin(drop)].copy()
    df = df[~((df["st"] == "Sarallenque") & (df["ts"] < "2026-09-25 21:00"))]
    df = df[df["ws"] >= 0.5]
    exclusions = [
        ("Alto_Quellaveco", "2026-09-15 11:00", "2099"),
        ("Cortadera", "2026-09-13 11:00", "2099"),
        ("Alto_Tala", "2026-08-18 05:00", "2026-09-23 15:00"),
        ("Charaque", "2026-01-14 14:00", "2026-01-15 12:00"),
        ("Charaque", "2026-01-28 14:00", "2026-01-29 07:00"),
        ("Sarallenque_MQG-15-02", "2026-02-16 14:00", "2026-02-17 09:00"),
    ]
    for st, start, end in exclusions:
        df = df[~((df["st"] == st) & (df["ts"] >= start) & (df["ts"] <= end))]

    df["dir"] = df["d1"].fillna(df["a"])
    pivots = {c: df.pivot(index="ts", columns="st", values=c) for c in ("dir", "ws", "d1", "a")}
    return pivots, xy


def calibrated_neighbor(src_series: pd.Series, truth_series: pd.Series, tr_mask: pd.Series, band: np.ndarray) -> pd.Series:
    """Calibra una estación vecina por (sector de 22.5° × franja horaria) exactamente como consensus_pairs.py."""
    idx = src_series.index
    sec = (((src_series + 11.25) % 360) // 22.5)
    key = pd.Series(sec.astype("Int64").astype(str) + "_" + pd.Series(band, index=idx).astype(str), index=idx)
    ok = tr_mask & src_series.notna() & truth_series.notna()
    z = pd.Series(np.exp(1j * np.deg2rad(signed_diff(truth_series[ok], src_series[ok]))), index=src_series.index[ok])
    g = z.groupby(key[ok]).mean()
    off = pd.Series(np.rad2deg(np.angle(g.to_numpy())), index=g.index)
    return (src_series + key.map(off)) % 360.0


def compute_consensus_pairs(pivots: dict, target_db_name: str, reference_series: pd.Series | None = None, base_mask: pd.Series | None = None):
    """Calcula el consenso horario por pares para `target_db_name`.

    Si `reference_series` es None, usa D1 de la estación objetivo (como en consensus_pairs.py).
    También permite calibrar contra una serie limpia R4 (sin usar D1).
    Devuelve DataFrame con `comb` (dirección del consenso), `r_cons` (coherencia entre vecinas),
    `week` (0=par/entrenamiento, 1=impar/prueba) y las mejores vecinas.
    """
    d_mat = pivots["dir"]
    idx = d_mat.index
    week = (((idx - idx[0]) // pd.Timedelta(days=7)) % 2).to_numpy()
    hr = idx.hour
    band = np.where((hr >= 10) & (hr <= 17), 0, np.where((hr >= 22) | (hr <= 6), 1, 2))

    truth = pivots["d1"][target_db_name] if reference_series is None else reference_series.reindex(idx)
    if base_mask is None:
        base = (pivots["ws"][target_db_name] > 1) & truth.notna() & pivots["a"][target_db_name].notna()
    else:
        base = base_mask.reindex(idx).fillna(False) & truth.notna()

    tr = base & (week == 0)
    nbs = [s for s in d_mat.columns if s != target_db_name]

    u_sum = pd.Series(0.0, index=idx)
    w_sum = pd.Series(0.0, index=idx)
    s_sum = pd.Series(0.0, index=idx)

    for s in nbs:
        pred = calibrated_neighbor(d_mat[s], truth, tr, band)
        e_tr = angular_dist(pred[tr], truth[tr]).mean()
        if not np.isfinite(e_tr):
            continue
        wgt = 1.0 / max(e_tr, 5.0) ** 2
        m = pred.notna()
        u_sum[m] += wgt * np.sin(np.deg2rad(pred[m]))
        w_sum[m] += wgt * np.cos(np.deg2rad(pred[m]))
        s_sum[m] += wgt

    comb = pd.Series(np.rad2deg(np.arctan2(u_sum, w_sum)) % 360.0, index=idx).where(s_sum > 0)
    r_cons = pd.Series(np.hypot(u_sum, w_sum) / s_sum.where(s_sum > 0), index=idx)
    return pd.DataFrame({"comb": comb, "r_cons": r_cons, "week": week, "band": band}, index=idx)


def load_station_5min(st_key: str, pivots: dict):
    """Carga los datos alineados de 5 min de `st_key`, calcula rasgos propios y une el consenso horario."""
    db_name = TARGET_MAP[st_key]
    df = pd.read_csv(aligned_path(st_key), parse_dates=["TIMESTAMP"])
    # Filtrar al periodo del estudio de consenso (2025-11-01 en adelante)
    df = df[(df["TIMESTAMP"] >= "2025-11-01") & (df["TIMESTAMP"] <= "2026-11-03 23:59:59")].copy()
    if st_key == "cortadera":
        df = df[df["TIMESTAMP"] < "2026-09-13 11:00"].copy()
    elif st_key == "quellaveco":
        df = df[df["TIMESTAMP"] < "2026-09-15 11:00"].copy()
    df = df.reset_index(drop=True)

    s = to_5min(df)
    f = features(s)
    h = build_hourly(df)

    # Mapear timestamp horario (fin de la hora) a cada registro de 5 min
    row = s["row"].fillna(-1).astype(int).to_numpy()
    hour_ts = pd.Series(pd.NaT, index=s.index)
    valid_row = row >= 0
    hour_ts.iloc[np.where(valid_row)[0]] = df["TIMESTAMP"].iloc[row[valid_row]].to_numpy()
    s["hour_ts"] = pd.to_datetime(hour_ts)

    # Regla R4 horaria (sin usar D1): los 12 A en [20, 340] y ningún registro a > 45° de la mediana circular
    a_blocks = df[[f"WindDir_Avg_{b}" for b in BLOCKS]].to_numpy(float)
    in_20_340 = (angular_dist(a_blocks, 0.0) > 20.0).all(axis=1)
    max_pair_diff = np.nanmax(angular_dist(a_blocks[:, :, None], a_blocks[:, None, :]), axis=(1, 2))
    r4_mask_arr = (df["n_5min"].to_numpy() == 12) & in_20_340 & (max_pair_diff <= 60.0) & (h["ws_h"].to_numpy() > 1.0)
    r4_clean = pd.Series(r4_mask_arr, index=df["TIMESTAMP"])
    v1_series = pd.Series(h["V1"].to_numpy(), index=df["TIMESTAMP"])

    # Consenso calibrado con D1 (como consensus_pairs.py) y calibrado con R4 (sin D1)
    cons_d1 = compute_consensus_pairs(pivots, db_name)
    cons_r4 = compute_consensus_pairs(pivots, db_name, reference_series=v1_series, base_mask=r4_clean)

    s["comb_d1"] = cons_d1["comb"].reindex(s["hour_ts"]).to_numpy()
    s["r_cons_d1"] = cons_d1["r_cons"].reindex(s["hour_ts"]).to_numpy()
    s["comb_r4"] = cons_r4["comb"].reindex(s["hour_ts"]).to_numpy()
    s["r_cons_r4"] = cons_r4["r_cons"].reindex(s["hour_ts"]).to_numpy()
    s["week"] = cons_d1["week"].reindex(s["hour_ts"]).to_numpy()
    s["band"] = cons_d1["band"].reindex(s["hour_ts"]).to_numpy()

    # Añadir rasgos propios de north_mixture.features
    for col in f.columns:
        s[col] = f[col].to_numpy()

    # Rasgos físicos adicionales (estimación analítica de sigma con racha y velocidad como en protocol.py)
    g_ratio = np.clip((s["wsmax"] / s["ws"].where(s["ws"] > 0)).to_numpy(float) - 1.0, 0.02, None)
    ws_clip = np.clip(s["ws"].to_numpy(float), 0.3, None)
    # Ajuste log-log de SD1 en semanas pares de la propia estación (o aproximación universal)
    tr_sd = (s["week"] == 0) & (s["ws"] > 0) & s["SD1"].notna() & np.isfinite(g_ratio)
    x_sd = np.column_stack([np.ones(tr_sd.sum()), np.log(g_ratio[tr_sd]), np.log(ws_clip[tr_sd])])
    y_sd = np.log(np.clip(s.loc[tr_sd, "SD1"].to_numpy(float), 0.5, None))
    coef_sd, *_ = np.linalg.lstsq(x_sd, y_sd, rcond=None)
    sigma_est = np.clip(
        np.exp(coef_sd[0] + coef_sd[1] * np.log(g_ratio) + coef_sd[2] * np.log(ws_clip)),
        1.0,
        120.0,
    )
    sigma_est = np.where(np.isfinite(sigma_est), sigma_est, np.nanmedian(sigma_est))
    s["sigma_est"] = sigma_est
    s["mu"] = mixture_direction(s["A"].to_numpy(float), sigma_est)
    s["mu_ratio"] = angular_dist(s["mu"], 0.0) / sigma_est
    s["dcos_nb"] = np.cos(np.deg2rad(angular_dist(s["mu"], s["nb_dir"]))) - np.cos(
        np.deg2rad(angular_dist(s["A"], s["nb_dir"]))
    )

    cand = np.where(
        (s["ws"] > 0) & s["A"].notna(),
        np.where(angular_dist(s["A"], 0.0) < angular_dist(s["mu"], 0.0), s["A"], s["mu"]),
        np.nan,
    )
    near_cand = (angular_dist(cand, 0.0) <= NEAR_NORTH).astype(float)
    bigjump = (s["jump_prev"] > 60).astype(float)
    for w in ROLL:
        s[f"north_cand_{w}"] = rolling(near_cand, w)
        s[f"bigjump_{w}"] = rolling(bigjump, w)

    # Rasgos derivados del consenso
    s["dn_cons_d1"] = angular_dist(s["comb_d1"], 0.0)
    s["dist_a_cons_d1"] = angular_dist(s["A"], s["comb_d1"])
    s["dcos_cons_d1"] = np.cos(np.deg2rad(angular_dist(s["mu"], s["comb_d1"]))) - np.cos(
        np.deg2rad(angular_dist(s["A"], s["comb_d1"]))
    )
    s["dn_cons_r4"] = angular_dist(s["comb_r4"], 0.0)
    s["dist_a_cons_r4"] = angular_dist(s["A"], s["comb_r4"])
    s["dcos_cons_r4"] = np.cos(np.deg2rad(angular_dist(s["mu"], s["comb_r4"]))) - np.cos(
        np.deg2rad(angular_dist(s["A"], s["comb_r4"]))
    )

    return s, df, h


def analyze_point1_and_point2():
    pivots, _ = load_hourly_network()
    station_data = {}
    for st_key in MAIN_TARGETS:
        station_data[st_key] = load_station_5min(st_key, pivots)

    print("================================================================================")
    print("PUNTO 1: ZONA AMBIGUA A en [150°, 300°] - SEPARACIÓN H1 (D1<=45°) vs H0 (D1>=90°)")
    print("================================================================================")

    p1_rows = []
    lr_table_rows = []
    univariate_rows = []

    for st_key in MAIN_TARGETS:
        s, df, h = station_data[st_key]
        valid = (s["ws"] > 0) & s["A"].notna() & s["D1"].notna() & s["comb_d1"].notna()
        amb = valid & (s["A"] >= 150.0) & (s["A"] <= 300.0)
        d1_dn = angular_dist(s["D1"], 0.0)

        is_h1 = d1_dn <= 45.0
        is_h0 = d1_dn >= 90.0
        is_mid = (d1_dn > 45.0) & (d1_dn < 90.0)

        for split_name, split_mask in [("Semanas impares (prueba)", s["week"] == 1), ("Todas las semanas", s["week"].isin([0, 1]))]:
            sub_all = s[amb & split_mask]
            sub = s[amb & split_mask & (is_h1 | is_h0)].copy()
            y = (angular_dist(sub["D1"], 0.0) <= 45.0).astype(int).to_numpy()

            # Score del consenso: cuanto más cerca del norte (menor dn_cons), más probable H1
            score_dn_cons = -sub["dn_cons_d1"].to_numpy()
            score_dcos_cons = sub["dcos_cons_d1"].to_numpy()
            score_dist_cons = sub["dist_a_cons_d1"].to_numpy()
            score_dn_r4 = -sub["dn_cons_r4"].fillna(90.0).to_numpy()

            auc_dn = roc_auc_score(y, score_dn_cons)
            auc_dcos = roc_auc_score(y, score_dcos_cons)
            auc_dist = roc_auc_score(y, score_dist_cons)
            auc_r4 = roc_auc_score(y, score_dn_r4)

            p1_rows.append({
                "Estación": TARGET_MAP[st_key],
                "Muestra": split_name,
                "N_amb": len(sub_all),
                "N_H1 (<=45°)": int((y == 1).sum()),
                "N_H0 (>=90°)": int((y == 0).sum()),
                "N_interm (45-90°)": int((amb & split_mask & is_mid).sum()),
                "%H1": f"{100 * y.mean():.1f}%",
                "AUC (-dn_cons)": f"{auc_dn:.3f}",
                "AUC (dcos_cons)": f"{auc_dcos:.3f}",
                "AUC (|A-cons|)": f"{auc_dist:.3f}",
                "AUC (-dn_cons R4)": f"{auc_r4:.3f}",
            })

            if split_name == "Semanas impares (prueba)":
                # Razones de verosimilitud por franja de distancia del consenso al norte
                dn_c = sub["dn_cons_d1"].to_numpy()
                bins = [
                    ("Consenso cerca del norte (<= 45°)", dn_c <= 45.0),
                    ("Consenso moderado (45° - 90°)", (dn_c > 45.0) & (dn_c < 90.0)),
                    ("Consenso lejos del norte (>= 90°)", dn_c >= 90.0),
                    ("  - del cual: entre 90° y 135°", (dn_c >= 90.0) & (dn_c < 135.0)),
                    ("  - del cual: muy lejos (>= 135°)", dn_c >= 135.0),
                    ("Consenso en mitad norte (<= 60°)", dn_c <= 60.0),
                ]
                for b_label, b_mask in bins:
                    p_h1 = b_mask[y == 1].mean()
                    p_h0 = b_mask[y == 0].mean()
                    lr = p_h1 / p_h0 if p_h0 > 0 else np.inf
                    post_h1 = (b_mask & (y == 1)).sum() / max(b_mask.sum(), 1) * 100
                    lr_table_rows.append({
                        "Estación": TARGET_MAP[st_key],
                        "Condición consenso": b_label,
                        "N": int(b_mask.sum()),
                        "P(cond | H1)": f"{p_h1 * 100:.1f}%",
                        "P(cond | H0)": f"{p_h0 * 100:.1f}%",
                        "LR = P(c|H1)/P(c|H0)": f"{lr:.2f}",
                        "P(H1 | cond)": f"{post_h1:.1f}%",
                    })

                # Comparación de AUC univariado en semanas impares (prueba)
                cand_feats = [
                    ("Consenso: -dn_cons (cercanía al N)", -sub["dn_cons_d1"]),
                    ("Consenso: dcos_cons", sub["dcos_cons_d1"]),
                    ("Consenso: |A - cons|", sub["dist_a_cons_d1"]),
                    ("Propio: -nb_north (vecinos ±15m cerca del N)", -sub["nb_north"]),
                    ("Propio: dist_nb (|A - nb_dir|)", sub["dist_nb"]),
                    ("Propio: -r_nb (dispersión vecinos ±15m)", -sub["r_nb"]),
                    ("Propio: max(jump_prev, jump_next)", np.maximum(sub["jump_prev"], sub["jump_next"])),
                    ("Propio: jump_prev", sub["jump_prev"]),
                    ("Propio: jump_next", sub["jump_next"]),
                    ("Propio: frac_north_6 (±30m <=30°)", sub["frac_north_6"]),
                    ("Propio: north_cand_6 (candidatos <=30° ±30m)", sub["north_cand_6"]),
                    ("Propio: bigjump_6 (saltos >60° ±30m)", sub["bigjump_6"]),
                    ("Propio: dcos_nb", sub["dcos_nb"]),
                    ("Propio: gust (WS_Max / WS_Avg)", sub["gust"]),
                    ("Propio: -ws (baja velocidad)", -sub["ws"]),
                    ("Propio: -mu_ratio (-|μ|/σ)", -sub["mu_ratio"]),
                    ("Propio: hod_cos (ciclo diurno coseno)", sub["hod_cos"]),
                ]
                u_dict = {"Rasgo": [cf[0] for cf in cand_feats]}
                u_aucs = []
                for fname, fval in cand_feats:
                    ok_f = fval.notna().to_numpy()
                    u_aucs.append(roc_auc_score(y[ok_f], fval.to_numpy()[ok_f]))
                univariate_rows.append((TARGET_MAP[st_key], dict(zip([cf[0] for cf in cand_feats], u_aucs))))

    print("\n--- Tabla 1A: Conteos y AUC del consenso horario en A in [150°, 300°] ---")
    print(pd.DataFrame(p1_rows).to_string(index=False))

    print("\n--- Tabla 1B: Razones de verosimilitud (LR) en semanas de prueba (impares) ---")
    print(pd.DataFrame(lr_table_rows).to_string(index=False))

    print("\n--- Tabla 1C: AUC univariado de cada rasgo en A in [150°, 300°] (semanas impares) ---")
    df_uni = pd.DataFrame({st_name: d for st_name, d in univariate_rows})
    df_uni["Media 3 est."] = df_uni.mean(axis=1)
    print(df_uni.round(3).to_string())

    # ==============================================================================
    # VERIFICACIÓN DEL EJEMPLO DE LA AFIRMACIÓN 10 EN CORTADERA DE NOCHE
    # ==============================================================================
    print("\n================================================================================")
    print("VERIFICACIÓN DEL EJEMPLO DE LA AFIRMACIÓN 10: CORTADERA DE NOCHE (22-06h)")
    print("================================================================================")
    s_cor = station_data["cortadera"][0]
    valid_cor = (s_cor["ws"] > 0) & s_cor["A"].notna() & s_cor["D1"].notna()
    night_cor = valid_cor & (s_cor["band"] == 1)
    d1_cor_night = s_cor.loc[night_cor, "D1"]
    a_cor_night = s_cor.loc[night_cor, "A"]
    dn_cor_night = angular_dist(d1_cor_night, 0.0)
    print(f"Cortadera de noche (22-06h): N={night_cor.sum()} registros de 5 min válidos.")
    print(f"  Distribución real D1 de noche en Cortadera:")
    print(f"    Norte (D1 <= 45°): {(dn_cor_night <= 45).mean()*100:.1f}% (N={(dn_cor_night <= 45).sum()})")
    print(f"    NE-E (D1 en 45-90°): {d1_cor_night.between(45, 90).mean()*100:.1f}% (N={d1_cor_night.between(45, 90).sum()})")
    print(f"    SE (D1 en 90-150°): {d1_cor_night.between(90, 150).mean()*100:.1f}% (N={d1_cor_night.between(90, 150).sum()})")
    print(f"    Sur (D1 en 150-210°): {d1_cor_night.between(150, 210).mean()*100:.1f}% (N={d1_cor_night.between(150, 210).sum()})")
    print(f"    Oeste (D1 en 210-315°): {d1_cor_night.between(210, 315).mean()*100:.1f}% (N={d1_cor_night.between(210, 315).sum()})")

    for a_rng_name, m_sub in [
        ("De noche (22-06h) con A en 150-300°", night_cor & s_cor["A"].between(150, 300)),
        ("De noche (22-06h) con A en 210-270° (~240°)", night_cor & s_cor["A"].between(210, 270)),
        ("De noche estricta (23-05h) con A en 210-270° (~240°)", valid_cor & s_cor.index.hour.isin([23, 0, 1, 2, 3, 4, 5]) & s_cor["A"].between(210, 270)),
        ("De noche (22-06h) con A en 210-270° + consenso drenaje (<=135°)", night_cor & s_cor["A"].between(210, 270) & (s_cor["comb_d1"].between(0, 135) | (s_cor["comb_d1"] >= 315))),
        ("De noche (22-06h) con A en 210-270° + consenso norte (<=60°)", night_cor & s_cor["A"].between(210, 270) & (s_cor["dn_cons_d1"] <= 60)),
        ("De noche (22-06h) con A en 210-270° + propio salto >45° (max_jump>45°)", night_cor & s_cor["A"].between(210, 270) & (np.maximum(s_cor["jump_prev"], s_cor["jump_next"]) > 45)),
        ("De noche (22-06h) con A en 210-270° + propio estable (max_jump<=25°)", night_cor & s_cor["A"].between(210, 270) & (np.maximum(s_cor["jump_prev"], s_cor["jump_next"]) <= 25)),
    ]:
        d1_sub = s_cor.loc[m_sub, "D1"]
        dn_sub = angular_dist(d1_sub, 0.0)
        print(f"  {a_rng_name}: N={m_sub.sum()} registros:")
        print(f"    H1 (D1 <= 45°, mezcla norte): {(dn_sub <= 45).mean()*100:.1f}% (N={(dn_sub <= 45).sum()})")
        print(f"    Intermedio (D1 en 45-90°, NE-E): {((dn_sub > 45) & (dn_sub < 90)).mean()*100:.1f}% (N={((dn_sub > 45) & (dn_sub < 90)).sum()})")
        print(f"    H0 (D1 >= 90°, viento real SE/S/O): {(dn_sub >= 90).mean()*100:.1f}% (N={(dn_sub >= 90).sum()})")
        print(f"      - del cual D1 en 90-180° (drenaje SE): {d1_sub.between(90, 180).mean()*100:.1f}% (N={d1_sub.between(90, 180).sum()})")
        print(f"      - del cual D1 en 180-315° (S-O real): {d1_sub.between(180, 315).mean()*100:.1f}% (N={d1_sub.between(180, 315).sum()})")

    # ==============================================================================
    # PUNTO 2: REGRESIÓN LOGÍSTICA Y HGB CON Y SIN CONSENSO (VALIDACIÓN POR SEMANAS)
    # ==============================================================================
    print("\n================================================================================")
    print("PUNTO 2: MODELOS MULTIVARIADOS CON Y SIN CONSENSO (ENTRENAMIENTO PARES -> PRUEBA IMPARES)")
    print("================================================================================")

    cons_cols_d1 = ["dn_cons_d1", "dist_a_cons_d1", "dcos_cons_d1", "r_cons_d1"]
    cons_cols_r4 = ["dn_cons_r4", "dist_a_cons_r4", "dcos_cons_r4", "r_cons_r4"]
    base_no_hod = [c for c in BASE if c not in ("hod_sin", "hod_cos")]
    phys_extra = ["sigma_est", "mu_ratio", "dcos_nb", "north_cand_3", "north_cand_6", "north_cand_12", "bigjump_3", "bigjump_6", "bigjump_12"]
    full_own = BASE + phys_extra

    feature_sets = [
        ("1. Solo consenso (D1-cal)", cons_cols_d1),
        ("2. Solo consenso (R4-cal, sin D1)", cons_cols_r4),
        ("3. Propios BASE sin hora (10 rasgos)", base_no_hod),
        ("4. Propios BASE sin hora + consenso", base_no_hod + cons_cols_d1),
        ("5. Propios BASE (12 rasgos north_mixture.features)", BASE),
        ("6. Propios BASE + consenso (D1-cal)", BASE + cons_cols_d1),
        ("7. Propios BASE + consenso (R4-cal)", BASE + cons_cols_r4),
        ("8. Propios Etapa 1 completa (BASE + físicos)", full_own),
        ("9. Propios Etapa 1 completa + consenso (D1-cal)", full_own + cons_cols_d1),
    ]

    # A) Entrenamiento y evaluación dentro de cada estación (semanas pares -> impares) en zona ambigua A in [150, 300]
    model_rows_amb = []
    for st_key in MAIN_TARGETS:
        s, _, _ = station_data[st_key]
        valid = (s["ws"] > 0) & s["A"].notna() & s["D1"].notna() & s["comb_d1"].notna()
        amb = valid & (s["A"] >= 150.0) & (s["A"] <= 300.0)
        d1_dn = angular_dist(s["D1"], 0.0)
        h1_or_h0 = (d1_dn <= 45.0) | (d1_dn >= 90.0)

        tr_mask = amb & h1_or_h0 & (s["week"] == 0)
        te_mask = amb & h1_or_h0 & (s["week"] == 1)
        y_tr = (d1_dn[tr_mask] <= 45.0).astype(int).to_numpy()
        y_te = (d1_dn[te_mask] <= 45.0).astype(int).to_numpy()

        for fs_name, cols in feature_sets:
            x_tr = s.loc[tr_mask, cols].to_numpy(float)
            x_te = s.loc[te_mask, cols].to_numpy(float)

            lr = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            lr.fit(x_tr, y_tr)
            p_lr = lr.predict_proba(x_te)[:, 1]
            auc_lr = roc_auc_score(y_te, p_lr)

            hgb = HistGradientBoostingClassifier(max_iter=80, random_state=0)
            hgb.fit(x_tr, y_tr)
            p_hgb = hgb.predict_proba(x_te)[:, 1]
            auc_hgb = roc_auc_score(y_te, p_hgb)

            model_rows_amb.append({
                "Estación": TARGET_MAP[st_key],
                "Conjunto de rasgos": fs_name,
                "AUC_LR": auc_lr,
                "AUC_HGB": auc_hgb,
            })

    df_m_amb = pd.DataFrame(model_rows_amb)
    piv_lr = df_m_amb.pivot(index="Conjunto de rasgos", columns="Estación", values="AUC_LR")
    piv_lr["Media"] = piv_lr.mean(axis=1)
    piv_hgb = df_m_amb.pivot(index="Conjunto de rasgos", columns="Estación", values="AUC_HGB")
    piv_hgb["Media"] = piv_hgb.mean(axis=1)

    print("\n--- Tabla 2A: AUC de Regresión Logística en A in [150°, 300°] (entrenado en sem. pares, evaluado en impares) ---")
    print(piv_lr.round(4).to_string())

    print("\n--- Tabla 2B: AUC de HistGradientBoosting en A in [150°, 300°] (entrenado en sem. pares, evaluado en impares) ---")
    print(piv_hgb.round(4).to_string())

    # B) Entrenamiento sobre TODOS los registros de 5 min (como hace north_mixture.py) y evaluación tanto de AUC en [150, 300]
    #    como del ERROR HORARIO (en grados) con Etapa 1 y Etapa 2!
    print("\n================================================================================")
    print("IMPACTO EN EL CLASIFICADOR COMPLETO (TODOS LOS REGISTROS + ETAPA 2 + ERROR HORARIO)")
    print("================================================================================")

    hourly_eval_rows = []
    for st_key in MAIN_TARGETS:
        s, df, h = station_data[st_key]
        valid = (s["ws"] > 0) & s["A"].notna() & s["D1"].notna() & s["comb_d1"].notna()
        y_all = (angular_dist(s["D1"], s["mu"]) < angular_dist(s["D1"], s["A"])).astype(int).to_numpy()
        tr_all = valid & (s["week"] == 0)
        te_all = valid & (s["week"] == 1)

        amb_te = te_all & (s["A"] >= 150.0) & (s["A"] <= 300.0) & ((angular_dist(s["D1"], 0.0) <= 45.0) | (angular_dist(s["D1"], 0.0) >= 90.0))
        y_amb_te = (angular_dist(s.loc[amb_te, "D1"], 0.0) <= 45.0).astype(int).to_numpy()

        # Mascara de horas de prueba (semanas impares)
        h_ts = df["TIMESTAMP"]
        h_week = (((h_ts - h_ts.min()) // pd.Timedelta(days=7)) % 2).to_numpy()
        # Alinear week horario con el de la red
        cons_d1 = compute_consensus_pairs(pivots, TARGET_MAP[st_key])
        h_week_net = cons_d1["week"].reindex(df["TIMESTAMP"]).to_numpy()
        h_mask_te = valid_mask(h).to_numpy() & (h_week_net == 1)
        truth_h = h["truth"].to_numpy()
        north_h = h_mask_te & (angular_dist(truth_h, 0.0) <= 45.0)

        b_dict = {
            "moving": ((s["ws"] > 0) & s["A"].notna()).to_numpy(),
            "row": s["row"].fillna(-1).astype(int).to_numpy(),
            "A": s["A"].to_numpy(float),
            "truth": truth_h,
        }
        mu_arr = s["mu"].to_numpy(float)

        # Error V1 base
        v1_h = h["V1"].to_numpy()
        hourly_eval_rows.append({
            "Estación": TARGET_MAP[st_key],
            "Modelo": "0. V1 (sin corrección)",
            "AUC_amb_E1": np.nan,
            "AUC_amb_E2": np.nan,
            "Err_todas (°)": angular_dist(v1_h[h_mask_te], truth_h[h_mask_te]).mean(),
            "Err_norte (°)": angular_dist(v1_h[north_h], truth_h[north_h]).mean(),
            "Err_resto (°)": angular_dist(v1_h[h_mask_te & ~north_h], truth_h[h_mask_te & ~north_h]).mean(),
        })

        for m_label, kind, cols in [
            ("1. LR BASE (12 rasgos)", "lr", BASE),
            ("2. LR BASE + consenso", "lr", BASE + cons_cols_d1),
            ("3. LR Etapa1+2 (propios)", "lr", full_own),
            ("4. LR Etapa1+2 + consenso (D1)", "lr", full_own + cons_cols_d1),
            ("5. LR Etapa1+2 + consenso (R4)", "lr", full_own + cons_cols_r4),
            ("6. HGB Etapa1+2 (propios)", "hgb", full_own),
            ("7. HGB Etapa1+2 + consenso (D1)", "hgb", full_own + cons_cols_d1),
            ("8. HGB Etapa1+2 + consenso (R4)", "hgb", full_own + cons_cols_r4),
        ]:
            x_full = s[cols].to_numpy(float)
            if kind == "lr":
                clf1 = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
                clf2 = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            else:
                clf1 = HistGradientBoostingClassifier(max_iter=80, random_state=0)
                clf2 = HistGradientBoostingClassifier(max_iter=80, random_state=0)

            clf1.fit(x_full[tr_all.to_numpy()], y_all[tr_all.to_numpy()])
            p1 = np.zeros(len(s), dtype=float)
            ok_x = s["A"].notna().to_numpy()
            p1[ok_x] = clf1.predict_proba(x_full[ok_x])[:, 1]

            auc_e1 = roc_auc_score(y_amb_te, p1[amb_te.to_numpy()])

            # Etapa 2: añadir medias móviles de p1 en ±3, ±6, ±12
            x2_full = np.column_stack([x_full, p1] + [rolling(p1, w) for w in ROLL])
            clf2.fit(x2_full[tr_all.to_numpy()], y_all[tr_all.to_numpy()])
            p2 = np.zeros(len(s), dtype=float)
            p2[ok_x] = clf2.predict_proba(x2_full[ok_x])[:, 1]

            auc_e2 = roc_auc_score(y_amb_te, p2[amb_te.to_numpy()])

            est_h = soft_hourly(b_dict, mu_arr, p2)
            hourly_eval_rows.append({
                "Estación": TARGET_MAP[st_key],
                "Modelo": m_label,
                "AUC_amb_E1": auc_e1,
                "AUC_amb_E2": auc_e2,
                "Err_todas (°)": angular_dist(est_h[h_mask_te], truth_h[h_mask_te]).mean(),
                "Err_norte (°)": angular_dist(est_h[north_h], truth_h[north_h]).mean(),
                "Err_resto (°)": angular_dist(est_h[h_mask_te & ~north_h], truth_h[h_mask_te & ~north_h]).mean(),
            })

    df_he = pd.DataFrame(hourly_eval_rows)
    print(df_he.round(3).to_string(index=False))

    # ==============================================================================
    # C) VALIDACIÓN ENTRE ESTACIONES (LOSO: entrenar en 2 estaciones, probar en la 3ª)
    # ==============================================================================
    print("\n================================================================================")
    print("VALIDACIÓN ENTRE ESTACIONES (LOSO: ENTRENAR EN LAS OTRAS 2, EVALUAR EN LA 3ª)")
    print("================================================================================")
    loso_rows = []
    for te_key in MAIN_TARGETS:
        tr_keys = [k for k in MAIN_TARGETS if k != te_key]
        s_te, df_te, h_te = station_data[te_key]
        valid_te = (s_te["ws"] > 0) & s_te["A"].notna() & s_te["D1"].notna() & s_te["comb_d1"].notna()
        te_mask = valid_te & (s_te["week"] == 1)
        amb_te = te_mask & (s_te["A"] >= 150.0) & (s_te["A"] <= 300.0) & (
            (angular_dist(s_te["D1"], 0.0) <= 45.0) | (angular_dist(s_te["D1"], 0.0) >= 90.0)
        )
        y_amb_te = (angular_dist(s_te.loc[amb_te, "D1"], 0.0) <= 45.0).astype(int).to_numpy()

        cons_d1 = compute_consensus_pairs(pivots, TARGET_MAP[te_key])
        h_week_net = cons_d1["week"].reindex(df_te["TIMESTAMP"]).to_numpy()
        h_mask_te = valid_mask(h_te).to_numpy() & (h_week_net == 1)
        truth_h = h_te["truth"].to_numpy()
        north_h = h_mask_te & (angular_dist(truth_h, 0.0) <= 45.0)

        b_dict = {
            "moving": ((s_te["ws"] > 0) & s_te["A"].notna()).to_numpy(),
            "row": s_te["row"].fillna(-1).astype(int).to_numpy(),
            "A": s_te["A"].to_numpy(float),
            "truth": truth_h,
        }
        mu_arr = s_te["mu"].to_numpy(float)

        for m_label, kind, cols in [
            ("LR BASE (12 rasgos)", "lr", BASE),
            ("LR BASE + consenso (D1)", "lr", BASE + cons_cols_d1),
            ("LR BASE + consenso (R4)", "lr", BASE + cons_cols_r4),
            ("LR Etapa1+2 (propios)", "lr", full_own),
            ("LR Etapa1+2 + consenso (D1)", "lr", full_own + cons_cols_d1),
            ("LR Etapa1+2 + consenso (R4)", "lr", full_own + cons_cols_r4),
            ("HGB Etapa1+2 (propios)", "hgb", full_own),
            ("HGB Etapa1+2 + consenso (D1)", "hgb", full_own + cons_cols_d1),
            ("HGB Etapa1+2 + consenso (R4)", "hgb", full_own + cons_cols_r4),
        ]:
            x_trs, y_trs = [], []
            for k in tr_keys:
                s_k = station_data[k][0]
                v_k = (s_k["ws"] > 0) & s_k["A"].notna() & s_k["D1"].notna() & s_k["comb_d1"].notna() & (s_k["week"] == 0)
                x_trs.append(s_k.loc[v_k, cols].to_numpy(float))
                yk = (angular_dist(s_k.loc[v_k, "D1"], s_k.loc[v_k, "mu"]) < angular_dist(s_k.loc[v_k, "D1"], s_k.loc[v_k, "A"])).astype(int).to_numpy()
                y_trs.append(yk)
            x_tr_all = np.vstack(x_trs)
            y_tr_all = np.concatenate(y_trs)

            if kind == "lr":
                clf1 = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
                clf2 = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            else:
                clf1 = HistGradientBoostingClassifier(max_iter=80, random_state=0)
                clf2 = HistGradientBoostingClassifier(max_iter=80, random_state=0)

            clf1.fit(x_tr_all, y_tr_all)

            # Predicción etapa 1 en estaciones de entrenamiento y prueba
            x2_trs = []
            for k in tr_keys:
                s_k = station_data[k][0]
                v_k = (s_k["ws"] > 0) & s_k["A"].notna() & s_k["D1"].notna() & s_k["comb_d1"].notna() & (s_k["week"] == 0)
                xk_full = s_k[cols].to_numpy(float)
                ok_k = s_k["A"].notna().to_numpy()
                p1_k = np.zeros(len(s_k), dtype=float)
                p1_k[ok_k] = clf1.predict_proba(xk_full[ok_k])[:, 1]
                x2_k = np.column_stack([xk_full, p1_k] + [rolling(p1_k, w) for w in ROLL])
                x2_trs.append(x2_k[v_k.to_numpy()])

            clf2.fit(np.vstack(x2_trs), y_tr_all)

            x_te_full = s_te[cols].to_numpy(float)
            ok_te = s_te["A"].notna().to_numpy()
            p1_te = np.zeros(len(s_te), dtype=float)
            p1_te[ok_te] = clf1.predict_proba(x_te_full[ok_te])[:, 1]
            auc_e1 = roc_auc_score(y_amb_te, p1_te[amb_te.to_numpy()])

            x2_te_full = np.column_stack([x_te_full, p1_te] + [rolling(p1_te, w) for w in ROLL])
            p2_te = np.zeros(len(s_te), dtype=float)
            p2_te[ok_te] = clf2.predict_proba(x2_te_full[ok_te])[:, 1]
            auc_e2 = roc_auc_score(y_amb_te, p2_te[amb_te.to_numpy()])

            est_h = soft_hourly(b_dict, mu_arr, p2_te)
            loso_rows.append({
                "Estación": TARGET_MAP[te_key],
                "Modelo (LOSO)": m_label,
                "AUC_amb_E1": auc_e1,
                "AUC_amb_E2": auc_e2,
                "Err_todas (°)": angular_dist(est_h[h_mask_te], truth_h[h_mask_te]).mean(),
                "Err_norte (°)": angular_dist(est_h[north_h], truth_h[north_h]).mean(),
                "Err_resto (°)": angular_dist(est_h[h_mask_te & ~north_h], truth_h[h_mask_te & ~north_h]).mean(),
            })

    df_loso = pd.DataFrame(loso_rows)
    print(df_loso.round(3).to_string(index=False))

    # ==============================================================================
    # D) ¿DÓNDE PODRÍA APORTAR EL CONSENSO? SUBGRUPOS: frac_north_6 == 0 vs > 0
    # ==============================================================================
    print("\n================================================================================")
    print("SUBGRUPOS EN A in [150°, 300°]: ¿QUÉ PASA CUANDO NINGÚN VECINO DE 5 MIN ESTÁ EN EL NORTE (frac_north_6 == 0)?")
    print("================================================================================")
    sub_rows = []
    for st_key in MAIN_TARGETS:
        s, _, _ = station_data[st_key]
        valid = (s["ws"] > 0) & s["A"].notna() & s["D1"].notna() & s["comb_d1"].notna()
        amb = valid & (s["A"] >= 150.0) & (s["A"] <= 300.0)
        d1_dn = angular_dist(s["D1"], 0.0)
        h1_or_h0 = (d1_dn <= 45.0) | (d1_dn >= 90.0)

        tr_m = amb & h1_or_h0 & (s["week"] == 0)
        te_m = amb & h1_or_h0 & (s["week"] == 1)

        lr_own = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
        lr_both = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))

        y_tr = (d1_dn[tr_m] <= 45.0).astype(int).to_numpy()
        lr_own.fit(s.loc[tr_m, BASE].to_numpy(float), y_tr)
        lr_both.fit(s.loc[tr_m, BASE + cons_cols_d1].to_numpy(float), y_tr)

        for grp_name, grp_cond in [
            ("Sin vecinos 5m en el norte (frac_north_6 == 0)", s["frac_north_6"] == 0),
            ("Con algún vecino 5m en el norte (frac_north_6 > 0)", s["frac_north_6"] > 0),
            ("Sin candidatos norte en ±30m (north_cand_6 == 0)", s["north_cand_6"] == 0),
        ]:
            m_g = te_m & grp_cond
            yg = (d1_dn[m_g] <= 45.0).astype(int).to_numpy()
            if len(np.unique(yg)) < 2:
                continue
            p_cons = -s.loc[m_g, "dn_cons_d1"].to_numpy(float)
            p_own = lr_own.predict_proba(s.loc[m_g, BASE].to_numpy(float))[:, 1]
            p_both = lr_both.predict_proba(s.loc[m_g, BASE + cons_cols_d1].to_numpy(float))[:, 1]
            sub_rows.append({
                "Estación": TARGET_MAP[st_key],
                "Subgrupo": grp_name,
                "N_te": len(yg),
                "N_H1": int(yg.sum()),
                "%H1": f"{100*yg.mean():.1f}%",
                "AUC_cons_solo": round(roc_auc_score(yg, p_cons), 4),
                "AUC_LR_BASE": round(roc_auc_score(yg, p_own), 4),
                "AUC_LR_BASE+cons": round(roc_auc_score(yg, p_both), 4),
            })
    print(pd.DataFrame(sub_rows).to_string(index=False))


if __name__ == "__main__":
    analyze_point1_and_point2()
