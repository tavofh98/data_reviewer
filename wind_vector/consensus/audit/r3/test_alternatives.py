"""Prueba de alternativas para usar las vecinas (y el régimen propio R4) frente al consenso por pares en r3."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from wind_vector.analyze import valid_mask
from wind_vector.consensus.audit.r3.analyze_r3 import (
    BASE,
    MAIN_TARGETS,
    ROLL,
    TARGET_MAP,
    angular_dist,
    compute_consensus_pairs,
    load_hourly_network,
    load_station_5min,
    rolling,
    soft_hourly,
)

warnings.filterwarnings("ignore")


def evaluate_alternatives():
    pivots, xy = load_hourly_network()
    d_mat = pivots["dir"]
    ws_mat = pivots["ws"]

    # 1. Índice sinóptico crudo de la red (media vectorial ponderada por velocidad de toda la red limpia, sin calibrar hacia la media de la estación)
    u_net = (ws_mat * np.sin(np.deg2rad(d_mat))).mean(axis=1)
    w_net = (ws_mat * np.cos(np.deg2rad(d_mat))).mean(axis=1)
    net_dir = pd.Series(np.rad2deg(np.arctan2(u_net, w_net)) % 360.0, index=d_mat.index)
    net_r = pd.Series(np.hypot(u_net, w_net) / ws_mat.mean(axis=1), index=d_mat.index)

    rows = []
    for st_key in MAIN_TARGETS:
        s, df, h = load_station_5min(st_key, pivots)
        db_name = TARGET_MAP[st_key]

        # Vecinas crudas más correlacionadas (vectores sin/cos directos de las 3 mejores vecinas)
        best_nbs = {
            "cortadera": ["Calientes1", "Alto_Tala", "Tala-1"],
            "papujune": ["Alto_Quellaveco", "Minas_Sur", "Tala-1"],
            "tala1": ["Alto_Tala", "Papujune", "Charaque"],
        }[st_key]
        raw_nb_cols = []
        for nb in best_nbs:
            if nb in d_mat.columns:
                nb_deg = d_mat[nb].reindex(s["hour_ts"]).to_numpy(float)
                s[f"sin_{nb}"] = np.sin(np.deg2rad(nb_deg))
                s[f"cos_{nb}"] = np.cos(np.deg2rad(nb_deg))
                s[f"dist_a_{nb}"] = angular_dist(s["A"], nb_deg)
                raw_nb_cols.extend([f"sin_{nb}", f"cos_{nb}", f"dist_a_{nb}"])

        # Red sinóptica cruda
        nd = net_dir.reindex(s["hour_ts"]).to_numpy(float)
        s["net_dn"] = angular_dist(nd, 0.0)
        s["net_dist_a"] = angular_dist(s["A"], nd)
        s["net_r"] = net_r.reindex(s["hour_ts"]).to_numpy(float)
        net_cols = ["net_dn", "net_dist_a", "net_r"]

        # Prior empírico propio R4 (SIN VECINAS): frecuencia con que un viento real estable (max_jump <= 20° en sem. pares)
        # cae en el sector de A (16 sectores × 3 franjas horarias)
        sec_a = (((s["A"].fillna(0.0) + 11.25) % 360.0) // 22.5).astype(int)
        stable_tr = (s["week"] == 0) & (s["ws"] > 0) & s["A"].notna() & (s["dn"] > 35.0) & (
            np.maximum(s["jump_prev"], s["jump_next"]) <= 20.0
        ) & (s["r_nb"] >= 0.92)
        key_ab = pd.Series(sec_a.astype(str) + "_" + s["band"].fillna(-1).astype(int).astype(str), index=s.index)
        band_s = s["band"].fillna(-1).astype(int)
        counts_key = key_ab[stable_tr].value_counts()
        counts_band = band_s[stable_tr].value_counts()
        prior_r4 = np.array([
            counts_key.get(k, 0) / max(counts_band.get(b, 1), 1)
            for k, b in zip(key_ab, band_s)
        ], dtype=float)
        s["own_r4_prior"] = prior_r4
        s["own_r4_log_prior"] = np.log(prior_r4 + 1e-4)

        phys_extra = [
            "sigma_est", "mu_ratio", "dcos_nb",
            "north_cand_3", "north_cand_6", "north_cand_12",
            "bigjump_3", "bigjump_6", "bigjump_12",
        ]
        full_own = BASE + phys_extra
        cons_cols_d1 = ["dn_cons_d1", "dist_a_cons_d1", "dcos_cons_d1", "r_cons_d1"]

        valid = (s["ws"] > 0) & s["A"].notna() & s["D1"].notna() & s["comb_d1"].notna()
        tr_all = valid & (s["week"] == 0)
        te_all = valid & (s["week"] == 1)
        y_all = (angular_dist(s["D1"], s["mu"]) < angular_dist(s["D1"], s["A"])).astype(int).to_numpy()

        amb_te = te_all & (s["A"] >= 150.0) & (s["A"] <= 300.0) & (
            (angular_dist(s["D1"], 0.0) <= 45.0) | (angular_dist(s["D1"], 0.0) >= 90.0)
        )
        y_amb_te = (angular_dist(s.loc[amb_te, "D1"], 0.0) <= 45.0).astype(int).to_numpy()

        cons_d1 = compute_consensus_pairs(pivots, db_name)
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

        configs = [
            ("1. Propios Etapa 1+2 (sin vecinas)", full_own),
            ("2. Propios + Consenso por pares (D1-cal)", full_own + cons_cols_d1),
            ("3. Propios + Red sinóptica cruda (sin cal.)", full_own + net_cols),
            ("4. Propios + 3 mejores vecinas crudas (sin/cos/|A-nb|)", full_own + raw_nb_cols),
            ("5. Propios + Prior climático propio R4 (SIN vecinas)", full_own + ["own_r4_prior", "own_r4_log_prior"]),
            ("6. Propios + Prior propio R4 + 3 vecinas crudas", full_own + ["own_r4_prior", "own_r4_log_prior"] + raw_nb_cols),
        ]

        for label, cols in configs:
            x_full = s[cols].to_numpy(float)
            clf1 = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            clf2 = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            clf1.fit(x_full[tr_all.to_numpy()], y_all[tr_all.to_numpy()])
            p1 = np.zeros(len(s), dtype=float)
            ok_x = s["A"].notna().to_numpy()
            p1[ok_x] = clf1.predict_proba(x_full[ok_x])[:, 1]
            auc_e1 = roc_auc_score(y_amb_te, p1[amb_te.to_numpy()])

            x2_full = np.column_stack([x_full, p1] + [rolling(p1, w) for w in ROLL])
            clf2.fit(x2_full[tr_all.to_numpy()], y_all[tr_all.to_numpy()])
            p2 = np.zeros(len(s), dtype=float)
            p2[ok_x] = clf2.predict_proba(x2_full[ok_x])[:, 1]
            auc_e2 = roc_auc_score(y_amb_te, p2[amb_te.to_numpy()])

            est_h = soft_hourly(b_dict, mu_arr, p2)
            rows.append({
                "Estación": db_name,
                "Configuración": label,
                "AUC_amb_E1": auc_e1,
                "AUC_amb_E2": auc_e2,
                "Err_todas (°)": angular_dist(est_h[h_mask_te], truth_h[h_mask_te]).mean(),
                "Err_norte (°)": angular_dist(est_h[north_h], truth_h[north_h]).mean(),
                "Err_resto (°)": angular_dist(est_h[h_mask_te & ~north_h], truth_h[h_mask_te & ~north_h]).mean(),
            })

    df_res = pd.DataFrame(rows)
    print("=== EVALUACIÓN DENTRO DE ESTACIÓN (SEMANAS PARES -> IMPARES) ===")
    print(df_res.round(4).to_string(index=False))

    # También evaluar en LOSO (entrenar en 2 estaciones, evaluar en la 3ª) la Red sinóptica cruda frente a Propios y Consenso por pares
    st_cache = {}
    for st_key in MAIN_TARGETS:
        s, df, h = load_station_5min(st_key, pivots)
        nd = net_dir.reindex(s["hour_ts"]).to_numpy(float)
        s["net_dn"] = angular_dist(nd, 0.0)
        s["net_dist_a"] = angular_dist(s["A"], nd)
        s["net_r"] = net_r.reindex(s["hour_ts"]).to_numpy(float)
        st_cache[st_key] = (s, df, h)

    loso_alt_rows = []
    for te_key in MAIN_TARGETS:
        tr_keys = [k for k in MAIN_TARGETS if k != te_key]
        s_te, df_te, h_te = st_cache[te_key]
        db_name = TARGET_MAP[te_key]
        valid_te = (s_te["ws"] > 0) & s_te["A"].notna() & s_te["D1"].notna() & s_te["comb_d1"].notna()
        te_mask = valid_te & (s_te["week"] == 1)
        amb_te = te_mask & (s_te["A"] >= 150.0) & (s_te["A"] <= 300.0) & (
            (angular_dist(s_te["D1"], 0.0) <= 45.0) | (angular_dist(s_te["D1"], 0.0) >= 90.0)
        )
        y_amb_te = (angular_dist(s_te.loc[amb_te, "D1"], 0.0) <= 45.0).astype(int).to_numpy()
        cons_d1 = compute_consensus_pairs(pivots, db_name)
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

        for label, cols in [
            ("1. LOSO Propios Etapa 1+2 (sin vecinas)", full_own),
            ("2. LOSO Propios + Consenso pares (D1-cal)", full_own + cons_cols_d1),
            ("3. LOSO Propios + Consenso pares (R4-cal)", full_own + ["dn_cons_r4", "dist_a_cons_r4", "dcos_cons_r4", "r_cons_r4"]),
            ("4. LOSO Propios + Red sinóptica cruda (sin cal.)", full_own + ["net_dn", "net_dist_a", "net_r"]),
        ]:
            x_trs, y_trs = [], []
            for k in tr_keys:
                s_k = st_cache[k][0]
                v_k = (s_k["ws"] > 0) & s_k["A"].notna() & s_k["D1"].notna() & s_k["comb_d1"].notna() & (s_k["week"] == 0)
                x_trs.append(s_k.loc[v_k, cols].to_numpy(float))
                yk = (angular_dist(s_k.loc[v_k, "D1"], s_k.loc[v_k, "mu"]) < angular_dist(s_k.loc[v_k, "D1"], s_k.loc[v_k, "A"])).astype(int).to_numpy()
                y_trs.append(yk)
            clf1 = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            clf2 = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
            clf1.fit(np.vstack(x_trs), np.concatenate(y_trs))

            x2_trs = []
            for k in tr_keys:
                s_k = st_cache[k][0]
                v_k = (s_k["ws"] > 0) & s_k["A"].notna() & s_k["D1"].notna() & s_k["comb_d1"].notna() & (s_k["week"] == 0)
                xk_full = s_k[cols].to_numpy(float)
                ok_k = s_k["A"].notna().to_numpy()
                p1_k = np.zeros(len(s_k), dtype=float)
                p1_k[ok_k] = clf1.predict_proba(xk_full[ok_k])[:, 1]
                x2_k = np.column_stack([xk_full, p1_k] + [rolling(p1_k, w) for w in ROLL])
                x2_trs.append(x2_k[v_k.to_numpy()])
            clf2.fit(np.vstack(x2_trs), np.concatenate(y_trs))

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
            loso_alt_rows.append({
                "Estación": db_name,
                "Configuración LOSO": label,
                "AUC_amb_E1": auc_e1,
                "AUC_amb_E2": auc_e2,
                "Err_todas (°)": angular_dist(est_h[h_mask_te], truth_h[h_mask_te]).mean(),
                "Err_norte (°)": angular_dist(est_h[north_h], truth_h[north_h]).mean(),
                "Err_resto (°)": angular_dist(est_h[h_mask_te & ~north_h], truth_h[h_mask_te & ~north_h]).mean(),
            })
    print("\n=== EVALUACIÓN LOSO (ENTRENAR EN 2 ESTACIONES -> PROBAR EN LA 3ª) ===")
    print(pd.DataFrame(loso_alt_rows).round(4).to_string(index=False))


if __name__ == "__main__":
    evaluate_alternatives()
