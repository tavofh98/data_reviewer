"""Auditoría completa del Encargo r1: afirmaciones 1 a 5, corrección de pesos con validación interna y método mejorado."""
import os
import re
import warnings
warnings.filterwarnings("ignore")

import duckdb
import numpy as np
import pandas as pd

BASE_DIR = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc"
DB_PATH = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db"
ST_FILE = os.path.join(BASE_DIR, "met_viewer", "stations.py")
OUT_DIR = os.path.join(BASE_DIR, "wind_vector", "consensus", "audit", "r1")
CACHE_PKL = os.path.join(OUT_DIR, "meteo_r1_cache.pkl")

os.makedirs(OUT_DIR, exist_ok=True)

src = open(ST_FILE, encoding="utf-8").read()
XY = {}
Z = {}
for m in re.finditer(r'"([^"]+)":\s+Station\((\d+),\s*(\d+),\s*(\d+)', src):
    XY[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    Z[m.group(1)] = float(m.group(4))

if not os.path.exists(CACHE_PKL):
    st_list = ",".join(f"'{s}'" for s in sorted(XY.keys()))
    con = duckdb.connect(DB_PATH, read_only=True)
    df_raw = con.execute(f"""
        SELECT estacion_id st, timestamp ts, WindDir_D1_WVT d1, WindDir_Avg a,
               WindDir_SD1_WVT sd1, WS_ms_Avg ws
        FROM meteorologia
        WHERE timestamp >= '2025-11-01' AND timestamp <= '2026-11-03 23:59:59'
          AND estacion_id IN ({st_list})
          AND WindDir_Avg IS NOT NULL
    """).df()
    con.close()
    df_raw.to_pickle(CACHE_PKL)
else:
    df_raw = pd.read_pickle(CACHE_PKL)

ang = lambda a, b: np.minimum(np.abs((a - b) % 360), 360 - np.abs((a - b) % 360))
sdiff = lambda a, b: (a - b + 180) % 360 - 180

TARGETS = [
    "Altarani", "Alto_Quellaveco", "Camp_Quellaveco", "Cortadera",
    "Minas_Sur", "Papujune", "Tala-1", "Tala_Legal"
]

def apply_clean(df):
    """Aplica las exclusiones oficiales de --limpio."""
    df = df.copy()
    drop = {
        "Dique_pie_botadero", "Chalsos", "Mina_Norte", "Planta_Concentradora",
        "Ilo", "Huachunta", "Vizcachas", "Titire"
    }
    df = df[df.st.isin(XY) & ~df.st.isin(drop)]
    df = df[~((df.st == "Sarallenque") & (df.ts < "2026-09-25 21:00"))]
    df = df[df.ws >= 0.5]
    for st, a, b in [
        ("Alto_Quellaveco", "2026-09-15 11:00", "2099"),
        ("Cortadera", "2026-09-13 11:00", "2099"),
        ("Alto_Tala", "2026-08-18 05:00", "2026-09-23 15:00"),
        ("Charaque", "2026-01-14 14:00", "2026-01-15 12:00"),
        ("Charaque", "2026-01-28 14:00", "2026-01-29 07:00"),
        ("Sarallenque_MQG-15-02", "2026-02-16 14:00", "2026-02-17 09:00"),
    ]:
        df = df[~((df.st == st) & (df.ts >= a) & (df.ts <= b))]
    return df

df_clean = apply_clean(df_raw)
df_clean["dir"] = df_clean.d1.fillna(df_clean.a)
P = {c: df_clean.pivot(index="ts", columns="st", values=c) for c in ("dir", "ws", "d1", "a", "sd1")}
idx = P["dir"].index
week_num = (idx - idx[0]) // pd.Timedelta(days=7)
week = week_num % 2
hr = idx.hour
band = np.where((hr >= 10) & (hr <= 17), 0, np.where((hr >= 22) | (hr <= 6), 1, 2))

def calibrated(src, truth, tr_mask):
    """Calibra desfase circular por sector de 22.5° × franja horaria en tr_mask."""
    sec = (((src + 11.25) % 360) // 22.5)
    key = pd.Series(sec.astype("Int64").astype(str) + "_" + band.astype(str), index=idx)
    ok = tr_mask & src.notna() & truth.notna()
    z = np.exp(1j * np.deg2rad(sdiff(truth[ok], src[ok])))
    g = z.groupby(key[ok]).mean()
    off = pd.Series(np.rad2deg(np.angle(g.to_numpy())), index=g.index)
    return (src + key.map(off)) % 360

# ==============================================================================
# 1. AFIRMACIÓN 1
# ==============================================================================
print("=== AFIRMACION 1A: Desglose de error de WindDir_Avg vs D1 (ws > 1 m/s) ===")
rows_c1a = []
for t in TARGETS:
    ok = (P["ws"][t] > 1) & P["d1"][t].notna() & P["a"][t].notna()
    d1 = P["d1"][t][ok]
    a = P["a"][t][ok]
    sd1 = P["sd1"][t][ok]
    err = ang(a, d1)
    d_n = ang(d1, 0)
    n_true = d_n <= 45
    non_n = d_n > 45
    in_45_90 = (d_n > 45) & (d_n <= 90)
    gt_90 = d_n > 90
    e_out = err[non_n]
    out_gt30 = (e_out > 30).sum()
    rows_c1a.append({
        "estacion": t,
        "n_total": int(ok.sum()),
        "%h_norte": round(100 * n_true.mean(), 1),
        "err_todas": round(err.mean(), 1),
        "err_norte(<=45)": round(err[n_true].mean(), 1),
        "err_fuera(>45)_mean": round(e_out.mean(), 1),
        "err_fuera_med": round(e_out.median(), 1),
        "err_45_90": round(err[in_45_90].mean(), 1),
        "err_>90": round(err[gt_90].mean(), 1),
        "fuera_>30_n(%)": f"{out_gt30} ({100*out_gt30/len(e_out):.1f}%)",
        "SD1_en_fuera>30": round(sd1[non_n][e_out > 30].mean(), 1) if out_gt30 > 0 else np.nan,
        "SD1_en_fuera<=30": round(sd1[non_n][e_out <= 30].mean(), 1),
    })
print(pd.DataFrame(rows_c1a).to_string(index=False))

print("\n=== AFIRMACION 1B: En semanas de prueba (te) fuera del norte (|D1|>45°) y regla híbrida ciega ===")
rows_c1b = []
for t in TARGETS:
    truth = P["d1"][t]
    base = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna()
    tr, te = base & (week == 0), base & (week == 1)
    U = pd.Series(0.0, index=idx); W = U.copy(); S_ = U.copy()
    for s in [s for s in P["dir"].columns if s != t]:
        pred = calibrated(P["dir"][s], truth, tr)
        e_tr = ang(pred[tr], truth[tr]).mean()
        if not np.isfinite(e_tr):
            continue
        wgt = 1 / max(e_tr, 5) ** 2
        m = pred.notna()
        U[m] += wgt * np.sin(np.deg2rad(pred[m]))
        W[m] += wgt * np.cos(np.deg2rad(pred[m]))
        S_[m] += wgt
    comb = (np.rad2deg(np.arctan2(U, W)) % 360).where(S_ > 0)
    non_n = te & (ang(truth, 0) > 45)
    eo = ang(P["a"][t], truth)
    ec = ang(comb, truth)
    part_cross = non_n & (eo > 30)
    # Regla ciega (sin ver D1): si consenso apunta cerca del norte (<=55°) y A discrepa fuerte (>55°) y A está lejos del norte (>45°)
    blind_switch = (ang(comb, 0) <= 55) & (ang(P["a"][t], comb) > 55) & (ang(P["a"][t], 0) > 45)
    hyb = P["a"][t].where(~blind_switch, comb)
    eh = ang(hyb, truth)
    det_out = non_n & blind_switch
    rows_c1b.append({
        "estacion": t,
        "n_te_fuera": int(non_n.sum()),
        "err_A_fuera": round(eo[non_n].mean(), 2),
        "err_Pares_fuera": round(ec[non_n].mean(), 2),
        "n_A>30_fuera": int(part_cross.sum()),
        "en_A>30_A_vs_Pares": f"{eo[part_cross].mean():.1f} vs {ec[part_cross].mean():.1f}" if part_cross.sum() else "-",
        "n_ciego_fuera": int(det_out.sum()),
        "en_ciego_A_vs_Pares": f"{eo[det_out].mean():.1f} vs {ec[det_out].mean():.1f}" if det_out.sum() else "-",
        "err_Hibrido_fuera": round(eh[non_n].mean(), 2),
        "err_Hibrido_todas": f"{eo[te].mean():.1f}->{eh[te].mean():.1f}",
    })
print(pd.DataFrame(rows_c1b).to_string(index=False))

# ==============================================================================
# 2. AFIRMACIÓN 2
# ==============================================================================
print("\n=== AFIRMACION 2: Desglose metodológico vs físico del IDW crudo (en semanas impares te) ===")
# También preparar matriz sin --limpio (como consensus_idw.py original: todas en XY menos Dique_pie_botadero)
df_idw_orig = df_raw[df_raw.st.isin(XY) & (df_raw.st != "Dique_pie_botadero")].copy()
df_idw_orig["dir"] = df_idw_orig.d1.fillna(df_idw_orig.a)
P_orig = {c: df_idw_orig.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws")}
u_orig = P_orig["ws"] * np.sin(np.deg2rad(P_orig["dir"]))
w_orig = P_orig["ws"] * np.cos(np.deg2rad(P_orig["dir"]))

u_ws = P["ws"] * np.sin(np.deg2rad(P["dir"]))
w_ws = P["ws"] * np.cos(np.deg2rad(P["dir"]))
u_unit = np.sin(np.deg2rad(P["dir"]))
w_unit = np.cos(np.deg2rad(P["dir"]))

rows_c2 = []
for t in TARGETS:
    truth = P["d1"][t]
    ok = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna() & (week == 1)
    n_mk = ok & (ang(truth, 0) <= 45)
    
    # 0) IDW original (sin --limpio, ws * 1/d^2)
    nb0 = [s for s in P_orig["dir"].columns if s != t]
    d0 = pd.Series({s: np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1])/1000 for s in nb0})
    p0 = 1 / d0**2
    U0 = (u_orig[nb0].fillna(0)*p0).sum(1); W0 = (w_orig[nb0].fillna(0)*p0).sum(1)
    c0 = pd.Series(np.rad2deg(np.arctan2(U0, W0)) % 360, index=idx)

    nb_all = [s for s in P["dir"].columns if s != t]
    nb_d1 = [s for s in TARGETS if s != t and s in P["dir"].columns]
    d_km = pd.Series({s: np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1])/1000 for s in nb_all})
    dz_km = pd.Series({s: abs(Z[t]-Z[s])/1000 for s in nb_all})
    p1 = 1 / d_km**2

    # 1) IDW --limpio ws * 1/d^2
    U1 = (u_ws[nb_all].fillna(0)*p1).sum(1); W1 = (w_ws[nb_all].fillna(0)*p1).sum(1)
    c1 = pd.Series(np.rad2deg(np.arctan2(U1, W1)) % 360, index=idx)

    # 2) IDW --limpio unitario * 1/d^2
    U2 = (u_unit[nb_all].fillna(0)*p1).sum(1); W2 = (w_unit[nb_all].fillna(0)*p1).sum(1)
    c2 = pd.Series(np.rad2deg(np.arctan2(U2, W2)) % 360, index=idx)

    # 3) IDW --limpio unitario * 1/d^2 SOLO vecinas con D1 (sin vecinas WindDir_Avg que meten ~180° en norte)
    p3 = 1 / d_km[nb_d1]**2
    U3 = (u_unit[nb_d1].fillna(0)*p3).sum(1); W3 = (w_unit[nb_d1].fillna(0)*p3).sum(1)
    c3 = pd.Series(np.rad2deg(np.arctan2(U3, W3)) % 360, index=idx)

    # 4) IDW --limpio unitario * 1/d_3D^2 (solo D1)
    p4 = 1 / (d_km[nb_d1]**2 + (8.0 * dz_km[nb_d1])**2)
    U4 = (u_unit[nb_d1].fillna(0)*p4).sum(1); W4 = (w_unit[nb_d1].fillna(0)*p4).sum(1)
    c4 = pd.Series(np.rad2deg(np.arctan2(U4, W4)) % 360, index=idx)

    # Sesgo medio circular día vs noche entre c3 y truth
    day_mk = ok & (band == 0)
    night_mk = ok & (band == 1)
    bias_day = np.rad2deg(np.angle(np.exp(1j * np.deg2rad(sdiff(truth[day_mk], c1[day_mk]))).mean()))
    bias_night = np.rad2deg(np.angle(np.exp(1j * np.deg2rad(sdiff(truth[night_mk], c1[night_mk]))).mean()))

    rows_c2.append({
        "estacion": t,
        "IDW_bruto(idw.py)": f"{ang(c0[ok], truth[ok]).mean():.1f} / {ang(c0[n_mk], truth[n_mk]).mean():.1f}",
        "IDW_limpio_ws": f"{ang(c1[ok], truth[ok]).mean():.1f} / {ang(c1[n_mk], truth[n_mk]).mean():.1f}",
        "IDW_limpio_unit": f"{ang(c2[ok], truth[ok]).mean():.1f} / {ang(c2[n_mk], truth[n_mk]).mean():.1f}",
        "IDW_unit_soloD1": f"{ang(c3[ok], truth[ok]).mean():.1f} / {ang(c3[n_mk], truth[n_mk]).mean():.1f}",
        "IDW_3D_soloD1": f"{ang(c4[ok], truth[ok]).mean():.1f} / {ang(c4[n_mk], truth[n_mk]).mean():.1f}",
        "desfase_dia/noche": f"{bias_day:+.0f}° / {bias_night:+.0f}°",
    })
print(pd.DataFrame(rows_c2).to_string(index=False))

# ==============================================================================
# 3. AFIRMACIÓN 3
# ==============================================================================
print("\n=== AFIRMACION 3: Comparación Calib_IDW vs Pares (D1 oráculo vs entrenado con Avg vs Climatología) ===")
rows_c3 = []
for t in TARGETS:
    truth = P["d1"][t]
    avg_own = P["a"][t]
    base = (P["ws"][t] > 1) & truth.notna() & avg_own.notna()
    tr, te = base & (week == 0), base & (week == 1)
    n_te = te & (ang(truth, 0) <= 45)

    # Climatología horaria pura (0 vecinas, entrenada con D1)
    z_clim = np.exp(1j * np.deg2rad(truth[tr])).groupby(hr[tr]).mean()
    clim_hr = pd.Series(np.rad2deg(np.angle(z_clim.to_numpy())) % 360, index=z_clim.index)
    pred_clim = pd.Series(hr, index=idx).map(clim_hr)

    # Consenso IDW crudo (--limpio) y su calibración (consensus_calibrated.py --limpio)
    nb = [s for s in P["dir"].columns if s != t]
    p = pd.Series({s: 1 / (np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1])/1000)**2 for s in nb})
    m = u_ws[nb].notna()
    U = (u_ws[nb].fillna(0)*p).sum(1)/(m*p).sum(1); W = (w_ws[nb].fillna(0)*p).sum(1)/(m*p).sum(1)
    c = pd.Series(np.rad2deg(np.arctan2(U, W)) % 360, index=idx)
    cal_idw = calibrated(c, truth, tr)

    # Pares entrenado con D1 (oráculo)
    U_p1 = pd.Series(0.0, index=idx); W_p1 = U_p1.copy()
    # Pares entrenado con WindDir_Avg propio (todas las horas tr)
    U_pa = pd.Series(0.0, index=idx); W_pa = U_pa.copy()
    # Pares entrenado con WindDir_Avg propio filtrado (R4: excluyendo |A|<=45° donde A podría estar sesgado o SD1>25)
    tr_clean_a = tr & (ang(avg_own, 0) > 45)
    U_pac = pd.Series(0.0, index=idx); W_pac = U_pac.copy()

    for s in nb:
        # 1) D1
        pred_s = calibrated(P["dir"][s], truth, tr)
        e_tr = ang(pred_s[tr], truth[tr]).mean()
        if np.isfinite(e_tr):
            wgt = 1 / max(e_tr, 5)**2
            mk = pred_s.notna()
            U_p1[mk] += wgt * np.sin(np.deg2rad(pred_s[mk]))
            W_p1[mk] += wgt * np.cos(np.deg2rad(pred_s[mk]))
        # 2) Avg todas
        pred_sa = calibrated(P["dir"][s], avg_own, tr)
        e_tra = ang(pred_sa[tr], avg_own[tr]).mean()
        if np.isfinite(e_tra):
            wgta = 1 / max(e_tra, 5)**2
            mk = pred_sa.notna()
            U_pa[mk] += wgta * np.sin(np.deg2rad(pred_sa[mk]))
            W_pa[mk] += wgta * np.cos(np.deg2rad(pred_sa[mk]))
        # 3) Avg solo fuera del norte (|A|>45°)
        pred_sac = calibrated(P["dir"][s], avg_own, tr_clean_a)
        e_trac = ang(pred_sac[tr_clean_a], avg_own[tr_clean_a]).mean()
        if np.isfinite(e_trac):
            wgtac = 1 / max(e_trac, 5)**2
            mk = pred_sac.notna()
            U_pac[mk] += wgtac * np.sin(np.deg2rad(pred_sac[mk]))
            W_pac[mk] += wgtac * np.cos(np.deg2rad(pred_sac[mk]))

    comb_d1 = np.rad2deg(np.arctan2(U_p1, W_p1)) % 360
    comb_avg = np.rad2deg(np.arctan2(U_pa, W_pa)) % 360
    comb_avg_clean = np.rad2deg(np.arctan2(U_pac, W_pac)) % 360

    f = lambda pr: f"{ang(pr[te], truth[te]).mean():.1f} / {ang(pr[n_te], truth[n_te]).mean():.1f}"
    rows_c3.append({
        "estacion": t,
        "Propio_A": f(avg_own),
        "Climatologia_0vec": f(pred_clim),
        "Calib_IDW(D1)": f(cal_idw),
        "Pares(D1_oraculo)": f(comb_d1),
        "Pares(ent_Avg_todas)": f(comb_avg),
        "Pares(ent_Avg_|A|>45)": f(comb_avg_clean),
    })
print(pd.DataFrame(rows_c3).to_string(index=False))

# ==============================================================================
# 4. AFIRMACIÓN 4
# ==============================================================================
print("\n=== AFIRMACION 4: Vecina más cercana vs mejores vecinas reales en prueba (te) ===")
rows_c4 = []
for t in TARGETS:
    truth = P["d1"][t]
    base = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna()
    tr, te = base & (week == 0), base & (week == 1)
    n_te = te & (ang(truth, 0) <= 45)
    nb = [s for s in P["dir"].columns if s != t]
    res_nb = []
    for s in nb:
        d_km = np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1]) / 1000
        dz = abs(Z[t] - Z[s])
        pred = calibrated(P["dir"][s], truth, tr)
        e_tr = ang(pred[tr], truth[tr]).mean()
        e_te = ang(pred[te], truth[te]).mean()
        e_raw_te = ang(P["dir"][s][te], truth[te]).mean()
        e_n_te = ang(pred[n_te], truth[n_te]).mean()
        n_obs_te = int(pred[te].notna().sum())
        res_nb.append({
            "vecina": s, "km": round(d_km, 2), "dz": int(dz),
            "tiene_D1": s in TARGETS, "n_te": n_obs_te,
            "raw_te": round(e_raw_te, 1), "cal_tr": round(e_tr, 1),
            "cal_te": round(e_te, 1), "cal_n_te": round(e_n_te, 1)
        })
    df_nb = pd.DataFrame(res_nb)
    df_full = df_nb[df_nb.n_te >= 500].copy()
    df_full["rank_te"] = df_full["cal_te"].rank().astype(int)
    df_full["rank_n_te"] = df_full["cal_n_te"].rank().astype(int)
    nearest = df_full.sort_values("km").iloc[0]
    best_te = df_full.sort_values("cal_te").iloc[:3]
    best_n = df_full.sort_values("cal_n_te").iloc[:3]
    rows_c4.append({
        "estacion": t,
        "mas_cercana": f"{nearest.vecina} ({nearest.km}km, dz={nearest.dz}m, D1={nearest.tiene_D1})",
        "err_cercana(tot/N/rank)": f"{nearest.cal_te}° / {nearest.cal_n_te}° (#{nearest.rank_te}/#{nearest.rank_n_te})",
        "top3_prueba_total": ", ".join(f"{r.vecina}({r.km}km:{r.cal_te}°)" for _, r in best_te.iterrows()),
        "top3_prueba_norte": ", ".join(f"{r.vecina}({r.km}km:{r.cal_n_te}°)" for _, r in best_n.iterrows()),
    })
print(pd.DataFrame(rows_c4).to_string(index=False))

# Detalle completo de Cortadera para Afirmación 4
print("\n--- Detalle de vecinas de Cortadera (ordenadas por cal_te, n_te >= 500) ---")
truth_c = P["d1"]["Cortadera"]
base_c = (P["ws"]["Cortadera"] > 1) & truth_c.notna() & P["a"]["Cortadera"].notna()
tr_c, te_c = base_c & (week == 0), base_c & (week == 1)
n_te_c = te_c & (ang(truth_c, 0) <= 45)
det_cort = []
for s in [s for s in P["dir"].columns if s != "Cortadera"]:
    d_km = np.hypot(XY["Cortadera"][0]-XY[s][0], XY["Cortadera"][1]-XY[s][1]) / 1000
    pred = calibrated(P["dir"][s], truth_c, tr_c)
    det_cort.append({
        "vecina": s, "km": round(d_km, 2), "dz_m": int(Z[s] - Z["Cortadera"]),
        "D1": "Sí" if s in TARGETS else "No(Avg)",
        "n_te": int(pred[te_c].notna().sum()),
        "raw_te": round(ang(P["dir"][s][te_c], truth_c[te_c]).mean(), 1),
        "cal_tr": round(ang(pred[tr_c], truth_c[tr_c]).mean(), 1),
        "cal_te": round(ang(pred[te_c], truth_c[te_c]).mean(), 1),
        "cal_norte_te": round(ang(pred[n_te_c], truth_c[n_te_c]).mean(), 1),
    })
print(pd.DataFrame(det_cort).sort_values("cal_te").to_string(index=False))

# ==============================================================================
# 5. AFIRMACIÓN 5
# ==============================================================================
print("\n=== AFIRMACION 5: Impacto de estaciones defectuosas sobre las MISMAS horas limpias de prueba ===")
# Escenario A: Todas las estaciones en XY (incluyendo Dique_pie_botadero, Planta_Concentradora, Chalsos, Sarallenque todo el año, etc.)
df_A = df_raw[df_raw.st.isin(XY)].copy()
df_A["dir"] = df_A.d1.fillna(df_A.a)
P_A = {c: df_A.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws")}

# Escenario B: Como calib.py sin --limpio (excluye solo Dique_pie_botadero)
df_B = df_raw[df_raw.st.isin(XY) & (df_raw.st != "Dique_pie_botadero")].copy()
df_B["dir"] = df_B.d1.fillna(df_B.a)
P_B = {c: df_B.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws")}

# Escenario C: --limpio pero SIN excluir Planta_Concentradora (0.58 km de Papujune)
df_C = df_raw.copy()
drop_C = {"Dique_pie_botadero", "Chalsos", "Mina_Norte", "Ilo", "Huachunta", "Vizcachas", "Titire"}
df_C = df_C[df_C.st.isin(XY) & ~df_C.st.isin(drop_C)]
df_C = df_C[~((df_C.st == "Sarallenque") & (df_C.ts < "2026-09-25 21:00"))]
df_C = df_C[df_C.ws >= 0.5]
for st, a, b in [
    ("Alto_Quellaveco", "2026-09-15 11:00", "2099"),
    ("Cortadera", "2026-09-13 11:00", "2099"),
    ("Alto_Tala", "2026-08-18 05:00", "2026-09-23 15:00"),
]:
    df_C = df_C[~((df_C.st == st) & (df_C.ts >= a) & (df_C.ts <= b))]
df_C["dir"] = df_C.d1.fillna(df_C.a)
P_C = {c: df_C.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws")}

# Escenario E: --limpio pero dejando los tramos girados de sept 2026 en vecinas (Cortadera, Alto_Quellaveco, Alto_Tala, Sarallenque completo)
df_E = df_raw.copy()
drop_E = {"Dique_pie_botadero", "Chalsos", "Mina_Norte", "Planta_Concentradora", "Ilo", "Huachunta", "Vizcachas", "Titire"}
df_E = df_E[df_E.st.isin(XY) & ~df_E.st.isin(drop_E)]
df_E = df_E[df_E.ws >= 0.5]
df_E["dir"] = df_E.d1.fillna(df_E.a)
P_E = {c: df_E.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws")}

def eval_idw_and_pairs(P_scen, t, tr, te, n_te):
    u_s = P_scen["ws"] * np.sin(np.deg2rad(P_scen["dir"]))
    w_s = P_scen["ws"] * np.cos(np.deg2rad(P_scen["dir"]))
    nb = [s for s in P_scen["dir"].columns if s != t]
    p = pd.Series({s: 1 / (np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1])/1000)**2 for s in nb})
    m = u_s[nb].notna()
    U = (u_s[nb].fillna(0)*p).sum(1)/(m*p).sum(1); W = (w_s[nb].fillna(0)*p).sum(1)/(m*p).sum(1)
    c = pd.Series(np.rad2deg(np.arctan2(U, W)) % 360, index=idx)
    truth = P["d1"][t]
    cal = calibrated(c, truth, tr)
    # También evaluar en tramo post 2026-09-15
    te_post = te & (idx >= "2026-09-15")
    return (
        f"{ang(c[te], truth[te]).mean():.1f}->{ang(cal[te], truth[te]).mean():.1f}/{ang(cal[n_te], truth[n_te]).mean():.1f}",
        f"{ang(cal[te_post], truth[te_post]).mean():.1f}" if te_post.sum() > 10 else "-"
    )

rows_c5 = []
rows_c5_post = []
for t in TARGETS:
    truth = P["d1"][t]
    base = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna()
    tr, te = base & (week == 0), base & (week == 1)
    n_te = te & (ang(truth, 0) <= 45)
    a_all, a_post = eval_idw_and_pairs(P_A, t, tr, te, n_te)
    b_all, b_post = eval_idw_and_pairs(P_B, t, tr, te, n_te)
    c_all, c_post = eval_idw_and_pairs(P_C, t, tr, te, n_te)
    e_all, e_post = eval_idw_and_pairs(P_E, t, tr, te, n_te)
    d_all, d_post = eval_idw_and_pairs(P, t, tr, te, n_te)
    rows_c5.append({
        "estacion": t,
        "A_Con_Dique": a_all,
        "B_Sin_Dique(no_limpio)": b_all,
        "C_Limpio+Planta": c_all,
        "E_Limpio+GirosSept": e_all,
        "D_Limpio_Total": d_all,
    })
    rows_c5_post.append({
        "estacion": t,
        "A_post0915": a_post,
        "B_post0915": b_post,
        "C_post0915": c_post,
        "E_post0915(con_giros)": e_post,
        "D_post0915(limpio)": d_post,
    })
print("Formato: Crudo->Cal_Total/Cal_Norte (toda la prueba):")
print(pd.DataFrame(rows_c5).to_string(index=False))
print("\nError Cal_Total solo desde 2026-09-15 (cuando ocurren los giros de Cortadera/Alto_Q/Sarallenque):")
print(pd.DataFrame(rows_c5_post).to_string(index=False))

# Mostrar también las 3 vecinas más cercanas a cada estación en P_A (para ver qué mandan con 1/d^2)
print("\n--- Vecinas más cercanas en red bruta (P_A) y su peso relativo 1/d^2 ---")
for t in TARGETS:
    nb = [s for s in P_A["dir"].columns if s != t]
    d = pd.Series({s: np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1])/1000 for s in nb}).sort_values()
    w = (1 / d**2) / (1 / d**2).sum() * 100
    top3 = ", ".join(f"{s} ({d[s]:.2f}km, {w[s]:.1f}%)" for s in d.index[:4])
    print(f"  {t:16s}: {top3}")

# ==============================================================================
# 6. CORRECCIÓN DE PESOS EN CONSENSUS_PAIRS.PY + MÉTODO MEJORADO
# ==============================================================================
print("\n======================================================================")
print("CORRECCION DE PESOS (VALIDACION INTERNA) Y METODO MEJORADO")
print("======================================================================")

rows_weights_summary = []
weight_shifts_detail = []

for t in TARGETS:
    truth = P["d1"][t]
    base = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna()
    tr, te = base & (week == 0), base & (week == 1)
    n_te = te & (ang(truth, 0) <= 45)
    # Partición interna de las semanas pares (week == 0):
    # tr_sub: semanas múltiplo de 4 (0, 4, 8, ...); val_sub: semanas pares restantes (2, 6, 10, ...)
    tr_sub = base & (week_num % 4 == 0)
    val_sub = base & (week_num % 4 == 2)

    nbs = [s for s in P["dir"].columns if s != t]

    # M0: Original consensus_pairs.py (peso in-sample sobre tr)
    U0 = pd.Series(0.0, index=idx); W0 = U0.copy()
    # M1a: Calibrar en tr_sub, medir peso en val_sub, predecir te con tabla de tr_sub
    U1a = pd.Series(0.0, index=idx); W1a = U1a.copy()
    # M1b: Calibrar en tr_sub, medir peso en val_sub, reajustar tabla en todo tr para predecir te
    U1b = pd.Series(0.0, index=idx); W1b = U1b.copy()
    # M1c: 2-fold CV interna sobre tr (tr_sub <-> val_sub) + penalización por cobertura (n_val / n_tr_total)
    U1c = pd.Series(0.0, index=idx); W1c = U1c.copy()
    # M2: Método mejorado propuesto:
    #     - Desfase con fallback jerárquico (celda sector×franja si n>=5, si no sector global)
    #     - Ponderación por celda y vecina usando concentración circular R_celda^2 * (n/(n+8))^2 * (cobertura / e_cv^4)
    #       restringido a las Top-5 vecinas por validación interna CV
    U2 = pd.Series(0.0, index=idx); W2 = U2.copy()

    w0_dict, w1b_dict, w1c_dict = {}, {}, {}
    e_tr_dict, e_val_dict, e_cv_dict, cov_dict = {}, {}, {}, {}
    m2_candidates = []

    n_tr_tot = int(tr.sum())
    n_val_tot = int(val_sub.sum())

    for s in nbs:
        src_s = P["dir"][s]
        # --- M0 ---
        pred_tr = calibrated(src_s, truth, tr)
        e_tr = ang(pred_tr[tr], truth[tr]).mean()
        w0 = (1 / max(e_tr, 5) ** 2) if np.isfinite(e_tr) else 0.0
        w0_dict[s] = w0
        e_tr_dict[s] = e_tr
        mk = pred_tr.notna()
        U0[mk] += w0 * np.sin(np.deg2rad(pred_tr[mk]))
        W0[mk] += w0 * np.cos(np.deg2rad(pred_tr[mk]))

        # --- M1a & M1b (split tr_sub -> val_sub) ---
        pred_sub = calibrated(src_s, truth, tr_sub)
        e_val = ang(pred_sub[val_sub], truth[val_sub]).mean()
        n_val_s = int(pred_sub[val_sub].notna().sum())
        w1 = (1 / max(e_val, 5) ** 2) if (np.isfinite(e_val) and n_val_s >= 10) else 0.0
        w1b_dict[s] = w1
        e_val_dict[s] = e_val

        mk_sub = pred_sub.notna()
        U1a[mk_sub] += w1 * np.sin(np.deg2rad(pred_sub[mk_sub]))
        W1a[mk_sub] += w1 * np.cos(np.deg2rad(pred_sub[mk_sub]))

        U1b[mk] += w1 * np.sin(np.deg2rad(pred_tr[mk]))
        W1b[mk] += w1 * np.cos(np.deg2rad(pred_tr[mk]))

        # --- M1c (2-fold CV interna sobre tr + factor de cobertura real en validación) ---
        pred_sub2 = calibrated(src_s, truth, val_sub)
        oof = pd.Series(np.nan, index=idx)
        oof[val_sub] = pred_sub[val_sub]
        oof[tr_sub] = pred_sub2[tr_sub]
        e_cv = ang(oof[tr], truth[tr]).mean()
        n_cv_s = int(oof[tr].notna().sum())
        cov = n_cv_s / max(n_tr_tot, 1)
        # Error efectivo: penaliza celdas/horas donde no pudo predecir o tiene poca muestra (shrinkage bayesiano a 45°)
        e_cv_shrunk = (n_cv_s * e_cv + 50.0 * 45.0) / (n_cv_s + 50.0) if np.isfinite(e_cv) else 90.0
        w1c = cov / max(e_cv_shrunk, 5) ** 2 if np.isfinite(e_cv) else 0.0
        w1c_dict[s] = w1c
        e_cv_dict[s] = e_cv
        cov_dict[s] = cov

        U1c[mk] += w1c * np.sin(np.deg2rad(pred_tr[mk]))
        W1c[mk] += w1c * np.cos(np.deg2rad(pred_tr[mk]))

        # Guardar datos para M2
        m2_candidates.append((s, e_cv_shrunk, cov, e_cv))

    # --- M2_Top5: Top-5 vecinas por CV shrunk + R_celda^3 + fallback ---
    # --- M2a: Todas las vecinas ponderadas por concentracion circular de celda R_celda^3 * w_cv ---
    # --- M2b: Igual que M2a pero usando error CV especifico por regimen ---
    U2_top5 = pd.Series(0.0, index=idx); W2_top5 = U2_top5.copy()
    U2a = pd.Series(0.0, index=idx); W2a = U2a.copy()
    U2b = pd.Series(0.0, index=idx); W2b = U2b.copy()

    top5_s = {x[0] for x in sorted(m2_candidates, key=lambda x: x[1])[:5]}
    c1c_prelim = np.rad2deg(np.arctan2(U1c, W1c)) % 360
    is_north_est_tr = tr & (ang(c1c_prelim, 0) <= 55)
    is_north_est_all = ang(c1c_prelim, 0) <= 55

    for s, e_cv_sh, cov, e_cv in m2_candidates:
        src_s = P["dir"][s]
        sec = (((src_s + 11.25) % 360) // 22.5)
        key_sb = pd.Series(sec.astype("Int64").astype(str) + "_" + band.astype(str), index=idx)
        key_s = pd.Series(sec.astype("Int64").astype(str), index=idx)
        ok_s = tr & src_s.notna() & truth.notna()
        z = np.exp(1j * np.deg2rad(sdiff(truth[ok_s], src_s[ok_s])))

        grp_sb = z.groupby(key_sb[ok_s])
        g_mean_sb = grp_sb.mean()
        g_cnt_sb = grp_sb.count()
        off_sb = pd.Series(np.rad2deg(np.angle(g_mean_sb.to_numpy())), index=g_mean_sb.index)
        r_sb = pd.Series(np.abs(g_mean_sb.to_numpy()) * (g_cnt_sb / (g_cnt_sb + 10.0)), index=g_mean_sb.index)

        if s in top5_s:
            r_sb_8 = pd.Series(np.abs(g_mean_sb.to_numpy()) * (g_cnt_sb / (g_cnt_sb + 8.0)), index=g_mean_sb.index)
            grp_s = z.groupby(key_s[ok_s])
            g_mean_s = grp_s.mean()
            g_cnt_s = grp_s.count()
            off_s = pd.Series(np.rad2deg(np.angle(g_mean_s.to_numpy())), index=g_mean_s.index)
            r_s = pd.Series(np.abs(g_mean_s.to_numpy()) * (g_cnt_s / (g_cnt_s + 8.0)) * 0.7, index=g_mean_s.index)
            mapped_cnt = key_sb.map(g_cnt_sb).fillna(0)
            mapped_off_t5 = key_sb.map(off_sb).where(mapped_cnt >= 5, key_s.map(off_s))
            mapped_r_t5 = key_sb.map(r_sb_8).where(mapped_cnt >= 5, key_s.map(r_s)).fillna(0)
            pred_t5 = (src_s + mapped_off_t5) % 360
            w_t5 = (cov / (max(e_cv_sh, 8.0) ** 3)) * (mapped_r_t5 ** 3)
            mkt5 = pred_t5.notna() & (w_t5 > 0)
            U2_top5[mkt5] += w_t5[mkt5] * np.sin(np.deg2rad(pred_t5[mkt5]))
            W2_top5[mkt5] += w_t5[mkt5] * np.cos(np.deg2rad(pred_t5[mkt5]))

        pred_m2 = (src_s + key_sb.map(off_sb)) % 360
        mapped_r = key_sb.map(r_sb).fillna(0)

        # Peso global CV shrunk (M2a)
        w_base_a = cov / (max(e_cv_sh, 10.0) ** 2)
        w_ta = w_base_a * (mapped_r ** 3)
        mk2 = pred_m2.notna() & (w_ta > 0)
        U2a[mk2] += w_ta[mk2] * np.sin(np.deg2rad(pred_m2[mk2]))
        W2a[mk2] += w_ta[mk2] * np.cos(np.deg2rad(pred_m2[mk2]))

        # Peso CV desglosado por régimen estimado norte / fuera-norte (M2b, 100% out-of-fold en tr)
        pred_sub1 = calibrated(src_s, truth, tr_sub)
        pred_sub2 = calibrated(src_s, truth, val_sub)
        oof = pd.Series(np.nan, index=idx)
        oof[val_sub] = pred_sub1[val_sub]
        oof[tr_sub] = pred_sub2[tr_sub]

        mk_n_tr = is_north_est_tr & oof.notna()
        mk_o_tr = tr & (~is_north_est_all) & oof.notna()
        e_cv_n = ang(oof[mk_n_tr], truth[mk_n_tr]).mean() if mk_n_tr.sum() >= 5 else 60.0
        e_cv_o = ang(oof[mk_o_tr], truth[mk_o_tr]).mean() if mk_o_tr.sum() >= 10 else 45.0
        e_cv_n_sh = (mk_n_tr.sum() * e_cv_n + 15.0 * 50.0) / (mk_n_tr.sum() + 15.0)
        e_cv_o_sh = (mk_o_tr.sum() * e_cv_o + 30.0 * 40.0) / (mk_o_tr.sum() + 30.0)

        w_n = cov / (max(e_cv_n_sh, 10.0) ** 3)
        w_o = cov / (max(e_cv_o_sh, 10.0) ** 2)
        w_reg = pd.Series(np.where(is_north_est_all, w_n, w_o), index=idx)
        w_tb = w_reg * (mapped_r ** 3)
        mk2b = pred_m2.notna() & (w_tb > 0)
        U2b[mk2b] += w_tb[mk2b] * np.sin(np.deg2rad(pred_m2[mk2b]))
        W2b[mk2b] += w_tb[mk2b] * np.cos(np.deg2rad(pred_m2[mk2b]))

    c0 = np.rad2deg(np.arctan2(U0, W0)) % 360
    c1a = np.rad2deg(np.arctan2(U1a, W1a)) % 360
    c1b = np.rad2deg(np.arctan2(U1b, W1b)) % 360
    c1c = np.rad2deg(np.arctan2(U1c, W1c)) % 360
    c2_t5 = np.rad2deg(np.arctan2(U2_top5, W2_top5)) % 360
    c2a = np.rad2deg(np.arctan2(U2a, W2a)) % 360
    c2b = np.rad2deg(np.arctan2(U2b, W2b)) % 360

    f = lambda pr: f"{ang(pr[te], truth[te]).mean():.1f} / {ang(pr[n_te], truth[n_te]).mean():.1f}"
    rows_weights_summary.append({
        "estacion": t,
        "M0_Original(in-sample)": f(c0),
        "M1a_Val_Split(tabla_sub)": f(c1a),
        "M1b_Val_Split(tabla_tr)": f(c1b),
        "M1c_Val_2Fold+Cob": f(c1c),
        "M2_Top5_Rcelda_CV": f(c2_t5),
        "M2b_Rcelda_CV_Regimen": f(c2b),
    })

    # Analizar cambio de pesos normalizados (% del peso total)
    s0 = sum(w0_dict.values()) or 1.0
    s1b = sum(w1b_dict.values()) or 1.0
    s1c = sum(w1c_dict.values()) or 1.0
    for s in nbs:
        p0 = 100 * w0_dict[s] / s0
        p1b = 100 * w1b_dict[s] / s1b
        p1c = 100 * w1c_dict[s] / s1c
        weight_shifts_detail.append({
            "target": t, "vecina": s,
            "e_tr": round(e_tr_dict[s], 1),
            "e_val_split": round(e_val_dict[s], 1) if np.isfinite(e_val_dict[s]) else np.nan,
            "e_cv_2fold": round(e_cv_dict[s], 1) if np.isfinite(e_cv_dict[s]) else np.nan,
            "cob_%": round(100 * cov_dict[s], 1),
            "w_orig_%": round(p0, 2),
            "w_split_%": round(p1b, 2),
            "w_cv_cob_%": round(p1c, 2),
            "diff_split_%": round(p1b - p0, 2),
            "diff_cv_cob_%": round(p1c - p0, 2),
        })

print("\n--- Tabla comparativa de error en prueba (todas / norte, grados) ---")
print(pd.DataFrame(rows_weights_summary).to_string(index=False))

df_ws = pd.DataFrame(weight_shifts_detail)
print("\n--- Mayores caídas y subidas de peso por estación (M0 in-sample vs M1b Split y M1c CV+Cob) ---")
for t in TARGETS:
    sub = df_ws[df_ws.target == t].copy()
    top_orig = sub.sort_values("w_orig_%", ascending=False).iloc[:3]
    top_split = sub.sort_values("w_split_%", ascending=False).iloc[:3]
    top_cv = sub.sort_values("w_cv_cob_%", ascending=False).iloc[:3]
    biggest_drop_split = sub.sort_values("diff_split_%").iloc[0]
    biggest_gain_split = sub.sort_values("diff_split_%", ascending=False).iloc[0]
    biggest_drop_cv = sub.sort_values("diff_cv_cob_%").iloc[0]
    biggest_gain_cv = sub.sort_values("diff_cv_cob_%", ascending=False).iloc[0]
    print(f"\n[{t}]")
    print("  Top 3 Original (M0):   " + ", ".join(f"{r.vecina} ({r['w_orig_%']:.1f}%, e_tr={r.e_tr}°)" for _, r in top_orig.iterrows()))
    print("  Top 3 Val Split (M1b): " + ", ".join(f"{r.vecina} ({r['w_split_%']:.1f}%, e_val={r.e_val_split}°)" for _, r in top_split.iterrows()))
    print("  Top 3 CV+Cob (M1c):    " + ", ".join(f"{r.vecina} ({r['w_cv_cob_%']:.1f}%, e_cv={r.e_cv_2fold}°, cob={r['cob_%']:.0f}%)" for _, r in top_cv.iterrows()))
    print(f"  Split (M1b-M0) -> Pierde más: {biggest_drop_split.vecina} ({biggest_drop_split['diff_split_%']:+.1f} pp, e_tr={biggest_drop_split.e_tr}°->e_val={biggest_drop_split.e_val_split}°) | Gana más: {biggest_gain_split.vecina} ({biggest_gain_split['diff_split_%']:+.1f} pp)")
    print(f"  CV+Cob(M1c-M0) -> Pierde más: {biggest_drop_cv.vecina} ({biggest_drop_cv['diff_cv_cob_%']:+.1f} pp, cob={biggest_drop_cv['cob_%']:.0f}%) | Gana más: {biggest_gain_cv.vecina} ({biggest_gain_cv['diff_cv_cob_%']:+.1f} pp)")
