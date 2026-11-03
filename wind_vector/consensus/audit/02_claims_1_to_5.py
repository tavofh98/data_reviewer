"""Auditoría cuantitativa de las Afirmaciones 1 a 5."""
import warnings
warnings.filterwarnings("ignore")
import re
import duckdb
import numpy as np
import pandas as pd

DB = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db"
ST_FILE = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc/met_viewer/stations.py"

src = open(ST_FILE, encoding="utf-8").read()
XY = {}
Z = {}
for m in re.finditer(r'"([^"]+)":\s+Station\((\d+),\s*(\d+),\s*(\d+)', src):
    XY[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    Z[m.group(1)] = float(m.group(4))

con = duckdb.connect(DB, read_only=True)
df_raw = con.execute("""
    SELECT estacion_id st, timestamp ts, WindDir_D1_WVT d1, WindDir_Avg a,
           WindDir_SD1_WVT sd1, WS_ms_Avg ws
    FROM meteorologia
    WHERE timestamp >= '2025-11-01' AND WindDir_Avg IS NOT NULL
""").df()
con.close()

ang = lambda a, b: np.minimum(np.abs((a - b) % 360), 360 - np.abs((a - b) % 360))
sdiff = lambda a, b: (a - b + 180) % 360 - 180

TARGETS = ["Altarani", "Alto_Quellaveco", "Camp_Quellaveco", "Cortadera",
           "Minas_Sur", "Papujune", "Tala-1", "Tala_Legal"]

def apply_clean(df, exclude_dique_in_raw=True):
    df = df.copy()
    drop = {"Dique_pie_botadero", "Chalsos", "Mina_Norte", "Planta_Concentradora",
            "Ilo", "Huachunta", "Vizcachas", "Titire"}
    df = df[df.st.isin(XY) & ~df.st.isin(drop)]
    df = df[~((df.st == "Sarallenque") & (df.ts < "2026-09-25 21:00"))]
    df = df[df.ws >= 0.5]
    for st, a, b in [("Alto_Quellaveco", "2026-09-15 11:00", "2099"),
                     ("Cortadera", "2026-09-13 11:00", "2099"),
                     ("Alto_Tala", "2026-08-18 05:00", "2026-09-23 15:00"),
                     ("Charaque", "2026-01-14 14:00", "2026-01-15 12:00"),
                     ("Charaque", "2026-01-28 14:00", "2026-01-29 07:00"),
                     ("Sarallenque_MQG-15-02", "2026-02-16 14:00", "2026-02-17 09:00")]:
        df = df[~((df.st == st) & (df.ts >= a) & (df.ts <= b))]
    return df

df_clean = apply_clean(df_raw)
df_clean["dir"] = df_clean.d1.fillna(df_clean.a)
P = {c: df_clean.pivot(index="ts", columns="st", values=c) for c in ("dir", "ws", "d1", "a", "sd1")}
idx = P["dir"].index
week = ((idx - idx[0]) // pd.Timedelta(days=7)) % 2
hr = idx.hour
band = np.where((hr >= 10) & (hr <= 17), 0, np.where((hr >= 22) | (hr <= 6), 1, 2))

# ==============================================================================
# AFIRMACION 1: Error de WindDir_Avg fuera del sector norte (|D1| > 45°)
# ==============================================================================
print("======================================================================")
print("AFIRMACION 1: WindDir_Avg vs D1 fuera del sector norte (|D1| > 45°)")
print("======================================================================")
rows_c1 = []
for t in TARGETS:
    ok = (P["ws"][t] > 1) & P["d1"][t].notna() & P["a"][t].notna()
    d1 = P["d1"][t][ok]
    a = P["a"][t][ok]
    sd1 = P["sd1"][t][ok]
    err = ang(a, d1)
    n_true = ang(d1, 0) <= 45
    non_n = ~n_true
    e_out = err[non_n]
    e_in = err[n_true]
    # ¿Qué pasa si miramos dónde cae WindDir_Avg cuando D1 está en el norte?
    a_in_north_when_d1_north = (ang(a[n_true], 0) <= 45).mean() * 100
    # Horas fuera de [-45, 45] donde err > 30°
    out_gt30 = (e_out > 30).sum()
    out_gt45 = (e_out > 45).sum()
    # Relación con distancia al norte (45-90 vs >90) y con SD1
    in_45_90 = (ang(d1, 0) > 45) & (ang(d1, 0) <= 90)
    gt_90 = ang(d1, 0) > 90
    rows_c1.append({
        "estacion": t,
        "err_todas": round(err.mean(), 1),
        "err_norte(|D1|<=45)": round(e_in.mean(), 1),
        "err_fuera(|D1|>45)_mean": round(e_out.mean(), 1),
        "err_fuera_mediana": round(e_out.median(), 1),
        "err_fuera_p90": round(e_out.quantile(0.90), 1),
        "err_45_90_mean": round(err[in_45_90].mean(), 1),
        "err_>90_mean": round(err[gt_90].mean(), 1),
        "n_fuera_>30deg": f"{out_gt30} ({100*out_gt30/len(e_out):.1f}%)",
        "n_fuera_>45deg": f"{out_gt45} ({100*out_gt45/len(e_out):.1f}%)",
        "%A_en_norte_si_D1_norte": f"{a_in_north_when_d1_north:.1f}%"
    })
print(pd.DataFrame(rows_c1).to_string(index=False))

# Ahora veamos en semanas de prueba (te) qué pasa fuera del norte (|D1|>45) y
# qué pasa cuando |A - consenso_pares| > 45° fuera del norte
def calibrated(src, truth, tr):
    sec = (((src + 11.25) % 360) // 22.5)
    key = pd.Series(sec.astype("Int64").astype(str) + "_" + band.astype(str), index=idx)
    ok = tr & src.notna()
    z = np.exp(1j * np.deg2rad(sdiff(truth[ok], src[ok])))
    g = z.groupby(key[ok]).mean()
    off = pd.Series(np.rad2deg(np.angle(g.to_numpy())), index=g.index)
    return (src + key.map(off)) % 360

print("\n--- Comparación en prueba (te) fuera del norte (|D1|>45°): global vs horas con cruce parcial ---")
rows_c1b = []
for t in TARGETS:
    truth = P["d1"][t]
    base = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna()
    tr, te = base & (week == 0), base & (week == 1)
    U = pd.Series(0.0, index=idx); W = U.copy(); S_ = U.copy()
    for s in [s for s in P["dir"].columns if s != t]:
        pred = calibrated(P["dir"][s], truth, tr)
        e_tr = ang(pred[tr], truth[tr]).mean()
        if not np.isfinite(e_tr): continue
        wgt = 1 / max(e_tr, 5) ** 2
        m = pred.notna()
        U[m] += wgt * np.sin(np.deg2rad(pred[m]))
        W[m] += wgt * np.cos(np.deg2rad(pred[m]))
        S_[m] += wgt
    comb = (np.rad2deg(np.arctan2(U, W)) % 360).where(S_ > 0)
    non_n = te & (ang(truth, 0) > 45)
    eo = ang(P["a"][t], truth)
    ec = ang(comb, truth)
    # Horas fuera del norte donde A tiene error > 30° (cruces parciales por 0/360)
    part_cross = non_n & (eo > 30)
    # Horas fuera del norte detectables SIN usar D1: p.ej. cuando A cae en [60, 300] pero consenso dice cerca del norte (<=60) y |A - comb| > 45
    det_no_d1 = non_n & (ang(comb, 0) <= 65) & (ang(P["a"][t], comb) > 50)
    rows_c1b.append({
        "estacion": t,
        "fuera_norte_A": round(eo[non_n].mean(), 1),
        "fuera_norte_Pares": round(ec[non_n].mean(), 1),
        "fuera_norte_A>30_n": int(part_cross.sum()),
        "en_A>30_err_A": round(eo[part_cross].mean(), 1) if part_cross.sum() else np.nan,
        "en_A>30_err_Pares": round(ec[part_cross].mean(), 1) if part_cross.sum() else np.nan,
        "detectable_sin_D1_n": int(det_no_d1.sum()),
        "det_err_A": round(eo[det_no_d1].mean(), 1) if det_no_d1.sum() else np.nan,
        "det_err_Pares": round(ec[det_no_d1].mean(), 1) if det_no_d1.sum() else np.nan,
    })
print(pd.DataFrame(rows_c1b).to_string(index=False))

# ==============================================================================
# AFIRMACION 2: ¿Por qué falla el IDW crudo 25-58°? Desglose metodológico vs físico
# ==============================================================================
print("\n======================================================================")
print("AFIRMACION 2: Desglose de fallos del IDW crudo")
print("======================================================================")
# Compare:
# 1) IDW de idw_all.py (con estaciones malas/lejanas y ws cruda)
# 2) IDW con red limpia (--limpio) y ws cruda
# 3) IDW con red limpia y vectores unitarios (sin ponderar por ws cruda)
# 4) IDW con red limpia pero excluyendo en vecinas sin D1 las horas en que su propio A está entre 120 y 240 cuando las demás apuntan al norte, o usando solo vecinas con D1
# 5) IDW penalizando desnivel vertical: d_eff = sqrt(d_km^2 + (5 * dz_km)^2)
u_ws = P["ws"] * np.sin(np.deg2rad(P["dir"]))
w_ws = P["ws"] * np.cos(np.deg2rad(P["dir"]))
u_unit = np.sin(np.deg2rad(P["dir"]))
w_unit = np.cos(np.deg2rad(P["dir"]))

rows_c2 = []
for t in TARGETS:
    truth = P["d1"][t]
    ok = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna() & (week == 1)
    n_mk = ok & (ang(truth, 0) <= 45)
    nb_all = [s for s in P["dir"].columns if s != t]
    nb_d1 = [s for s in TARGETS if s != t and s in P["dir"].columns]
    
    d_km = pd.Series({s: np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1])/1000 for s in nb_all})
    dz_km = pd.Series({s: abs(Z[t]-Z[s])/1000 for s in nb_all})
    
    # 1) IDW limpio ws * 1/d^2
    p1 = 1 / d_km**2
    U1 = (u_ws[nb_all].fillna(0)*p1).sum(1); W1 = (w_ws[nb_all].fillna(0)*p1).sum(1)
    c1 = pd.Series(np.rad2deg(np.arctan2(U1, W1)) % 360, index=idx)
    
    # 2) IDW limpio unitario * 1/d^2 (sin sesgo de velocidad torre vs climavue)
    U2 = (u_unit[nb_all].fillna(0)*p1).sum(1); W2 = (w_unit[nb_all].fillna(0)*p1).sum(1)
    c2 = pd.Series(np.rad2deg(np.arctan2(U2, W2)) % 360, index=idx)
    
    # 3) IDW solo vecinas con D1 (sin contaminación de WindDir_Avg en el norte)
    p3 = 1 / d_km[nb_d1]**2
    U3 = (u_unit[nb_d1].fillna(0)*p3).sum(1); W3 = (w_unit[nb_d1].fillna(0)*p3).sum(1)
    c3 = pd.Series(np.rad2deg(np.arctan2(U3, W3)) % 360, index=idx)
    
    # 4) IDW con distancia 3D (penalizando desnivel: 1 km vertical = 8 km horizontal)
    p4 = 1 / (d_km**2 + (8.0 * dz_km)**2)
    U4 = (u_unit[nb_all].fillna(0)*p4).sum(1); W4 = (w_unit[nb_all].fillna(0)*p4).sum(1)
    c4 = pd.Series(np.rad2deg(np.arctan2(U4, W4)) % 360, index=idx)

    rows_c2.append({
        "estacion": t,
        "IDW_ws_d2": f"{ang(c1[ok], truth[ok]).mean():.1f} / {ang(c1[n_mk], truth[n_mk]).mean():.1f}",
        "IDW_unit_d2": f"{ang(c2[ok], truth[ok]).mean():.1f} / {ang(c2[n_mk], truth[n_mk]).mean():.1f}",
        "IDW_unit_soloD1": f"{ang(c3[ok], truth[ok]).mean():.1f} / {ang(c3[n_mk], truth[n_mk]).mean():.1f}",
        "IDW_unit_3D(dz)": f"{ang(c4[ok], truth[ok]).mean():.1f} / {ang(c4[n_mk], truth[n_mk]).mean():.1f}",
    })
print(pd.DataFrame(rows_c2).to_string(index=False))

# ==============================================================================
# AFIRMACION 3: Calibración, baseline climatológico, sobreajuste y entrenamiento sin D1
# ==============================================================================
print("\n======================================================================")
print("AFIRMACION 3: Escrutinio de calib.py y pairs_calib.py")
print("======================================================================")
# 1) ¿Qué pasa si predecimos SOLO la climatología horaria de la estación objetivo (sin mirar ninguna vecina)?
# 2) ¿Qué pasa en calib.py y pairs_calib.py si entrenamos con WindDir_Avg (caso real en estación sin D1) en vez de D1?
# 3) ¿Qué pasa si en pairs_calib ponderamos por la concentración |g| de cada celda y solo top-3 vecinas?
rows_c3 = []
for t in TARGETS:
    truth = P["d1"][t]
    avg_own = P["a"][t]
    base = (P["ws"][t] > 1) & truth.notna() & avg_own.notna()
    tr, te = base & (week == 0), base & (week == 1)
    n_te = te & (ang(truth, 0) <= 45)
    
    # Baseline 0: Climatología horaria pura (24 horas del día, sin vecinas)
    z_clim = np.exp(1j * np.deg2rad(truth[tr])).groupby(hr[tr]).mean()
    clim_hr = pd.Series(np.rad2deg(np.angle(z_clim.to_numpy())) % 360, index=z_clim.index)
    pred_clim = pd.Series(hr, index=idx).map(clim_hr)
    
    # Consenso IDW crudo
    nb = [s for s in P["dir"].columns if s != t]
    p = pd.Series({s: 1 / (np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1])/1000)**2 for s in nb})
    m = u_ws[nb].notna()
    U = (u_ws[nb].fillna(0)*p).sum(1)/(m*p).sum(1); W = (w_ws[nb].fillna(0)*p).sum(1)/(m*p).sum(1)
    c = pd.Series(np.rad2deg(np.arctan2(U, W)) % 360, index=idx)
    
    # Calib sobre consenso entrenado con D1 (oráculo) vs entrenado con WindDir_Avg (realista sin D1)
    cal_d1 = calibrated(c, truth, tr)
    cal_avg = calibrated(c, avg_own, tr)
    
    # Pairs calib entrenado con D1 vs entrenado con WindDir_Avg
    U_p1 = pd.Series(0.0, index=idx); W_p1 = U_p1.copy()
    U_pa = pd.Series(0.0, index=idx); W_pa = U_pa.copy()
    U_R = pd.Series(0.0, index=idx); W_R = U_R.copy()
    
    for s in nb:
        # Con D1
        pred_s = calibrated(P["dir"][s], truth, tr)
        e_tr = ang(pred_s[tr], truth[tr]).mean()
        if np.isfinite(e_tr):
            wgt = 1 / max(e_tr, 5)**2
            mk = pred_s.notna()
            U_p1[mk] += wgt * np.sin(np.deg2rad(pred_s[mk]))
            W_p1[mk] += wgt * np.cos(np.deg2rad(pred_s[mk]))
        # Con Avg_own (sin D1)
        pred_sa = calibrated(P["dir"][s], avg_own, tr)
        e_tra = ang(pred_sa[tr], avg_own[tr]).mean()
        if np.isfinite(e_tra):
            wgta = 1 / max(e_tra, 5)**2
            mk = pred_sa.notna()
            U_pa[mk] += wgta * np.sin(np.deg2rad(pred_sa[mk]))
            W_pa[mk] += wgta * np.cos(np.deg2rad(pred_sa[mk]))
            
        # Mejorado: ponderando cada celda por concentración R = |g|^2 y penalizando muestras pequeñas (n / (n + 10))
        src_s = P["dir"][s]
        sec = (((src_s + 11.25) % 360) // 22.5)
        key = pd.Series(sec.astype("Int64").astype(str) + "_" + band.astype(str), index=idx)
        ok_s = tr & src_s.notna()
        z = np.exp(1j * np.deg2rad(sdiff(truth[ok_s], src_s[ok_s])))
        grp = z.groupby(key[ok_s])
        g_mean = grp.mean()
        g_cnt = grp.count()
        off_s = pd.Series(np.rad2deg(np.angle(g_mean.to_numpy())), index=g_mean.index)
        r_cell = pd.Series(np.abs(g_mean.to_numpy()) * (g_cnt / (g_cnt + 10.0)), index=g_mean.index)
        pred_sr = (src_s + key.map(off_s)) % 360
        w_cell = (key.map(r_cell).fillna(0) ** 3) * (1 / max(e_tr, 10)**2 if np.isfinite(e_tr) else 0)
        mk = pred_sr.notna()
        U_R[mk] += w_cell[mk] * np.sin(np.deg2rad(pred_sr[mk]))
        W_R[mk] += w_cell[mk] * np.cos(np.deg2rad(pred_sr[mk]))

    comb_d1 = np.rad2deg(np.arctan2(U_p1, W_p1)) % 360
    comb_avg = np.rad2deg(np.arctan2(U_pa, W_pa)) % 360
    comb_R = np.rad2deg(np.arctan2(U_R, W_R)) % 360
    
    f = lambda p: f"{ang(p[te], truth[te]).mean():.1f} / {ang(p[n_te], truth[n_te]).mean():.1f}"
    rows_c3.append({
        "estacion": t,
        "Solo_Climatologia": f(pred_clim),
        "Calib_IDW(con_D1)": f(cal_d1),
        "Pares(con_D1)": f(comb_d1),
        "Pares(entrenado_con_Avg!)": f(comb_avg),
        "Pares_ponderado_R_celda": f(comb_R)
    })
print(pd.DataFrame(rows_c3).to_string(index=False))

# ==============================================================================
# AFIRMACION 4: ¿Cuál es la mejor vecina en cada estación (todas vs norte, cruda vs calibrada)?
# ==============================================================================
print("\n======================================================================")
print("AFIRMACION 4: Ranking de vecinas en PRUEBA (todas vs norte, cruda vs calibrada)")
print("======================================================================")
for t in TARGETS:
    truth = P["d1"][t]
    base = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna()
    tr, te = base & (week == 0), base & (week == 1)
    n_te = te & (ang(truth, 0) <= 45)
    nb = [s for s in P["dir"].columns if s != t]
    res_nb = []
    for s in nb:
        d_km = np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1]) / 1000
        pred = calibrated(P["dir"][s], truth, tr)
        e_tr = ang(pred[tr], truth[tr]).mean()
        e_te = ang(pred[te], truth[te]).mean()
        e_raw_te = ang(P["dir"][s][te], truth[te]).mean()
        e_n_te = ang(pred[n_te], truth[n_te]).mean()
        n_obs_te = pred[te].notna().sum()
        n_obs_n = pred[n_te].notna().sum()
        res_nb.append({
            "vecina": s, "km": round(d_km, 2), "n_te": n_obs_te, "n_norte": n_obs_n,
            "raw_te": round(e_raw_te, 1), "cal_tr": round(e_tr, 1),
            "cal_te": round(e_te, 1), "cal_norte_te": round(e_n_te, 1)
        })
    df_nb = pd.DataFrame(res_nb)
    # Filtrar estaciones con cobertura razonable (>500 horas en te) para evitar sesgo de Sarallenque (solo oct)
    df_nb_full = df_nb[df_nb.n_te >= 500]
    by_dist = df_nb.sort_values("km").iloc[0]
    best_te = df_nb_full.sort_values("cal_te").iloc[:3]
    best_n = df_nb_full.sort_values("cal_norte_te").iloc[:3]
    print(f"\nEstación: {t} | Más cercana limpia: {by_dist['vecina']} ({by_dist['km']} km, cal_te={by_dist['cal_te']}°, norte={by_dist['cal_norte_te']}°)")
    print("  Top 3 cal_te (>500h):   ", ", ".join(f"{r.vecina} ({r.km}km: {r.cal_te}° / N:{r.cal_norte_te}° / raw:{r.raw_te}°)" for _, r in best_te.iterrows()))
    print("  Top 3 norte_te (>500h): ", ", ".join(f"{r.vecina} ({r.km}km: N:{r.cal_norte_te}° / tot:{r.cal_te}°)" for _, r in best_n.iterrows()))
    # Mostrar Sarallenque si estaba en el top del análisis
    sar = df_nb[df_nb.vecina == "Sarallenque"]
    if len(sar):
        r = sar.iloc[0]
        print(f"  [Nota Sarallenque: n_te={r.n_te} de {te.sum()} h ({100*r.n_te/te.sum():.1f}%), cal_tr={r.cal_tr}°, cal_te={r.cal_te}°, cal_norte={r.cal_norte_te}°]")

# ==============================================================================
# AFIRMACION 5: Efecto real de excluir estaciones defectuosas (mismas horas de prueba y con Dique)
# ==============================================================================
print("\n======================================================================")
print("AFIRMACION 5: Efecto real de excluir estaciones defectuosas")
print("======================================================================")
# Compararemos sobre EL MISMO conjunto de horas de prueba limpias (te_clean) de cada estación objetivo:
# Escenario A: Todas las estaciones en XY INCLUYENDO Dique_pie_botadero, Chalsos, Sarallenque, Mina_Norte, Planta_Concentradora, etc.
# Escenario B: Como calib.py sin --limpio (todas menos Dique_pie_botadero)
# Escenario C: Con --limpio pero manteniendo Planta_Concentradora
# Escenario D: Con --limpio exacto de calib.py
df_A = df_raw[df_raw.st.isin(XY)].copy()
df_A["dir"] = df_A.d1.fillna(df_A.a)
P_A = {c: df_A.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws")}

df_B = df_raw[df_raw.st.isin(XY) & (df_raw.st != "Dique_pie_botadero")].copy()
df_B["dir"] = df_B.d1.fillna(df_B.a)
P_B = {c: df_B.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws")}

df_C = df_raw.copy()
drop_C = {"Dique_pie_botadero", "Chalsos", "Mina_Norte", "Ilo", "Huachunta", "Vizcachas", "Titire"} # sin tirar Planta_Concentradora
df_C = df_C[df_C.st.isin(XY) & ~df_C.st.isin(drop_C)]
df_C = df_C[~((df_C.st == "Sarallenque") & (df_C.ts < "2026-09-25 21:00"))]
df_C = df_C[df_C.ws >= 0.5]
for st, a, b in [("Alto_Quellaveco", "2026-09-15 11:00", "2099"), ("Cortadera", "2026-09-13 11:00", "2099"),
                 ("Alto_Tala", "2026-08-18 05:00", "2026-09-23 15:00")]:
    df_C = df_C[~((df_C.st == st) & (df_C.ts >= a) & (df_C.ts <= b))]
df_C["dir"] = df_C.d1.fillna(df_C.a)
P_C = {c: df_C.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws")}

def eval_idw_scenario(P_scen, t, tr, te, n_te):
    u_s = P_scen["ws"] * np.sin(np.deg2rad(P_scen["dir"]))
    w_s = P_scen["ws"] * np.cos(np.deg2rad(P_scen["dir"]))
    nb = [s for s in P_scen["dir"].columns if s != t]
    p = pd.Series({s: 1 / (np.hypot(XY[t][0]-XY[s][0], XY[t][1]-XY[s][1])/1000)**2 for s in nb})
    m = u_s[nb].notna()
    U = (u_s[nb].fillna(0)*p).sum(1)/(m*p).sum(1); W = (w_s[nb].fillna(0)*p).sum(1)/(m*p).sum(1)
    c = pd.Series(np.rad2deg(np.arctan2(U, W)) % 360, index=idx)
    truth = P["d1"][t]
    cal = calibrated(c, truth, tr)
    return f"{ang(c[te], truth[te]).mean():.1f}->{ang(cal[te], truth[te]).mean():.1f} (N:{ang(cal[n_te], truth[n_te]).mean():.1f})"

rows_c5 = []
for t in TARGETS:
    truth = P["d1"][t]
    base = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna()
    tr, te = base & (week == 0), base & (week == 1)
    n_te = te & (ang(truth, 0) <= 45)
    rows_c5.append({
        "estacion": t,
        "A_Todas(con_Dique)": eval_idw_scenario(P_A, t, tr, te, n_te),
        "B_Sin_Dique(calib.py)": eval_idw_scenario(P_B, t, tr, te, n_te),
        "C_Limpio_con_Planta": eval_idw_scenario(P_C, t, tr, te, n_te),
        "D_Limpio(sin_Planta)": eval_idw_scenario(P, t, tr, te, n_te),
    })
print("Formato: Crudo->Calibrado_Total (N: Calibrado_Norte) evaluado sobre las MISMAS horas limpias:")
print(pd.DataFrame(rows_c5).to_string(index=False))
