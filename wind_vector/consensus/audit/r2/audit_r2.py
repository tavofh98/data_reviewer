"""Auditoría completa del encargo r2: Afirmaciones 6, 7, 8 y 9.
Solo utiliza variables de viento (WindDir_D1_WVT, WindDir_Avg, WindDir_SD1_WVT, WS_ms_Avg).
"""
import warnings
warnings.filterwarnings("ignore")
import re
import duckdb
import numpy as np
import pandas as pd

DB = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db"
ST_FILE = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc/met_viewer/stations.py"

src = open(ST_FILE, encoding="utf-8").read()
XY = {m[0]: (float(m[1]), float(m[2])) for m in re.findall(r'"([^"]+)":\s+Station\((\d+), (\d+)', src)}

ang = lambda a, b: np.minimum(np.abs((a - b) % 360), 360 - np.abs((a - b) % 360))
sdiff = lambda a, b: (a - b + 180) % 360 - 180

def cmean_deg(s):
    """Media circular unitaria en grados [0, 360)."""
    s = pd.Series(s).dropna()
    if len(s) == 0:
        return np.nan
    r = np.deg2rad(s)
    return float(np.rad2deg(np.arctan2(np.sin(r).mean(), np.cos(r).mean())) % 360)

def cmean_vec(d, w):
    """Media vectorial ponderada por velocidad en grados [0, 360)."""
    m = pd.Series(d).notna() & pd.Series(w).notna()
    if m.sum() == 0:
        return np.nan
    r = np.deg2rad(d[m])
    u = (w[m] * np.sin(r)).mean()
    v = (w[m] * np.cos(r)).mean()
    return float(np.rad2deg(np.arctan2(u, v)) % 360)

def r_const(s):
    """Constancia direccional unitaria R en [0, 1]."""
    s = pd.Series(s).dropna()
    if len(s) == 0:
        return np.nan
    r = np.deg2rad(s)
    return float(np.hypot(np.sin(r).mean(), np.cos(r).mean()))

# 1. Consulta única del periodo de estudio (2025-11-01 -> 2026-11-03) y resumen histórico por estación seleccionada
con = duckdb.connect(DB, read_only=True)
st_list = list(XY.keys())
st_sql = ",".join(f"'{s}'" for s in st_list)

df = con.execute(f"""
    SELECT estacion_id st, timestamp ts, WindDir_D1_WVT d1, WindDir_Avg a,
           WindDir_SD1_WVT sd1, WS_ms_Avg ws
    FROM meteorologia
    WHERE timestamp >= '2025-11-01' AND timestamp <= '2026-11-03 23:59:59'
      AND estacion_id IN ({st_sql})
""").df()

df_hist = con.execute("""
    SELECT estacion_id st, timestamp ts, year(timestamp) yr, month(timestamp) mo,
           dayofyear(timestamp) doy, hour(timestamp) hr,
           WindDir_D1_WVT d1, WindDir_Avg a, WindDir_SD1_WVT sd1, WS_ms_Avg ws
    FROM meteorologia
    WHERE estacion_id IN ('Altarani', 'Cortadera', 'Alto_Quellaveco', 'Camp_Quellaveco',
                          'Minas_Sur', 'Calientes1', 'Tala-1', 'Apacheta', 'Cerro_Salviani',
                          'Papujune', 'Sarallenque_MQG-15-02', 'Chancado_primario')
      AND timestamp >= '2020-01-01' AND timestamp <= '2026-11-03 23:59:59'
      AND WindDir_Avg IS NOT NULL
""").df()
con.close()

# Preparar pivots del periodo 2025-11-01 -> 2026-11-03
df_valid = df[df.a.notna()].copy()
df_valid["dir"] = df_valid.d1.fillna(df_valid.a)
P = {c: df_valid.pivot(index="ts", columns="st", values=c) for c in ("dir", "ws", "d1", "a", "sd1")}
idx = P["dir"].index
hr = idx.hour
is_night = (hr >= 22) | (hr <= 6)
is_day = (hr >= 10) & (hr <= 17)
is_trans = ~is_night & ~is_day
week = ((idx - idx[0]) // pd.Timedelta(days=7)) % 2

# Versíón con filtro --limpio para reproducir exactamente consensus_diagnosis.py
df_clean = df_valid.copy()
drop_clean = {"Dique_pie_botadero", "Chalsos", "Mina_Norte", "Planta_Concentradora", "Ilo", "Huachunta", "Vizcachas", "Titire"}
df_clean = df_clean[df_clean.st.isin(XY) & ~df_clean.st.isin(drop_clean)]
df_clean = df_clean[~((df_clean.st == "Sarallenque") & (df_clean.ts < "2026-09-25 21:00"))]
df_clean = df_clean[df_clean.ws >= 0.5]
for st_c, a_c, b_c in [("Alto_Quellaveco", "2026-09-15 11:00", "2099"),
                       ("Cortadera", "2026-09-13 11:00", "2099"),
                       ("Alto_Tala", "2026-08-18 05:00", "2026-09-23 15:00"),
                       ("Charaque", "2026-01-14 14:00", "2026-01-15 12:00"),
                       ("Charaque", "2026-01-28 14:00", "2026-01-29 07:00"),
                       ("Sarallenque_MQG-15-02", "2026-02-16 14:00", "2026-02-17 09:00")]:
    df_clean = df_clean[~((df_clean.st == st_c) & (df_clean.ts >= a_c) & (df_clean.ts <= b_c))]
Pc = {c: df_clean.pivot(index="ts", columns="st", values=c).reindex(idx) for c in ("dir", "ws", "d1", "a", "sd1")}

print("================================================================================")
print("AFIRMACION 6: ALTARANI DE NOCHE Y EL GIRO DE TALA-1 A 230-290° (104 h)")
print("================================================================================")

alt_d1 = P["d1"]["Altarani"]
alt_ws = P["ws"]["Altarani"]
alt_sd1 = P["sd1"]["Altarani"]
tala_d1 = P["d1"]["Tala-1"]
tala_ws = P["ws"]["Tala-1"]

for thr in [0.5, 1.0]:
    m = is_night & (alt_ws > thr if thr == 1.0 else alt_ws >= thr) & alt_d1.notna()
    se = ((alt_d1[m] >= 90) & (alt_d1[m] <= 180)).mean() * 100
    nw = ((alt_d1[m] >= 270) & (alt_d1[m] <= 360)).mean() * 100
    print(f"Altarani noche (ws {'>' if thr==1.0 else '>='} {thr}): N={m.sum()}, 90-180°={se:.2f}%, 270-360°={nw:.2f}%, "
          f"dir_media={cmean_deg(alt_d1[m]):.1f}°, R={r_const(alt_d1[m]):.3f}, sd1_med={alt_sd1[m].median():.1f}° (IQR {alt_sd1[m].quantile(0.25):.1f}-{alt_sd1[m].quantile(0.75):.1f}°)")

# Reproducción exacta de las 104 h con Tala-1 en 230-290°
for desc, m_cond in [
    ("is_night & alt_ws>1 & tala_ws>=0.5 & Tala-1 D1 in [230,290]",
     is_night & (alt_ws > 1) & alt_d1.notna() & (tala_ws >= 0.5) & (tala_d1 >= 230) & (tala_d1 <= 290)),
    ("is_night & alt_ws>1 & Tala-1 D1 in [230,290] (sin filtro ws Tala)",
     is_night & (alt_ws > 1) & alt_d1.notna() & (tala_d1 >= 230) & (tala_d1 <= 290)),
    ("is_night & alt_ws>=0.5 & tala_ws>=0.5 & Tala-1 D1 in [230,290]",
     is_night & (alt_ws >= 0.5) & alt_d1.notna() & (tala_ws >= 0.5) & (tala_d1 >= 230) & (tala_d1 <= 290)),
]:
    sub = alt_d1[m_cond]
    se_90_180 = ((sub >= 90) & (sub <= 180)).mean() * 100
    nw_270_360 = ((sub >= 270) & (sub <= 360)).mean() * 100
    nw_250_360 = ((sub >= 250) & (sub <= 360)).mean() * 100
    print(f"  [{desc}] -> N={len(sub)} | SE(90-180°): {se_90_180:.1f}% (n={((sub>=90)&(sub<=180)).sum()}), "
          f"NO(270-360°): {nw_270_360:.1f}% (n={((sub>=270)&(sub<=360)).sum()}), NO(250-360°): {nw_250_360:.1f}% (n={((sub>=250)&(sub<=360)).sum()})")

# Histórico 2021-2026 de Altarani (¿sitio o sensor?)
print("\n--- Histórico anual de Altarani (2021-2026, ws >= 0.5 m/s) ---")
ah = df_hist[(df_hist.st == "Altarani") & (df_hist.ws >= 0.5)].copy()
ah["dir"] = ah.d1.fillna(ah.a)
ah["fr"] = np.where((ah.hr >= 10) & (ah.hr <= 17), "Dia", np.where((ah.hr >= 22) | (ah.hr <= 6), "Noche", "Trans"))
for yr, g in ah.groupby("yr"):
    gn = g[g.fr == "Noche"]
    gd = g[g.fr == "Dia"]
    se_n = ((gn.dir >= 90) & (gn.dir <= 180)).mean() * 100
    se_n_gt1 = ((gn[gn.ws > 1].dir >= 90) & (gn[gn.ws > 1].dir <= 180)).mean() * 100
    nw_d = ((gd.dir >= 250) & (gd.dir <= 350)).mean() * 100
    print(f"  {yr}: Noche N={len(gn):4d} | %90-180(ws>=0.5)={se_n:5.1f}%, %90-180(ws>1)={se_n_gt1:5.1f}% | "
          f"dir_noche={cmean_deg(gn.dir):5.1f}° (R={r_const(gn.dir):.2f}, ws={gn.ws.mean():.2f}, sd1_med={gn.sd1.median():.1f}°) | "
          f"Día N={len(gd):4d} | dir_día={cmean_deg(gd.dir):5.1f}° (%250-350={nw_d:4.1f}%, ws={gd.ws.mean():.2f})")

# Chequear si hay rachas pegadas (criterio D) o SD1=0 en Altarani de noche
alt_n_all = is_night & (alt_ws >= 0.5) & alt_d1.notna()
d1_diff_1h = ang(alt_d1, alt_d1.shift(1))[alt_n_all]
print(f"\nAltarani noche 2025-2026: cambio horario mediano |D1(t)-D1(t-1)| = {d1_diff_1h.median():.1f}° (media {d1_diff_1h.mean():.1f}°), "
      f"% horas con SD1 < 1°: {(alt_sd1[alt_n_all] < 1.0).mean()*100:.2f}%, % con SD1 < 3°: {(alt_sd1[alt_n_all] < 3.0).mean()*100:.2f}%")

# Análisis detallado de las 104 h cuando Tala-1 está en 230-290° de noche
m104 = is_night & (alt_ws > 1) & alt_d1.notna() & (tala_ws >= 0.5) & (tala_d1 >= 230) & (tala_d1 <= 290)
if m104.sum() != 104:
    # probar con Pc
    m104 = is_night & (Pc["ws"]["Altarani"] > 1) & Pc["d1"]["Altarani"].notna() & (Pc["d1"]["Tala-1"] >= 230) & (Pc["d1"]["Tala-1"] <= 290)

sub104 = pd.DataFrame({
    "alt_d1": alt_d1[m104],
    "alt_ws": alt_ws[m104],
    "alt_sd1": alt_sd1[m104],
    "hr": idx[m104].hour,
    "tala_d1": tala_d1[m104],
    "tala_ws": tala_ws[m104],
    "mqg_dir": Pc["dir"]["Sarallenque_MQG-15-02"][m104],
    "mqg_ws": Pc["ws"]["Sarallenque_MQG-15-02"][m104],
    "aq_dir": Pc["dir"]["Alto_Quellaveco"][m104],
    "aq_ws": Pc["ws"]["Alto_Quellaveco"][m104],
    "ms_dir": Pc["dir"]["Minas_Sur"][m104],
    "ms_ws": Pc["ws"]["Minas_Sur"][m104],
    "cha_dir": Pc["dir"]["Charaque"][m104],
    "cha_ws": Pc["ws"]["Charaque"][m104],
    "pap_dir": Pc["dir"]["Papujune"][m104],
    "pap_ws": Pc["ws"]["Papujune"][m104],
})
sub104["reg"] = np.where((sub104.alt_d1 >= 90) & (sub104.alt_d1 <= 180), "SE (90-180)",
                np.where((sub104.alt_d1 >= 270) & (sub104.alt_d1 <= 360), "NO (270-360)", "Otro"))

print(f"\nDetalle de las N={len(sub104)} horas con Tala-1 en 230-290° de noche:")
print(sub104["reg"].value_counts())
print((sub104["reg"].value_counts(normalize=True) * 100).round(1))

print("\nMedias y medianas por régimen (SE vs NO) en esas 104 h (solo variables de viento):")
print(sub104.groupby("reg")[["alt_ws", "alt_sd1", "tala_ws", "mqg_ws", "aq_ws", "ms_ws", "cha_ws", "pap_ws"]].agg(["count", "mean", "median"]).round(2).to_string())

print("\nReparto por hora de la noche en esas 104 h:")
print(pd.crosstab(sub104.hr, sub104.reg))

# ¿Qué pasa en esas 104 h según la velocidad de Altarani, la hora y las vecinas de su propia cuenca (MQG, Charaque, Alto_Quellaveco)?
for vname, cond in [
    ("alt_ws > 2.2 m/s", sub104.alt_ws > 2.2),
    ("alt_ws > 2.5 m/s", sub104.alt_ws > 2.5),
    ("Hora 22-23h (cola vespertina)", sub104.hr >= 22),
    ("Charaque en O-NO (250-360°)", (sub104.cha_dir >= 250) & (sub104.cha_dir <= 360)),
    ("Sarallenque_MQG en O-NO (250-360°)", (sub104.mqg_dir >= 250) & (sub104.mqg_dir <= 360)),
    ("Sarallenque_MQG ws > 2.5 m/s", sub104.mqg_ws > 2.5),
    ("tala_ws > 3.5 m/s", sub104.tala_ws > 3.5),
    ("alt_ws > 2.2 O hr==22", (sub104.alt_ws > 2.2) | (sub104.hr == 22)),
    ("Sin usar alt_ws: (hr>=22) O (cha_dir en 260-360 y mqg_ws>2.2)",
     (sub104.hr >= 22) | (((sub104.cha_dir >= 260) & (sub104.cha_dir <= 360)) & (sub104.mqg_ws > 2.2))),
]:
    sub_b = sub104[sub104.reg.isin(["SE (90-180)", "NO (270-360)"])]
    c_b = cond.loc[sub_b.index]
    acc = ((c_b & (sub_b.reg == "NO (270-360)")) | (~c_b & (sub_b.reg == "SE (90-180)"))).mean() * 100
    tp = (c_b & (sub_b.reg == "NO (270-360)")).sum()
    fp = (c_b & (sub_b.reg == "SE (90-180)")).sum()
    tn = (~c_b & (sub_b.reg == "SE (90-180)")).sum()
    fn = (~c_b & (sub_b.reg == "NO (270-360)")).sum()
    print(f"  Regla [{vname}]: exactitud={acc:.1f}% (NO predicho: {tp} NO vs {fp} SE | SE predicho: {tn} SE vs {fn} NO)")

print("\n================================================================================")
print("AFIRMACION 7: CORTADERA DE NOCHE (ABANICO 0° A 135°)")
print("================================================================================")
cort_n = is_night & (idx < "2026-09-13 11:00") & (Pc["ws"]["Cortadera"] > 1) & Pc["d1"]["Cortadera"].notna()
c_d1 = Pc["d1"]["Cortadera"][cort_n]
c_a = Pc["a"]["Cortadera"][cort_n]
c_ws = Pc["ws"]["Cortadera"][cort_n]
c_sd1 = Pc["sd1"]["Cortadera"][cort_n]

print(f"Cortadera noche (pre 2026-09-13 11:00, ws > 1): N={len(c_d1)}, dir_media={cmean_deg(c_d1):.1f}°, R={r_const(c_d1):.3f}")
bins_cort = [
    ("315-360° (NO-N)", (c_d1 >= 315) & (c_d1 < 360)),
    ("0-45° (N-NE)", (c_d1 >= 0) & (c_d1 <= 45)),
    ("45-90° (NE-E)", (c_d1 > 45) & (c_d1 <= 90)),
    ("90-135° (E-SE)", (c_d1 > 90) & (c_d1 <= 135)),
    ("135-225° (S)", (c_d1 > 135) & (c_d1 <= 225)),
    ("225-315° (O)", (c_d1 > 225) & (c_d1 < 315)),
]
for lbl, m_b in bins_cort:
    print(f"  {lbl:18s}: {m_b.mean()*100:5.1f}% (n={m_b.sum():4d}) | ws={c_ws[m_b].mean():.2f} m/s, sd1={c_sd1[m_b].mean():.1f}°, |Avg-D1|={ang(c_a[m_b], c_d1[m_b]).mean():.1f}°")

in_0_135 = (c_d1 >= 0) & (c_d1 <= 135)
in_345_135 = ((c_d1 >= 345) | (c_d1 <= 135))
in_north = ang(c_d1, 0) <= 45
print(f"Total en 0-135°: {in_0_135.mean()*100:.1f}% (n={in_0_135.sum()}), en 345-135°: {in_345_135.mean()*100:.1f}%, en Norte (<=45°): {in_north.mean()*100:.1f}% (n={in_north.sum()})")

# Verificar qué predice el consenso calibrado por pares en Cortadera de noche
band = np.where(is_day, 0, np.where(is_night, 1, 2))
def calibrated(src, truth, tr):
    sec = (((src + 11.25) % 360) // 22.5)
    key = pd.Series(sec.astype("Int64").astype(str) + "_" + band.astype(str), index=idx)
    ok = tr & src.notna()
    z = np.exp(1j * np.deg2rad(sdiff(truth[ok], src[ok]))); g = z.groupby(key[ok]).mean()
    off = pd.Series(np.rad2deg(np.angle(g.to_numpy())), index=g.index)
    return (src + key.map(off)) % 360

truth_c = Pc["d1"]["Cortadera"]
base_c = (Pc["ws"]["Cortadera"] > 1) & truth_c.notna()
tr_c = base_c & (week == 0)
te_c = base_c & (week == 1)
U_c = pd.Series(0.0, index=idx); W_c = U_c.copy(); S_c = U_c.copy()
for s in [s for s in Pc["dir"].columns if s != "Cortadera"]:
    pred = calibrated(Pc["dir"][s], truth_c, tr_c)
    e_tr = ang(pred[tr_c], truth_c[tr_c]).mean()
    if not np.isfinite(e_tr): continue
    wgt = 1 / max(e_tr, 5) ** 2; m = pred.notna()
    U_c[m] += wgt * np.sin(np.deg2rad(pred[m])); W_c[m] += wgt * np.cos(np.deg2rad(pred[m])); S_c[m] += wgt
cons_c = (np.rad2deg(np.arctan2(U_c, W_c)) % 360).where(S_c > 0)

te_cn = te_c & is_night
te_cn_north = te_cn & (ang(truth_c, 0) <= 45)
print(f"\nConsenso por pares en Cortadera noche (semanas impares, N={te_cn.sum()}):")
print(f"  Predicción media del consenso de noche: {cmean_deg(cons_c[te_cn]):.1f}° (mediana {cons_c[te_cn].median():.1f}°, IQR {cons_c[te_cn].quantile(0.25):.1f}°-{cons_c[te_cn].quantile(0.75):.1f}°)")
print(f"  Error medio noche todas: {ang(cons_c[te_cn], truth_c[te_cn]).mean():.1f}°")
print(f"  Error medio noche cuando Cortadera es Norte (<=45°, N={te_cn_north.sum()}): {ang(cons_c[te_cn_north], truth_c[te_cn_north]).mean():.1f}° (pred media en esas horas: {cmean_deg(cons_c[te_cn_north]):.1f}° vs verdad media {cmean_deg(truth_c[te_cn_north]):.1f}°)")

# ¿Qué variable (velocidad, hora, SD1, mes, u otra vecina) indica la posición dentro del abanico 0-135° de noche?
# Evaluemos correlaciones y MAE de predicción de la posición dentro del abanico en Cortadera de noche
fan_mask = cort_n & ((c_d1 >= 330) | (c_d1 <= 150))
y_fan = sdiff(Pc["d1"]["Cortadera"][fan_mask], 60) + 60  # continuo en [-30, 150]
print(f"\nExploración de predictores de la posición en el abanico nocturno ([-30°, 150°], N={fan_mask.sum()}):")
print(f"  Media de y_fan: {y_fan.mean():.1f}°, std: {y_fan.std():.1f}°, MAE de predecir constante ({y_fan.median():.1f}°): {np.abs(y_fan - y_fan.median()).mean():.1f}°")

for vlbl, s_var in [
    ("WS propia Cortadera", Pc["ws"]["Cortadera"][fan_mask]),
    ("SD1 propia Cortadera", Pc["sd1"]["Cortadera"][fan_mask]),
    ("Hora de la noche (0..8 desde 22h)", ((idx[fan_mask].hour - 22) % 24).to_series(index=idx[fan_mask])),
    ("Mes (numérico)", idx[fan_mask].month.to_series(index=idx[fan_mask])),
]:
    r_p = y_fan.corr(s_var)
    r_s = y_fan.corr(s_var, method="spearman")
    print(f"  Correlación con {vlbl:34s}: Pearson r={r_p:+.3f}, Spearman rho={r_s:+.3f}")

# Probemos cada vecina individualmente (dirección calibrada solo en noche y velocidad)
print("\nCapacidad de cada vecina para predecir la posición en el abanico nocturno de Cortadera (test semanas impares):")
tr_fan = fan_mask & (week == 0)
te_fan = fan_mask & (week == 1)
te_fan_n = te_fan & (ang(truth_c, 0) <= 45)
for nb in sorted(Pc["dir"].columns):
    if nb == "Cortadera": continue
    # Calibrar desfase por sector de 22.5° de la vecina SOLO en horas de abanico nocturno
    src_nb = Pc["dir"][nb]
    ws_nb = Pc["ws"][nb]
    if src_nb[tr_fan].notna().sum() < 100 or src_nb[te_fan].notna().sum() < 50:
        continue
    sec_nb = (((src_nb + 11.25) % 360) // 22.5)
    ok_nb = tr_fan & src_nb.notna()
    z_nb = np.exp(1j * np.deg2rad(sdiff(truth_c[ok_nb], src_nb[ok_nb])))
    g_nb = z_nb.groupby(sec_nb[ok_nb]).mean()
    off_nb = pd.Series(np.rad2deg(np.angle(g_nb.to_numpy())), index=g_nb.index)
    pred_nb = (src_nb + sec_nb.map(off_nb)) % 360
    mae_all = ang(pred_nb[te_fan], truth_c[te_fan]).mean()
    mae_n = ang(pred_nb[te_fan_n], truth_c[te_fan_n]).mean()
    # Correlación circular/lineal de u,v de la vecina con y_fan
    r_u = y_fan.corr(np.sin(np.deg2rad(src_nb[fan_mask])))
    r_w = y_fan.corr(np.cos(np.deg2rad(src_nb[fan_mask])))
    r_ws = y_fan.corr(ws_nb[fan_mask])
    print(f"  {nb:22s}: N_test={src_nb[te_fan].notna().sum():4d} | MAE_abanico={mae_all:4.1f}°, MAE_norte={mae_n:4.1f}° | corr(sin,cos,ws)=({r_u:+.2f},{r_w:+.2f},{r_ws:+.2f})")

# Modelo multivariante (Ridge / RandomForest) con todas las vecinas + hora + ws propia + sd1 propia + mes
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

feat_cols = {}
feat_cols["hr_night"] = ((idx.hour - 22) % 24)
feat_cols["doy_sin"] = np.sin(2 * np.pi * idx.dayofyear / 365.25)
feat_cols["doy_cos"] = np.cos(2 * np.pi * idx.dayofyear / 365.25)
feat_cols["cort_ws"] = Pc["ws"]["Cortadera"]
feat_cols["cort_sd1"] = Pc["sd1"]["Cortadera"]
for nb in ["Calientes1", "Apacheta", "Cerro_Salviani", "Tala-1", "Tala_Legal", "Alto_Tala", "Papujune", "DME3_Cortadera", "Calacaja", "PMC-4_met"]:
    if nb in Pc["dir"]:
        feat_cols[f"{nb}_u"] = np.sin(np.deg2rad(Pc["dir"][nb]))
        feat_cols[f"{nb}_w"] = np.cos(np.deg2rad(Pc["dir"][nb]))
        feat_cols[f"{nb}_ws"] = Pc["ws"][nb]
X_all = pd.DataFrame(feat_cols, index=idx)

for m_name, cols_use in [
    ("Solo vecinas (u, w, ws)", [c for c in X_all.columns if c not in ("hr_night", "doy_sin", "doy_cos", "cort_ws", "cort_sd1")]),
    ("Vecinas + hora + ws/sd1 propia", [c for c in X_all.columns if c not in ("doy_sin", "doy_cos")]),
    ("Vecinas + hora + ws/sd1 + estación del año (doy)", list(X_all.columns)),
]:
    gbr = HistGradientBoostingRegressor(max_depth=4, min_samples_leaf=30, random_state=42)
    gbr.fit(X_all.loc[tr_fan, cols_use], y_fan.loc[tr_fan])
    p_fan = pd.Series(gbr.predict(X_all.loc[te_fan, cols_use]) % 360, index=idx[te_fan])
    mae_all = ang(p_fan, truth_c[te_fan]).mean()
    mae_n = ang(p_fan.loc[idx[te_fan_n]], truth_c[te_fan_n]).mean()
    r2_te = 1 - ((y_fan.loc[te_fan] - gbr.predict(X_all.loc[te_fan, cols_use]))**2).mean() / y_fan.loc[te_fan].var()
    print(f"  HGBR [{m_name:48s}]: R2_test={r2_te:+.3f} | MAE_abanico={mae_all:.1f}°, MAE_norte={mae_n:.1f}°")

# ¿Y la memoria temporal (D1 o Avg de la hora anterior)?
lag1_d1 = truth_c.shift(1)
print(f"  Persistencia D1(t-1) en abanico nocturno: corr={y_fan.corr(y_fan.shift(1)):+.3f}, MAE_abanico={ang(lag1_d1[te_fan], truth_c[te_fan]).mean():.1f}°, MAE_norte={ang(lag1_d1[te_fan_n], truth_c[te_fan_n]).mean():.1f}°")

# Histórico anual de Cortadera de noche (2021-2026)
print("\n--- Histórico anual de Cortadera de noche (2021-2026, ws > 1.0 m/s, pre-sep13 en 2026) ---")
ch = df_hist[(df_hist.st == "Cortadera") & (df_hist.ws > 1.0) & (df_hist.ts < "2026-09-13 11:00")].copy()
ch["dir"] = ch.d1.fillna(ch.a)
ch_n = ch[(ch.hr >= 22) | (ch.hr <= 6)]
for yr, g in ch_n.groupby("yr"):
    p_0_45 = ((g.dir >= 0) & (g.dir <= 45)).mean() * 100
    p_45_90 = ((g.dir > 45) & (g.dir <= 90)).mean() * 100
    p_90_135 = ((g.dir > 90) & (g.dir <= 135)).mean() * 100
    p_norte = (ang(g.dir, 0) <= 45).mean() * 100
    print(f"  {yr}: N={len(g):4d} | 0-45°={p_0_45:4.1f}%, 45-90°={p_45_90:4.1f}%, 90-135°={p_90_135:4.1f}% (total 0-135°={p_0_45+p_45_90+p_90_135:4.1f}%) | Norte(<=45°)={p_norte:4.1f}% | dir_media={cmean_deg(g.dir):5.1f}°, R={r_const(g.dir):.2f}")

print("\n================================================================================")
print("AFIRMACION 8: CAMP_QUELLAVECO DE NOCHE (¿SENSOR O MÉTODO/EXPOSICIÓN?)")
print("================================================================================")
# Datos sin filtro de calma (df_valid) para medir % de calmas y ceros
camp_ws_raw = P["ws"]["Camp_Quellaveco"]
camp_d1_raw = P["d1"]["Camp_Quellaveco"]
camp_sd1_raw = P["sd1"]["Camp_Quellaveco"]
m_camp_n = is_night & camp_ws_raw.notna()
print(f"Camp_Quellaveco noche (2025-11-01 a 2026-11-03, N={m_camp_n.sum()}):")
print(f"  ws == 0.00: {(camp_ws_raw[m_camp_n] == 0).mean()*100:.1f}% (n={(camp_ws_raw[m_camp_n] == 0).sum()})")
print(f"  ws < 0.5 m/s (calmas): {(camp_ws_raw[m_camp_n] < 0.5).mean()*100:.1f}% (n={(camp_ws_raw[m_camp_n] < 0.5).sum()})")
print(f"  0.5 <= ws <= 1.0 m/s: {((camp_ws_raw[m_camp_n] >= 0.5) & (camp_ws_raw[m_camp_n] <= 1.0)).mean()*100:.1f}% (n={((camp_ws_raw[m_camp_n] >= 0.5) & (camp_ws_raw[m_camp_n] <= 1.0)).sum()})")
print(f"  ws > 1.0 m/s (LAS ÚNICAS QUE EVALÚA EL CONSENSO): {(camp_ws_raw[m_camp_n] > 1.0).mean()*100:.1f}% (n={(camp_ws_raw[m_camp_n] > 1.0).sum()})")

# Evaluar consenso por pares en Camp_Quellaveco para desglosar el error antes y después de 2026-09-10, por franja y velocidad
truth_cq = Pc["d1"]["Camp_Quellaveco"]
base_cq = (Pc["ws"]["Camp_Quellaveco"] > 1) & truth_cq.notna()
tr_cq = base_cq & (week == 0)
te_cq = base_cq & (week == 1)
U_cq = pd.Series(0.0, index=idx); W_cq = U_cq.copy(); S_cq = U_cq.copy()
for s in [s for s in Pc["dir"].columns if s != "Camp_Quellaveco"]:
    pred = calibrated(Pc["dir"][s], truth_cq, tr_cq)
    e_tr = ang(pred[tr_cq], truth_cq[tr_cq]).mean()
    if not np.isfinite(e_tr): continue
    wgt = 1 / max(e_tr, 5) ** 2; m = pred.notna()
    U_cq[m] += wgt * np.sin(np.deg2rad(pred[m])); W_cq[m] += wgt * np.cos(np.deg2rad(pred[m])); S_cq[m] += wgt
cons_cq = (np.rad2deg(np.arctan2(U_cq, W_cq)) % 360).where(S_cq > 0)
err_cq = ang(cons_cq, truth_cq)

for lbl_p, m_p in [("Todo el año (nov25-nov26)", pd.Series(True, index=idx)),
                   ("Antes de 2026-09-10 (sin fallos de 0.00)", idx < "2026-09-10"),
                   ("Desde 2026-09-10 (tras calibración)", idx >= "2026-09-10")]:
    m_n_raw = m_camp_n & m_p
    m_te_n = te_cq & is_night & m_p
    m_te_t = te_cq & is_trans & m_p
    m_te_d = te_cq & is_day & m_p
    m_te_north = te_cq & (ang(truth_cq, 0) <= 45) & m_p
    print(f"\n  [{lbl_p}]:")
    print(f"    Noche total N={m_n_raw.sum()}: %ws==0: {(camp_ws_raw[m_n_raw]==0).mean()*100:.1f}%, %ws<0.5: {(camp_ws_raw[m_n_raw]<0.5).mean()*100:.1f}%, %ws>1.0: {(camp_ws_raw[m_n_raw]>1.0).mean()*100:.1f}% (n={(camp_ws_raw[m_n_raw]>1.0).sum()})")
    print(f"    Evaluación consenso (ws>1, semanas impares): Noche N={m_te_n.sum()} -> err={err_cq[m_te_n].mean():.1f}° | Trans N={m_te_t.sum()} -> err={err_cq[m_te_t].mean():.1f}° | Día N={m_te_d.sum()} -> err={err_cq[m_te_d].mean():.1f}° | Norte N={m_te_north.sum()} -> err={err_cq[m_te_north].mean():.1f}°")

# ¿Dónde están las horas del Norte (<=45°) evaluadas en Camp_Quellaveco (semanas impares, ws>1)?
m_cq_north = te_cq & (ang(truth_cq, 0) <= 45)
print(f"\nDesglose de las N={m_cq_north.sum()} horas del Norte evaluadas en Camp_Quellaveco (semanas impares, ws > 1):")
for fn_l, fn_m in [("Día (10-17h)", is_day), ("Noche (22-06h)", is_night), ("Transición (07-09, 18-21h)", is_trans)]:
    sub_m = m_cq_north & fn_m
    print(f"  {fn_l:26s}: N={sub_m.sum():3d} ({sub_m.sum()/m_cq_north.sum()*100:4.1f}%) | err_consenso={err_cq[sub_m].mean():.1f}°, ws_media={Pc['ws']['Camp_Quellaveco'][sub_m].mean():.2f}, sd1_media={Pc['sd1']['Camp_Quellaveco'][sub_m].mean():.1f}°")

# Histórico 2020-2026 de Camp_Quellaveco de noche frente a Chancado_primario y Tala-1 (efecto de la reubicación del 2022-10-06)
print("\n--- Histórico anual de Camp_Quellaveco de noche (2020-2026) ---")
cq_h = df_hist[df_hist.st == "Camp_Quellaveco"].copy()
cq_h["dir"] = cq_h.d1.fillna(cq_h.a)
cq_hn = cq_h[(cq_h.hr >= 22) | (cq_h.hr <= 6)].copy()
cq_hn["periodo_sitio"] = np.where(cq_hn.ts < "2022-10-06", "Pre-reubic (<=2022-10-05)", "Post-reubic (>=2022-10-06)")
for (yr, ps), g in cq_hn.groupby(["yr", "periodo_sitio"]):
    pct_calm = (g.ws < 0.5).mean() * 100
    pct_zero = (g.ws == 0).mean() * 100
    pct_gt1 = (g.ws > 1.0).mean() * 100
    g_gt1 = g[g.ws > 1.0]
    print(f"  {yr} ({ps:26s}): N={len(g):4d} | %ws==0={pct_zero:4.1f}%, %<0.5={pct_calm:4.1f}%, %>1.0={pct_gt1:4.1f}% (n={len(g_gt1):3d}) | "
          f"con ws>1: dir={cmean_deg(g_gt1.dir):5.1f}°, R={r_const(g_gt1.dir):.2f}, sd1={g_gt1.sd1.mean():.1f}°")

print("\n================================================================================")
print("AFIRMACION 9: GIROS DE CORTADERA (2026-09-13) Y ALTO_QUELLAVECO (2026-09-15)")
print("================================================================================")

# 1. Inspección hora a hora alrededor del inicio del cambio para determinar fecha y hora exactas
for st_g, d_center, ref_g in [("Cortadera", "2026-09-13", "Calientes1"),
                              ("Alto_Quellaveco", "2026-09-15", "Minas_Sur")]:
    print(f"\n--- Serie horaria alrededor de {d_center} en {st_g} (ref: {ref_g}) ---")
    t0 = pd.Timestamp(d_center) - pd.Timedelta(hours=6)
    t1 = pd.Timestamp(d_center) + pd.Timedelta(hours=30)
    # Consultar sobre df bruto (incluyendo filas con WindDir_Avg NULL si existen) y el rango horario completo
    full_rng = pd.date_range(t0, t1, freq="1h")
    sub_st = df[(df.st == st_g) & (df.ts >= t0) & (df.ts <= t1)].set_index("ts").reindex(full_rng)
    sub_rf = df[(df.st == ref_g) & (df.ts >= t0) & (df.ts <= t1)].set_index("ts").reindex(full_rng)
    for ts_i in full_rng:
        r_s = sub_st.loc[ts_i]
        r_r = sub_rf.loc[ts_i]
        d_s = r_s.d1 if pd.notna(r_s.d1) else r_s.a
        d_r = r_r.d1 if pd.notna(r_r.d1) else r_r.a
        dif_sr = sdiff(d_s, d_r) if (pd.notna(d_s) and pd.notna(d_r)) else np.nan
        print(f"  {ts_i}: {st_g} dir={d_s if pd.notna(d_s) else 'NULL':>6} (ws={r_s.ws if pd.notna(r_s.ws) else 'NULL':>5}, sd1={r_s.sd1 if pd.notna(r_s.sd1) else 'NULL':>5}) | "
              f"{ref_g} dir={d_r if pd.notna(d_r) else 'NULL':>6} (ws={r_r.ws if pd.notna(r_r.ws) else 'NULL':>5}) | Δ({st_g}-{ref_g})={dif_sr:+6.1f}°" if pd.notna(dif_sr) else
              f"  {ts_i}: {st_g} dir={'NULL':>6} (ws={'NULL':>5}) | {ref_g} dir={d_r if pd.notna(d_r) else 'NULL':>6}")

# 2. Estimación del ángulo de giro (Día, Noche, Transición, 24h) frente a sí misma y frente a múltiples vecinas
def analyze_rotation(st_g, t_b0, t_b1, t_a0, t_a1, nbs):
    print(f"\n=== Estimación de giro para {st_g} ===")
    print(f"Periodo ANTES: {t_b0} -> {t_b1} | Periodo DESPUÉS: {t_a0} -> {t_a1}")
    d_st = P["dir"][st_g]
    w_st = P["ws"][st_g]
    mb = (idx >= t_b0) & (idx <= t_b1) & (w_st >= 0.5) & d_st.notna()
    ma = (idx >= t_a0) & (idx <= t_a1) & (w_st >= 0.5) & d_st.notna()

    for fn_l, fn_m in [("Día (10-17h)", is_day), ("Noche (22-06h)", is_night), ("Transición", is_trans), ("Todas (24h)", pd.Series(True, index=idx))]:
        bs = d_st[mb & fn_m]; as_ = d_st[ma & fn_m]
        bw = w_st[mb & fn_m]; aw = w_st[ma & fn_m]
        m_b = cmean_deg(bs); m_a = cmean_deg(as_)
        mv_b = cmean_vec(bs, bw); mv_a = cmean_vec(as_, aw)
        # Correlación de histogramas cada 1°
        hb, _ = np.histogram(bs, bins=np.arange(0, 361, 5), density=True)
        ha, _ = np.histogram(as_, bins=np.arange(0, 361, 5), density=True)
        best_deg, best_cos = 0, -1
        cos0 = float(np.dot(hb, ha) / (np.linalg.norm(hb) * np.linalg.norm(ha) + 1e-12))
        for deg in range(-180, 180):
            # rotar los datos crudos de 'después' restando deg para alinear con 'antes'
            ha_r, _ = np.histogram((as_ - deg) % 360, bins=np.arange(0, 361, 5), density=True)
            c_v = float(np.dot(hb, ha_r) / (np.linalg.norm(hb) * np.linalg.norm(ha_r) + 1e-12))
            if c_v > best_cos:
                best_cos = c_v; best_deg = deg
        print(f"  {fn_l:15s}: Antes={m_b:5.1f}° (vec {mv_b:5.1f}°, n={len(bs):3d}, ws={bw.mean():.2f}) -> "
              f"Después={m_a:5.1f}° (vec {mv_a:5.1f}°, n={len(as_):3d}, ws={aw.mean():.2f}) | "
              f"Δ_unit={sdiff(m_a, m_b):+6.1f}°, Δ_vec={sdiff(mv_a, mv_b):+6.1f}° | Giro_hist={best_deg:+4d}° (cos {cos0:.2f}->{best_cos:.2f})")

    print(f"\n  Comparación con múltiples vecinas de referencia para {st_g} (Δ = cambio en la diferencia circular [{st_g} - vecina]):")
    for nb in nbs:
        d_nb = P["dir"][nb]; w_nb = P["ws"][nb]
        ok_b = mb & (w_nb >= 0.5) & d_nb.notna()
        ok_a = ma & (w_nb >= 0.5) & d_nb.notna()
        res_str = []
        for fn_l, fn_m in [("Día", is_day), ("Noche", is_night), ("24h", pd.Series(True, index=idx))]:
            nb_b = cmean_deg(d_nb[ok_b & fn_m]); nb_a = cmean_deg(d_nb[ok_a & fn_m])
            # Diferencia hora a hora (st - nb) antes vs después
            dif_b = cmean_deg(sdiff(d_st[ok_b & fn_m], d_nb[ok_b & fn_m]) % 360)
            dif_a = cmean_deg(sdiff(d_st[ok_a & fn_m], d_nb[ok_a & fn_m]) % 360)
            shift_rel = sdiff(dif_a, dif_b)
            shift_nb = sdiff(nb_a, nb_b)
            res_str.append(f"{fn_l}: vecina {nb_b:3.0f}°->{nb_a:3.0f}° (Δvec={shift_nb:+4.0f}°), Δ({st_g}-vec)={shift_rel:+6.1f}°")
        print(f"    vs {nb:22s} | " + " | ".join(res_str))

analyze_rotation("Cortadera", "2026-07-15 00:00", "2026-09-13 10:00", "2026-09-13 12:00", "2026-11-03 23:00",
                 ["Calientes1", "Apacheta", "Cerro_Salviani", "Tala_Legal", "DME3_Cortadera", "Calacaja"])

analyze_rotation("Alto_Quellaveco", "2026-07-15 00:00", "2026-09-15 10:00", "2026-09-15 13:00", "2026-11-03 23:00",
                 ["Minas_Sur", "Papujune", "Sarallenque_MQG-15-02", "Altarani", "Tala-1", "Cerro_Salviani"])

# 3. Evolución semana a semana de Alto_Quellaveco y Cortadera tras el giro (¿giro fijo o deriva?)
for st_g, t_start, ref_g in [("Cortadera", "2026-09-13 12:00", "Calientes1"),
                             ("Alto_Quellaveco", "2026-09-15 13:00", "Minas_Sur")]:
    print(f"\n--- Evolución semanal post-cambio en {st_g} (ref: {ref_g}) ---")
    m_post = (idx >= "2026-08-17") & (P["ws"][st_g] >= 0.5) & P["dir"][st_g].notna()
    wk_lbl = idx.to_series().dt.to_period("W").astype(str)
    for w_k, g_idx in idx[m_post].to_series().groupby(wk_lbl[m_post]):
        m_w = idx.isin(g_idx)
        d_day = cmean_deg(P["dir"][st_g][m_w & is_day & (P["ws"][st_g] >= 0.5)])
        d_nig = cmean_deg(P["dir"][st_g][m_w & is_night & (P["ws"][st_g] >= 0.5)])
        r_day = cmean_deg(P["dir"][ref_g][m_w & is_day & (P["ws"][ref_g] >= 0.5)])
        r_nig = cmean_deg(P["dir"][ref_g][m_w & is_night & (P["ws"][ref_g] >= 0.5)])
        print(f"  Semana {w_k}: {st_g} Día={d_day:5.1f}°, Noche={d_nig:5.1f}° | {ref_g} Día={r_day:5.1f}°, Noche={r_nig:5.1f}° | ΔDía={sdiff(d_day, r_day):+6.1f}°, ΔNoche={sdiff(d_nig, r_nig):+6.1f}°")

# 4. Comparación multianual del mismo periodo del año (15 sep - 03 nov, DOY 258-307) en 2020-2026
print("\n--- Comparación histórica del mismo periodo del año (15 Sep - 03 Nov, DOY 258-307) en 2020-2026 ---")
sub_doy = df_hist[(df_hist.doy >= 258) & (df_hist.doy <= 307) & (df_hist.ws >= 0.5)].copy()
sub_doy["dir"] = sub_doy.d1.fillna(sub_doy.a)
sub_doy["fr"] = np.where((sub_doy.hr >= 10) & (sub_doy.hr <= 17), "Día",
                np.where((sub_doy.hr >= 22) | (sub_doy.hr <= 6), "Noche", "Trans"))
for st_h in ["Cortadera", "Calientes1", "Alto_Quellaveco", "Minas_Sur"]:
    print(f"\nPeriodo 15 Sep - 03 Nov por año en {st_h}:")
    g_st = sub_doy[sub_doy.st == st_h]
    for yr, gy in g_st.groupby("yr"):
        gd = gy[gy.fr == "Día"]; gn = gy[gy.fr == "Noche"]
        print(f"  {yr}: Día={cmean_deg(gd.dir):5.1f}° (R={r_const(gd.dir):.2f}, ws={gd.ws.mean():.2f}, n={len(gd):3d}) | "
              f"Noche={cmean_deg(gn.dir):5.1f}° (R={r_const(gn.dir):.2f}, ws={gn.ws.mean():.2f}, n={len(gn):3d})")

print("\n================================================================================")
print("VERIFICACIONES ADICIONALES: AFIRMACIONES 6 Y 9")
print("================================================================================")

# A6.1: Encontrar la condición exacta de las 104 h (45 SE = 43.3%, 53 NO = 51.0%) y el 96.1% de Altarani
for h_cond_lbl, h_mask in [
    ("hr>=22 | hr<=6 (22-06h)", (hr >= 22) | (hr <= 6)),
    ("hr>=21 | hr<=5 (21-05h)", (hr >= 21) | (hr <= 5)),
    ("hr>=22 | hr<=5 (22-05h)", (hr >= 22) | (hr <= 5)),
    ("hr>=23 | hr<=6 (23-06h)", (hr >= 23) | (hr <= 6)),
    ("hr>=0 & hr<=6 (00-06h)", (hr >= 0) & (hr <= 6)),
]:
    for w_alt_thr in [0.5, 1.0]:
        m_a = h_mask & (alt_ws > w_alt_thr) & alt_d1.notna()
        pct_se_all = ((alt_d1[m_a] >= 90) & (alt_d1[m_a] <= 180)).mean() * 100
        for w_tala_thr in [0.0, 0.5, 1.0]:
            m_t = m_a & (tala_ws > w_tala_thr) & (tala_d1 >= 230) & (tala_d1 <= 290)
            n_t = m_t.sum()
            if 90 <= n_t <= 170 or abs(pct_se_all - 96.1) < 0.5:
                se_c = ((alt_d1[m_t] >= 90) & (alt_d1[m_t] <= 180)).sum()
                nw_c = ((alt_d1[m_t] >= 270) & (alt_d1[m_t] <= 360)).sum()
                nw250_c = ((alt_d1[m_t] >= 250) & (alt_d1[m_t] <= 360)).sum()
                print(f"  Filtro [{h_cond_lbl}, alt_ws>{w_alt_thr}, tala_ws>{w_tala_thr}]: "
                      f"All_SE={pct_se_all:.1f}% (N={m_a.sum()}) | Con Tala 230-290: N={n_t}, "
                      f"SE(90-180)={se_c} ({se_c/max(n_t,1)*100:.1f}%), NO(270-360)={nw_c} ({nw_c/max(n_t,1)*100:.1f}%), NO(250-360)={nw250_c} ({nw250_c/max(n_t,1)*100:.1f}%)")

# También probar la condición de red al oeste de 03_claims_6_to_9.py
clean_nbs = ["Alto_Quellaveco", "Minas_Sur", "Papujune", "Tala-1", "Tala_Legal", "Charaque", "Chancado_primario", "Cerro_Salviani"]
u_nbs = np.sin(np.deg2rad(P["dir"][clean_nbs]))
w_nbs = np.cos(np.deg2rad(P["dir"][clean_nbs]))
net_dir = pd.Series(np.rad2deg(np.arctan2(u_nbs.mean(1), w_nbs.mean(1))) % 360, index=idx)
m_net104 = is_night & (alt_ws > 1) & alt_d1.notna() & (ang(net_dir, 270) <= 45)
print(f"  Condición 03_claims_6_to_9 (net_dir en 225-315°, alt_ws>1, 22-06h): N={m_net104.sum()}, "
      f"SE={((alt_d1[m_net104]>=90)&(alt_d1[m_net104]<=180)).sum()} ({((alt_d1[m_net104]>=90)&(alt_d1[m_net104]<=180)).mean()*100:.1f}%), "
      f"NO(270-360)={((alt_d1[m_net104]>=270)&(alt_d1[m_net104]<=360)).sum()} ({((alt_d1[m_net104]>=270)&(alt_d1[m_net104]<=360)).mean()*100:.1f}%)")

# A6.2: Analizar exactamente las 104 h (alt_ws > 1, tala_ws > 1, Tala-1 en 230-290°, 22-06h)
m104_exact = is_night & (alt_ws > 1) & alt_d1.notna() & (tala_ws > 1) & (tala_d1 >= 230) & (tala_d1 <= 290)
print(f"\nAnálisis exacto sobre m104_exact (is_night & alt_ws>1 & tala_ws>1 & Tala-1 in 230-290): N={m104_exact.sum()}")
s104 = pd.DataFrame({
    "alt_d1": alt_d1[m104_exact],
    "alt_ws": alt_ws[m104_exact],
    "alt_sd1": alt_sd1[m104_exact],
    "hr": idx[m104_exact].hour,
    "mo": idx[m104_exact].month,
    "tala_d1": tala_d1[m104_exact],
    "tala_ws": tala_ws[m104_exact],
    "mqg_dir": Pc["dir"]["Sarallenque_MQG-15-02"][m104_exact],
    "mqg_ws": Pc["ws"]["Sarallenque_MQG-15-02"][m104_exact],
    "aq_dir": Pc["dir"]["Alto_Quellaveco"][m104_exact],
    "aq_ws": Pc["ws"]["Alto_Quellaveco"][m104_exact],
    "cha_dir": Pc["dir"]["Charaque"][m104_exact],
    "cha_ws": Pc["ws"]["Charaque"][m104_exact],
    "pap_dir": Pc["dir"]["Papujune"][m104_exact],
    "pap_ws": Pc["ws"]["Papujune"][m104_exact],
    "lag1_alt": alt_d1.shift(1)[m104_exact],
})
s104["reg"] = np.where((s104.alt_d1 >= 90) & (s104.alt_d1 <= 180), "SE (90-180)",
              np.where((s104.alt_d1 >= 270) & (s104.alt_d1 <= 360), "NO (270-360)", "Otro"))
print(s104["reg"].value_counts())
print((s104["reg"].value_counts(normalize=True) * 100).round(1))
print("\nReparto por tramo de noche (22-23h vs 00-06h) en m104_exact:")
s104["tramo"] = np.where(s104.hr >= 22, "22-23h (inicio noche)", "00-06h (madrugada)")
print(pd.crosstab(s104.tramo, s104.reg, margins=True))
print((pd.crosstab(s104.tramo, s104.reg, normalize="index") * 100).round(1))

print("\nComparación de variables de viento entre SE y NO en m104_exact:")
print(s104.groupby("reg")[["alt_ws", "alt_sd1", "tala_ws", "mqg_ws", "aq_ws", "cha_ws", "pap_ws"]].agg(["count", "mean", "median"]).round(2).to_string())

print("\nReparto según si las vecinas de la misma cuenca (Sarallenque_MQG, Alto_Quellaveco) o Charaque están en régimen Oeste (240-360°):")
for nb_c, col_d in [("Sarallenque_MQG-15-02", "mqg_dir"), ("Alto_Quellaveco", "aq_dir"), ("Charaque", "cha_dir"), ("Papujune", "pap_dir")]:
    w_flag = (s104[col_d] >= 240) & (s104[col_d] <= 360)
    ct = pd.crosstab(w_flag, s104.reg)
    ctn = (pd.crosstab(w_flag, s104.reg, normalize="index") * 100).round(1)
    print(f"  {nb_c} en 240-360°:\n{ct}\n{ctn}")

# A6.3: ¿Qué pasó en Altarani en 2025 para que bajara a 82.4% en 90-180°? Desglose mensual 2024-2026
print("\n--- Altarani noche (ws > 1.0 m/s) mes a mes (2024-01 a 2026-11) ---")
ah_n = ah[(ah.fr == "Noche") & (ah.ws > 1.0) & (ah.ts >= "2024-01-01")].copy()
ah_n["ym"] = ah_n.ts.dt.strftime("%Y-%m")
for ym, g in ah_n.groupby("ym"):
    se_p = ((g.dir >= 90) & (g.dir <= 180)).mean() * 100
    ne_p = ((g.dir >= 0) & (g.dir < 90)).mean() * 100
    nw_p = ((g.dir >= 270) & (g.dir <= 360)).mean() * 100
    sw_p = ((g.dir > 180) & (g.dir < 270)).mean() * 100
    print(f"  {ym}: N={len(g):3d} | 0-90°(NE)={ne_p:4.1f}%, 90-180°(SE)={se_p:5.1f}%, 180-270°(SO)={sw_p:4.1f}%, 270-360°(NO)={nw_p:4.1f}% | dir_media={cmean_deg(g.dir):5.1f}°, R={r_const(g.dir):.2f}, ws={g.ws.mean():.2f}, sd1={g.sd1.median():.1f}°")

# A9.1: Desglose cada 2 horas (00-23h) del giro de Cortadera y Alto_Quellaveco (absoluto y relativo a vecina de control)
for st_g, ref_g, tb0, tb1, ta0, ta1 in [
    ("Cortadera", "Calientes1", "2026-07-15 00:00", "2026-09-13 10:00", "2026-09-13 13:00", "2026-11-03 23:00"),
    ("Alto_Quellaveco", "Minas_Sur", "2026-07-15 00:00", "2026-09-15 10:00", "2026-09-15 12:00", "2026-11-03 23:00"),
]:
    print(f"\n--- Giro por bloques de 2 horas en {st_g} (control: {ref_g}) ---")
    d_s = P["dir"][st_g]; w_s = P["ws"][st_g]
    d_r = P["dir"][ref_g]; w_r = P["ws"][ref_g]
    mb = (idx >= tb0) & (idx <= tb1) & (w_s >= 0.5) & d_s.notna() & (w_r >= 0.5) & d_r.notna()
    ma = (idx >= ta0) & (idx <= ta1) & (w_s >= 0.5) & d_s.notna() & (w_r >= 0.5) & d_r.notna()
    for h0 in range(0, 24, 2):
        mh = (hr >= h0) & (hr < h0 + 2)
        sb = d_s[mb & mh]; sa = d_s[ma & mh]
        rb = d_r[mb & mh]; ra = d_r[ma & mh]
        dif_b = cmean_deg(sdiff(sb, rb) % 360)
        dif_a = cmean_deg(sdiff(sa, ra) % 360)
        print(f"  {h0:02d}-{h0+1:02d}h: {st_g} {cmean_deg(sb):5.1f}° -> {cmean_deg(sa):5.1f}° (Δ_abs={sdiff(cmean_deg(sa), cmean_deg(sb)):+6.1f}°) | "
              f"{ref_g} {cmean_deg(rb):5.1f}° -> {cmean_deg(ra):5.1f}° (Δ_ref={sdiff(cmean_deg(ra), cmean_deg(rb)):+5.1f}°) | "
              f"Δ_rel({st_g}-{ref_g})={sdiff(dif_a, dif_b):+6.1f}° (nb={len(sb):3d}, na={len(sa):3d})")

