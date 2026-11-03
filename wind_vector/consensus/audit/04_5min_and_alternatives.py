"""Análisis de los datos de 5 min (Table3, Afirmación 10), profundización en Afirmaciones 6-8,
y evaluación de propuestas alternativas (horarias y de 5 min)."""
import warnings
warnings.filterwarnings("ignore")
import os
import re
import duckdb
import numpy as np
import pandas as pd

DB = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db"
ST_FILE = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc/met_viewer/stations.py"
REFS = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/references"

src = open(ST_FILE, encoding="utf-8").read()
XY = {m[0]: (float(m[1]), float(m[2])) for m in re.findall(r'"([^"]+)":\s+Station\((\d+), (\d+)', src)}

ang = lambda a, b: np.minimum(np.abs((a - b) % 360), 360 - np.abs((a - b) % 360))
sdiff = lambda a, b: (a - b + 180) % 360 - 180

con = duckdb.connect(DB, read_only=True)
df_raw = con.execute("""
    SELECT estacion_id st, timestamp ts, WindDir_D1_WVT d1, WindDir_Avg a,
           WindDir_SD1_WVT sd1, WS_ms_Avg ws, AirTC_Avg tc, RH_Avg rh
    FROM meteorologia
    WHERE timestamp >= '2025-11-01' AND WindDir_Avg IS NOT NULL
""").df()
con.close()

# ==============================================================================
# 1. AFIRMACION 6: Encontrar las ~104 h exactas de Altarani y probar predictores
# ==============================================================================
print("======================================================================")
print("1. AFIRMACION 6: Las ~104 h de Altarani de noche cuando la red gira al oeste")
print("======================================================================")
# Aplicar --limpio como en calib.py
df = df_raw.copy()
drop = {"Dique_pie_botadero", "Chalsos", "Mina_Norte", "Planta_Concentradora", "Ilo", "Huachunta", "Vizcachas", "Titire"}
df = df[df.st.isin(XY) & ~df.st.isin(drop)]
df = df[~((df.st == "Sarallenque") & (df.ts < "2026-09-25 21:00"))]
df = df[df.ws >= 0.5]
for st, a, b in [("Alto_Quellaveco", "2026-09-15 11:00", "2099"), ("Cortadera", "2026-09-13 11:00", "2099"),
                 ("Alto_Tala", "2026-08-18 05:00", "2026-09-23 15:00"),
                 ("Charaque", "2026-01-14 14:00", "2026-01-15 12:00"), ("Charaque", "2026-01-28 14:00", "2026-01-29 07:00"),
                 ("Sarallenque_MQG-15-02", "2026-02-16 14:00", "2026-02-17 09:00")]:
    df = df[~((df.st == st) & (df.ts >= a) & (df.ts <= b))]
df["dir"] = df.d1.fillna(df.a)
P = {c: df.pivot(index="ts", columns="st", values=c) for c in ("dir", "ws", "d1", "a", "sd1", "tc", "rh")}
idx = P["dir"].index
week = ((idx - idx[0]) // pd.Timedelta(days=7)) % 2
hr = idx.hour
band = np.where((hr >= 10) & (hr <= 17), 0, np.where((hr >= 22) | (hr <= 6), 1, 2))

# Consenso IDW de Altarani (como en calib.py)
t = "Altarani"
nb = [s for s in P["dir"].columns if s != t]
p = pd.Series({s: 1 / (np.hypot(XY[t][0] - XY[s][0], XY[t][1] - XY[s][1]) / 1000) ** 2 for s in nb})
u = P["ws"] * np.sin(np.deg2rad(P["dir"])); w = P["ws"] * np.cos(np.deg2rad(P["dir"]))
m = u[nb].notna()
U = (u[nb].fillna(0) * p).sum(axis=1) / (m * p).sum(axis=1); W = (w[nb].fillna(0) * p).sum(axis=1) / (m * p).sum(axis=1)
c_alt = pd.Series(np.rad2deg(np.arctan2(U, W)) % 360, index=idx)

# Chequear cuándo c_alt (o vecinas) está en el oeste de noche:
ok_alt = (P["ws"]["Altarani"] > 1) & P["d1"]["Altarani"].notna() & (band == 1)
for name_c, mask_c in [
    ("IDW c_alt en 225-315° (todas las semanas)", ok_alt & (c_alt >= 225) & (c_alt <= 315)),
    ("IDW c_alt en 240-330° (todas las semanas)", ok_alt & (c_alt >= 240) & (c_alt <= 330)),
    ("IDW c_alt en 250-340° (todas las semanas)", ok_alt & (c_alt >= 250) & (c_alt <= 340)),
    ("Media unitaria red en 240-330°", ok_alt & (np.rad2deg(np.arctan2(np.sin(np.deg2rad(P['dir'][nb])).mean(1), np.cos(np.deg2rad(P['dir'][nb])).mean(1)))%360).between(240, 330)),
]:
    d_sub = P["d1"]["Altarani"][mask_c]
    se_pct = d_sub.between(90, 180).mean() * 100
    nw_pct = d_sub.between(270, 360).mean() * 100
    print(f"  {name_c}: N={len(d_sub)} h | SE(90-180°): {se_pct:.1f}% | NO(270-360°): {nw_pct:.1f}%")

# En esas horas nocturnas con IDW en el oeste (225-330°), ¿podemos predecir SE vs NO sin usar D1 de Altarani?
# ¡OJO! Si queremos saber si en Altarani el viento viene del SE (~135°) o del NO (~315°) en una hora dada:
# 1) Si miramos WindDir_Avg de Altarani: en SE (135°) NO cruza el norte, así que WindDir_Avg ≈ 135°. En NO (315°), ¿cuánto vale WindDir_Avg y qué hacen las variables meteorológicas (T, RH, dT, presión, hora, vecinas)?
# 2) Y si predecimos SOLO desde vecinas + variables térmicas/humedad (sin mirar WindDir_Avg de Altarani):
mask_west = ok_alt & (c_alt >= 225) & (c_alt <= 330)
sub_idx = idx[mask_west]
y_se = P["d1"]["Altarani"][mask_west].between(90, 180).astype(int) # 1 = SE, 0 = NO/otro
X_feat = pd.DataFrame({
    "is_22_23h": (sub_idx.hour >= 22).astype(float),
    "rh_alt": P["rh"]["Altarani"][mask_west].values,
    "tc_alt": P["tc"]["Altarani"][mask_west].values,
    "ws_alt": P["ws"]["Altarani"][mask_west].values,
    "dT_chancado": (P["tc"]["Chancado_primario"] - P["tc"]["Altarani"])[mask_west].values,
    "dT_camp": (P["tc"]["Camp_Quellaveco"] - P["tc"]["Altarani"])[mask_west].values,
    "mqg_sin": np.sin(np.deg2rad(P["dir"]["Sarallenque_MQG-15-02"][mask_west].fillna(0))).values,
    "mqg_cos": np.cos(np.deg2rad(P["dir"]["Sarallenque_MQG-15-02"][mask_west].fillna(0))).values,
    "tala_cos": np.cos(np.deg2rad(P["dir"]["Tala-1"][mask_west].fillna(0))).values,
    "month_wet": sub_idx.month.isin([12, 1, 2, 3]).astype(float),
}, index=sub_idx).fillna(0)

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
w_sub = week[mask_west]
clf = LogisticRegression(max_iter=500)
clf.fit(X_feat[w_sub == 0], y_se[w_sub == 0])
pred_se = clf.predict(X_feat[w_sub == 1])
acc_se = (pred_se == y_se[w_sub == 1]).mean()
# Error angular en esas horas de prueba si asignamos 135° cuando pred_se==1 y 310° cuando pred_se==0 vs desfase único (que asigna ~135° o ~220°):
d1_te_w = P["d1"]["Altarani"][mask_west][w_sub == 1]
c_te_w = c_alt[mask_west][w_sub == 1]
# Desfase único aprendido en tr sobre mask_west:
off_single = np.rad2deg(np.angle(np.exp(1j * np.deg2rad(sdiff(P["d1"]["Altarani"][mask_west][w_sub == 0], c_alt[mask_west][w_sub == 0]))).mean()))
pred_single = (c_te_w + off_single) % 360
pred_cond = np.where(pred_se == 1, 135.0, 310.0)
print(f"  En prueba (mask_west, n={len(d1_te_w)}): Exactitud clasificador logístico SE vs NO = {acc_se*100:.1f}%")
print(f"  Error medio desfase único: {ang(pred_single, d1_te_w).mean():.1f}° vs Error medio condicional (T/RH/hora/vecinas): {ang(pred_cond, d1_te_w).mean():.1f}°")

# ==============================================================================
# 2. ARCHIVOS DE 5 MINUTOS (Table3) Y AFIRMACION 10
# ==============================================================================
print("\n======================================================================")
print("2. AFIRMACION 10: Reconstrucción desde datos de 5 min (Table3) con y sin vecinas")
print("======================================================================")
TABLE3_MAP = {
    "Altarani": os.path.join(REFS, "AQQ_Est_Altarani_CR1000X_Table3.dat"),
    "Alto_Quellaveco": os.path.join(REFS, "val_wind_vector", "AAQ_Alto_Quellaveco_CR1000X_Table3.dat"),
    "Camp_Quellaveco": os.path.join(REFS, "AAQ_Est_Camp_Quellaveco_CR1000X_Table3.dat"),
    "Cortadera": os.path.join(REFS, "val_wind_vector", "AAQ_Est_Cortadera_CR1000X_Table3.dat"),
    "Minas_Sur": os.path.join(REFS, "AAQ_Minas_Sur_Table3.dat"),
    "Papujune": os.path.join(REFS, "val_wind_vector", "AAQ_Est_Papujune_CR1000X_Table3.dat"),
    "Tala-1": os.path.join(REFS, "AAQ_Est_Tala-1_CR310X_Table3.dat"),
    "Tala_Legal": os.path.join(REFS, "AAQ_Tala_Legal_Table3.dat"),
}

def load_table3_fast(filepath, min_date="2025-10-31"):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        col_line = f.readline().strip()
        _ = f.readline()
        _ = f.readline()
        cols = [c.strip('"') for c in col_line.split(",")]
        idx_ts = cols.index("TIMESTAMP")
        idx_ws = cols.index("WS_ms_Avg") if "WS_ms_Avg" in cols else -1
        idx_wd = cols.index("WindDir_Avg") if "WindDir_Avg" in cols else -1
        idx_d1 = cols.index("WindDir_D1_WVT") if "WindDir_D1_WVT" in cols else -1
        idx_sd1 = cols.index("WindDir_SD1_WVT") if "WindDir_SD1_WVT" in cols else -1
        rows = []
        for line in f:
            if line < f'"{min_date}':
                continue
            parts = line.strip().split(",")
            if len(parts) <= max(idx_ts, idx_ws, idx_wd):
                continue
            ts_str = parts[idx_ts].strip('"')
            if ts_str < min_date:
                continue
            try:
                ws_v = float(parts[idx_ws]) if idx_ws >= 0 and parts[idx_ws] not in ('"NAN"', 'NAN', '') else np.nan
                wd_v = float(parts[idx_wd]) if idx_wd >= 0 and parts[idx_wd] not in ('"NAN"', 'NAN', '') else np.nan
                d1_v = float(parts[idx_d1]) if idx_d1 >= 0 and parts[idx_d1] not in ('"NAN"', 'NAN', '') else np.nan
                sd1_v = float(parts[idx_sd1]) if idx_sd1 >= 0 and parts[idx_sd1] not in ('"NAN"', 'NAN', '') else np.nan
                rows.append((ts_str, ws_v, wd_v, d1_v, sd1_v))
            except ValueError:
                continue
    df5 = pd.DataFrame(rows, columns=["ts", "ws", "wd_avg", "d1", "sd1"])
    df5["ts"] = pd.to_datetime(df5["ts"])
    df5 = df5.drop_duplicates(subset=["ts"]).sort_values("ts")
    return df5

rows_5m = []
for st_name, fp in TABLE3_MAP.items():
    df5 = load_table3_fast(fp)
    if len(df5) == 0:
        print(f"Sin datos >= 2025-11 en {st_name}")
        continue
    # En Campbell, el registro horario de las HH:00:00 comprende los 12 registros de 5 min:
    # (HH-1):05, (HH-1):10, ..., HH:00 -> es decir, ceil('h')!
    # Verifiquemos la alineación exacta con la tabla horaria:
    df5["hr_ts"] = df5["ts"].dt.ceil("h")
    
    # ¿Cuántos bloques de 5 min tienen mezcla del norte (|wd_avg - d1| > 30°)?
    valid5 = df5.dropna(subset=["ws", "wd_avg", "d1"])
    valid5 = valid5[valid5.ws > 0.2]
    err5 = ang(valid5.wd_avg, valid5.d1)
    pct_mix_5m = (err5 > 30).mean() * 100
    
    # Método 1: Media vectorial directa de los 12 WindDir_Avg de 5 min (unitaria y ponderada por ws)
    # Campbell D1_WVT es media vectorial UNITARIA de dirección (o ponderada por ws para S_WVT; D1_WVT en instrucción WindVector(1, WS, WD, ...) depende del subtipo: tipo 1 = unit vector mean direction o velocity weighted).
    # Calculemos ambas: unitaria y ponderada por ws
    df5["u_unit"] = np.sin(np.deg2rad(df5["wd_avg"]))
    df5["w_unit"] = np.cos(np.deg2rad(df5["wd_avg"]))
    df5["u_ws"] = df5["ws"] * df5["u_unit"]
    df5["w_ws"] = df5["ws"] * df5["w_unit"]
    df5["u_d1"] = np.sin(np.deg2rad(df5["d1"]))
    df5["w_d1"] = np.cos(np.deg2rad(df5["d1"]))
    
    # Método 2 (SIN VECINAS - Auto-consistencia de 5 min):
    # En una hora donde el viento cruza 0°/360° dentro de uno o varios bloques de 5 min:
    # Un bloque de 5 min que cruza 0°/360° tiene muestras en ~355° y ~5°, por lo que su media aritmética wd_avg cae en [45°, 315°] (falso E/S/O),
    # mientras que otros bloques de esa misma hora (o ventana de ±30 min) NO cruzaron en esos 5 min y caen cerca del norte ([315°, 360°] o [0°, 45°]),
    # O bien hay saltos enormes entre bloques consecutivos de 5 min (> 45° en 5 min)!
    # Además, si en la hora hay al menos 2 bloques en el sector norte (ang(wd_avg, 0) <= 50°) y ningún régimen estable en el sur (los bloques fuera del norte tienen alta variación entre sí |Δwd| > 25°),
    # los bloques que cayeron en [50°, 310°] son MEZCLAS DEL NORTE (su media aritmética ~ 360 * p indica que p fracción del tiempo estuvo en ~350° y (1-p) en ~10°!).
    # ¡Es más! Si sabemos que un bloque de 5 min con wd_avg en [40°, 320°] es una mezcla del norte entre ~350° y ~10°,
    # entonces la fracción de muestras en el lado >180° es p ≈ wd_avg / 360!
    # Por tanto, su vector medio unitario verdadero en esos 5 min NO apunta a wd_avg, sino a:
    # u_reconstructed ≈ p * sin(352°) + (1 - p) * sin(8°), w_reconstructed ≈ cos(8°) ≈ 0.98!
    # ¡¡FÍSICA Y MATEMÁTICA EXACTA DEL PROMEDIO ARITMÉTICO EN EL CRUCE 0°/360°!!
    
    # Probemos este reconstructor matemático de 5 min SIN VECINAS:
    wd_arr = df5["wd_avg"].to_numpy()
    ws_arr = df5["ws"].to_numpy()
    # Diferencia con el bloque anterior y siguiente de 5 min:
    prev_diff = ang(wd_arr, np.roll(wd_arr, 1)); prev_diff[0] = 0
    next_diff = ang(wd_arr, np.roll(wd_arr, -1)); next_diff[-1] = 0
    jump_5m = np.maximum(prev_diff, next_diff)
    
    # Por cada hora (grupo de 12 bloques), veamos cuántos bloques están cerca del norte (ang <= 55°) y cuál es la estabilidad
    df5["jump"] = jump_5m
    df5["in_n55"] = (ang(df5["wd_avg"], 0) <= 55).astype(int)
    hr_stats = df5.groupby("hr_ts").agg(
        n_blocks=("wd_avg", "count"),
        n_north=("in_n55", "sum"),
        max_jump=("jump", "max"),
        mean_jump=("jump", "mean"),
        wd_hr_arith=("wd_avg", "mean")
    )
    df5 = df5.merge(hr_stats, on="hr_ts", how="left")
    
    # ¿Cuándo un bloque de 5 min que está fuera de [-45, 45] es una "mezcla del norte"?
    # Caso A: En su misma hora hay bloques en el norte (n_north >= 1) y este bloque dio un salto > 35° (o está entre 45° y 315° con mean_jump > 20°)
    # Caso B: Aunque n_north == 0 (los 12 bloques de 5 min cruzaron 0/360 porque el viento estuvo todo el rato oscilando entre 350° y 10°!),
    # en ese caso los 12 bloques tienen wd_avg fluctuando erráticamente entre 60° y 300° (jump > 25° entre bloques de 5 min, cuando un viento real del S/O tiene jump < 12°!).
    is_mix_block = (
        ((ang(df5["wd_avg"], 0) > 45) & (df5["n_north"] >= 2) & (df5["jump"] > 25)) |
        ((ang(df5["wd_avg"], 0) > 45) & (df5["n_north"] >= 4)) |
        ((ang(df5["wd_avg"], 0) > 55) & (df5["n_north"] >= 1) & (df5["jump"] > 45))
    )
    # Para un bloque detectado como mezcla del norte, p = wd_avg / 360 es la proporción de muestras de 5s en el lado NNO (~350°) vs NNE (~10°):
    p_nno = np.clip(df5["wd_avg"] / 360.0, 0.0, 1.0)
    u_clean = np.where(is_mix_block, p_nno * np.sin(np.deg2rad(350.0)) + (1 - p_nno) * np.sin(np.deg2rad(10.0)), df5["u_unit"])
    w_clean = np.where(is_mix_block, p_nno * np.cos(np.deg2rad(350.0)) + (1 - p_nno) * np.cos(np.deg2rad(10.0)), df5["w_unit"])
    df5["u_clean"] = u_clean
    df5["w_clean"] = w_clean
    
    # Agrupar por hora
    g_hr = df5.groupby("hr_ts").agg(
        u_unit=("u_unit", "mean"), w_unit=("w_unit", "mean"),
        u_ws=("u_ws", "mean"), w_ws=("w_ws", "mean"),
        u_d1=("u_d1", "mean"), w_d1=("w_d1", "mean"),
        u_clean=("u_clean", "mean"), w_clean=("w_clean", "mean"),
        cnt=("wd_avg", "count")
    )
    g_hr = g_hr[g_hr.cnt >= 6]
    dir_5m_unit = pd.Series(np.rad2deg(np.arctan2(g_hr.u_unit, g_hr.w_unit)) % 360, index=g_hr.index)
    dir_5m_ws = pd.Series(np.rad2deg(np.arctan2(g_hr.u_ws, g_hr.w_ws)) % 360, index=g_hr.index)
    dir_5m_d1 = pd.Series(np.rad2deg(np.arctan2(g_hr.u_d1, g_hr.w_d1)) % 360, index=g_hr.index)
    dir_5m_clean = pd.Series(np.rad2deg(np.arctan2(g_hr.u_clean, g_hr.w_clean)) % 360, index=g_hr.index)
    
    # Cruzar con las horas de prueba (te) de meteorologia
    truth = P["d1"][st_name]
    avg_hr = P["a"][st_name]
    te_mask = (P["ws"][st_name] > 1) & truth.notna() & avg_hr.notna() & (week == 1)
    common = idx[te_mask].intersection(g_hr.index)
    if len(common) == 0:
        continue
    t_c = truth.loc[common]
    a_c = avg_hr.loc[common]
    n_c = ang(t_c, 0) <= 45
    
    f = lambda s: f"{ang(s.loc[common], t_c).mean():.1f} / {ang(s.loc[common][n_c], t_c[n_c]).mean():.1f}"
    rows_5m.append({
        "estacion": st_name,
        "horas_te": len(common),
        "horas_N": int(n_c.sum()),
        "%5m_mix": f"{pct_mix_5m:.1f}%",
        "Avg_1h": f(a_c),
        "Vec_5m_crudo": f(dir_5m_unit),
        "Vec_5m_limpio(SIN_vecinas!)": f(dir_5m_clean),
        "Vec_5m_D1(techo)": f(dir_5m_d1),
    })

print("Error medio en semanas de prueba: Todas / Sector Norte (grados):")
print(pd.DataFrame(rows_5m).to_string(index=False))
