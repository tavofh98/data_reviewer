"""Auditoría cuantitativa de las Afirmaciones 6, 7, 8 y 9."""
import warnings
warnings.filterwarnings("ignore")
import re
import duckdb
import numpy as np
import pandas as pd

DB = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db"
ST_FILE = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc/met_viewer/stations.py"
INT_FILE = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/references/intervenciones_meteorologia.csv"

src = open(ST_FILE, encoding="utf-8").read()
XY = {m[0]: (float(m[1]), float(m[2])) for m in re.findall(r'"([^"]+)":\s+Station\((\d+), (\d+)', src)}

ang = lambda a, b: np.minimum(np.abs((a - b) % 360), 360 - np.abs((a - b) % 360))
sdiff = lambda a, b: (a - b + 180) % 360 - 180

con = duckdb.connect(DB, read_only=True)
df = con.execute("""
    SELECT estacion_id st, timestamp ts, WindDir_D1_WVT d1, WindDir_Avg a,
           WindDir_SD1_WVT sd1, WS_ms_Avg ws, AirTC_Avg tc, RH_Avg rh, BP_mbar_Avg bp
    FROM meteorologia
    WHERE timestamp >= '2025-11-01' AND WindDir_Avg IS NOT NULL
""").df()

# Datos históricos para chequear sitio vs sensor (2020-2026)
df_hist = con.execute("""
    SELECT estacion_id st, year(timestamp) yr, month(timestamp) mo, hour(timestamp) hr,
           WindDir_D1_WVT d1, WindDir_Avg a, WindDir_SD1_WVT sd1, WS_ms_Avg ws
    FROM meteorologia
    WHERE estacion_id IN ('Altarani', 'Cortadera', 'Alto_Quellaveco', 'Camp_Quellaveco', 'Minas_Sur', 'Calientes1')
      AND WS_ms_Avg >= 0.5 AND WindDir_Avg IS NOT NULL
""").df()
con.close()

df["dir"] = df.d1.fillna(df.a)
P = {c: df.pivot(index="ts", columns="st", values=c) for c in ("dir", "ws", "d1", "a", "sd1", "tc", "rh")}
idx = P["dir"].index
hr = idx.hour
is_night = (hr >= 22) | (hr <= 6)
is_day = (hr >= 10) & (hr <= 17)

# ==============================================================================
# AFIRMACION 6: Altarani de noche y cuando la red gira al oeste
# ==============================================================================
print("======================================================================")
print("AFIRMACION 6: Altarani de noche y el régimen de giro al oeste")
print("======================================================================")
alt_d1 = P["d1"]["Altarani"]
alt_ws = P["ws"]["Altarani"]
alt_sd1 = P["sd1"]["Altarani"]

for ws_thr in [0.5, 1.0]:
    ok_n = is_night & (alt_ws >= ws_thr) & alt_d1.notna()
    in_90_180 = (alt_d1[ok_n] >= 90) & (alt_d1[ok_n] <= 180)
    print(f"Altarani noche (ws >= {ws_thr}): N={ok_n.sum()}, en 90-180°: {in_90_180.mean()*100:.1f}%, "
          f"en 270-360° (NO): {((alt_d1[ok_n]>=270)&(alt_d1[ok_n]<=360)).mean()*100:.1f}%")

# ¿Cómo definió el analista "cuando la red gira al oeste de noche (~104 h)"?
# Probemos distintas definiciones de "la red gira al oeste de noche"
clean_nbs = ["Alto_Quellaveco", "Minas_Sur", "Papujune", "Tala-1", "Tala_Legal", "Charaque", "Chancado_primario", "Cerro_Salviani"]
u_nbs = np.sin(np.deg2rad(P["dir"][clean_nbs]))
w_nbs = np.cos(np.deg2rad(P["dir"][clean_nbs]))
net_dir = pd.Series(np.rad2deg(np.arctan2(u_nbs.mean(1), w_nbs.mean(1))) % 360, index=idx)

for label, cond_net in [
    ("net_dir en 225-315° y ws_Alt>1", is_night & (alt_ws > 1) & alt_d1.notna() & (ang(net_dir, 270) <= 45)),
    ("net_dir en 225-315° y ws_Alt>=0.5", is_night & (alt_ws >= 0.5) & alt_d1.notna() & (ang(net_dir, 270) <= 45)),
    ("Tala-1 en 225-315° y ws_Alt>1", is_night & (alt_ws > 1) & alt_d1.notna() & (ang(P["d1"]["Tala-1"], 270) <= 45)),
    ("Alto_Quellaveco en 225-315° (pre-sep15) y ws_Alt>1", is_night & (idx < "2026-09-15") & (alt_ws > 1) & alt_d1.notna() & (ang(P["d1"]["Alto_Quellaveco"], 270) <= 45)),
]:
    sub = alt_d1[cond_net]
    se = ((sub >= 90) & (sub <= 180)).mean() * 100
    nw = ((sub >= 270) & (sub <= 360)).mean() * 100
    print(f"  Condición [{label}]: N={len(sub)} h -> SE(90-180°): {se:.1f}%, NO(270-360°): {nw:.1f}%")

# Analicemos en detalle esas horas en que la red gira al oeste de noche: ¿qué separa que Altarani vaya a SE vs NO?
cond_west = is_night & (alt_ws > 1) & alt_d1.notna() & (ang(net_dir, 270) <= 45)
df_w = pd.DataFrame({
    "alt_d1": alt_d1[cond_west],
    "alt_ws": alt_ws[cond_west],
    "alt_sd1": alt_sd1[cond_west],
    "hr": idx[cond_west].hour,
    "aq_ws": P["ws"]["Alto_Quellaveco"].where(idx < "2026-09-15")[cond_west],
    "aq_d1": P["d1"]["Alto_Quellaveco"].where(idx < "2026-09-15")[cond_west],
    "mqg_ws": P["ws"]["Sarallenque_MQG-15-02"][cond_west],
    "mqg_dir": P["dir"]["Sarallenque_MQG-15-02"][cond_west],
    "dT_AQ_Alt": (P["tc"]["Alto_Quellaveco"] - P["tc"]["Altarani"])[cond_west],
    "alt_rh": P["rh"]["Altarani"][cond_west],
    "alt_prev1h_nw": ((alt_d1.shift(1) >= 250) & (alt_d1.shift(1) <= 360))[cond_west]
})
df_w["regimen"] = np.where((df_w.alt_d1 >= 90) & (df_w.alt_d1 <= 180), "SE (drenaje)",
                  np.where((df_w.alt_d1 >= 270) & (df_w.alt_d1 <= 360), "NO (acoplado)", "Otro"))
print("\nComparación física entre SE y NO en Altarani cuando la red gira al oeste de noche:")
print(df_w.groupby("regimen")[["alt_ws", "alt_sd1", "aq_ws", "mqg_ws", "dT_AQ_Alt", "alt_rh"]].agg(["count", "mean", "median"]).to_string())

print("\nReparto SE vs NO según hora de la noche (22-23h = cola vespertina vs 00-06h = madrugada):")
df_w["tramo_noche"] = np.where(df_w.hr >= 22, "22-23h", "00-06h")
print(pd.crosstab(df_w["tramo_noche"], df_w["regimen"], normalize="index").round(3) * 100)
print(pd.crosstab(df_w["tramo_noche"], df_w["regimen"]))

print("\nReparto SE vs NO según si Sarallenque_MQG-15-02 (misma cuenca, arriba) también viene del O-NO (240-360°):")
df_w["mqg_west"] = (df_w.mqg_dir >= 240) & (df_w.mqg_dir <= 360)
print(pd.crosstab(df_w["mqg_west"], df_w["regimen"], normalize="index").round(3) * 100)

print("\nReparto SE vs NO según velocidad propia de Altarani (ws > 2.2 m/s vs <= 2.2 m/s) y dT vertical:")
df_w["fast_or_unstable"] = (df_w.alt_ws > 2.2) | (df_w.dT_AQ_Alt < -3.2) | (df_w.hr == 22)
print(pd.crosstab(df_w["fast_or_unstable"], df_w["regimen"], normalize="index").round(3) * 100)
acc_rule = ((df_w.fast_or_unstable & (df_w.regimen == "NO (acoplado)")) | (~df_w.fast_or_unstable & (df_w.regimen == "SE (drenaje)"))).mean()
print(f"Exactitud de regla física simple sobre SE vs NO: {acc_rule*100:.1f}%")

# ==============================================================================
# AFIRMACION 7: Cortadera de noche (abanico 0° a 135°)
# ==============================================================================
print("\n======================================================================")
print("AFIRMACION 7: Cortadera de noche (abanico 0° a 135°)")
print("======================================================================")
cort_ok = is_night & (idx < "2026-09-13 11:00") & (P["ws"]["Cortadera"] > 1) & P["d1"]["Cortadera"].notna()
c_d1 = P["d1"]["Cortadera"][cort_ok]
c_ws = P["ws"]["Cortadera"][cort_ok]
c_sd1 = P["sd1"]["Cortadera"][cort_ok]
print(f"Cortadera noche (pre 2026-09-13, ws>1): N={len(c_d1)} h")
for a_sec, b_sec, lbl in [(0, 45, "0-45° (N-NE)"), (45, 90, "45-90° (NE-E)"), (90, 135, "90-135° (E-SE)"),
                          (135, 225, "135-225° (S)"), (225, 315, "225-315° (O)"), (315, 360, "315-360° (NO-N)")]:
    m_sec = (c_d1 >= a_sec) & (c_d1 < b_sec)
    print(f"  Sector {lbl:16s}: {m_sec.mean()*100:5.1f}% (n={m_sec.sum():4d}) | ws_mean={c_ws[m_sec].mean():.2f}, sd1_mean={c_sd1[m_sec].mean():.1f}°")

# ¿Qué predice si Cortadera de noche está en el Norte (315-45°) vs Este-Sureste (70-150°)?
df_cort = pd.DataFrame({
    "d1": c_d1,
    "ws": c_ws,
    "sd1": c_sd1,
    "mes": idx[cort_ok].strftime("%Y-%m"),
    "hr": idx[cort_ok].hour,
    "tc": P["tc"]["Cortadera"][cort_ok],
    "rh": P["rh"]["Cortadera"][cort_ok],
    "dT_Apa_Cort": (P["tc"]["Apacheta"] - P["tc"]["Cortadera"])[cort_ok],
    "dT_Sal_Cort": (P["tc"]["Cerro_Salviani"] - P["tc"]["Cortadera"])[cort_ok],
    "apa_dir": P["dir"]["Apacheta"][cort_ok],
    "apa_ws": P["ws"]["Apacheta"][cort_ok],
    "sal_dir": P["dir"]["Cerro_Salviani"][cort_ok],
    "sal_ws": P["ws"]["Cerro_Salviani"][cort_ok],
    "cal_dir": P["dir"]["Calientes1"][cort_ok],
    "cal_ws": P["ws"]["Calientes1"][cort_ok],
    "tala_d1": P["d1"]["Tala-1"][cort_ok],
})
df_cort["is_north"] = ang(df_cort.d1, 0) <= 45
print("\nCortadera noche: % en sector Norte (|D1|<=45°) y dirección circular media por MES:")
def cmean_deg(s):
    return np.rad2deg(np.arctan2(np.sin(np.deg2rad(s)).mean(), np.cos(np.deg2rad(s)).mean())) % 360
print(df_cort.groupby("mes").agg(
    n=("d1", "size"),
    pct_norte=("is_north", lambda x: round(x.mean()*100, 1)),
    dir_media=("d1", lambda x: round(cmean_deg(x), 0)),
    ws_media=("ws", lambda x: round(x.mean(), 2)),
    sd1_media=("sd1", lambda x: round(x.mean(), 1))
).to_string())

print("\nCortadera noche: % en sector Norte por HORA DE LA NOCHE:")
print(df_cort.groupby("hr").agg(
    n=("d1", "size"),
    pct_norte=("is_north", lambda x: round(x.mean()*100, 1)),
    dir_media=("d1", lambda x: round(cmean_deg(x), 0)),
    ws_media=("ws", lambda x: round(x.mean(), 2))
).to_string())

print("\nCortadera noche: comparación Norte (|D1|<=45°) vs SE (75-150°):")
df_cort["grupo_dir"] = np.where(df_cort.is_north, "Norte (<=45°)",
                       np.where((df_cort.d1 >= 75) & (df_cort.d1 <= 150), "Este-SE (75-150°)", "Intermedio"))
print(df_cort.groupby("grupo_dir")[["ws", "sd1", "tc", "rh", "dT_Apa_Cort", "dT_Sal_Cort", "apa_ws", "sal_ws", "cal_ws"]].mean().round(2).to_string())

# ==============================================================================
# AFIRMACION 8: Camp_Quellaveco de noche
# ==============================================================================
print("\n======================================================================")
print("AFIRMACION 8: Camp_Quellaveco de noche (¿sensor parado o flujo con ws>1?)")
print("======================================================================")
camp_n = is_night & P["ws"]["Camp_Quellaveco"].notna() & P["d1"]["Camp_Quellaveco"].notna()
print(f"Total horas nocturnas Camp_Quellaveco: {camp_n.sum()}")
print(f"  Calmas (<0.5 m/s): {(P['ws']['Camp_Quellaveco'][camp_n] < 0.5).mean()*100:.1f}%")
print(f"  Entre 0.5 y 1.0 m/s: {((P['ws']['Camp_Quellaveco'][camp_n] >= 0.5) & (P['ws']['Camp_Quellaveco'][camp_n] <= 1.0)).mean()*100:.1f}%")
print(f"  > 1.0 m/s (las que entran al test de diag.py/calib.py): {(P['ws']['Camp_Quellaveco'][camp_n] > 1.0).mean()*100:.1f}% (n={(P['ws']['Camp_Quellaveco'][camp_n] > 1.0).sum()})")

# Comparar antes y después del 2026-09-10 en horas con ws > 1.0 m/s
for per_lbl, m_per in [("Antes de 2026-09-10 (nov25-sep09)", idx < "2026-09-10"),
                       ("Después de 2026-09-10 (sep10-nov03)", idx >= "2026-09-10")]:
    m_all = camp_n & m_per
    m_gt1 = m_all & (P["ws"]["Camp_Quellaveco"] > 1.0)
    dif_chan = ang(P["d1"]["Camp_Quellaveco"][m_gt1], P["dir"]["Chancado_primario"][m_gt1])
    dif_tala = ang(P["d1"]["Camp_Quellaveco"][m_gt1], P["d1"]["Tala-1"][m_gt1])
    print(f"  {per_lbl}:")
    print(f"    Todas las noches (n={m_all.sum()}): % ws==0: {(P['ws']['Camp_Quellaveco'][m_all]==0).mean()*100:.1f}%, % <0.5: {(P['ws']['Camp_Quellaveco'][m_all]<0.5).mean()*100:.1f}%")
    print(f"    Noches con ws>1.0 (n={m_gt1.sum()}): ws_mean={P['ws']['Camp_Quellaveco'][m_gt1].mean():.2f}, sd1_mean={P['sd1']['Camp_Quellaveco'][m_gt1].mean():.1f}°, "
          f"|Camp-Chancado| mean={dif_chan.mean():.1f}° (med={dif_chan.median():.1f}°), |Camp-Tala1| mean={dif_tala.mean():.1f}°")

# Distribución direccional de Camp_Quellaveco de noche cuando ws > 1.0 m/s
c_gt1 = P["d1"]["Camp_Quellaveco"][camp_n & (P["ws"]["Camp_Quellaveco"] > 1.0)]
print("  Sectores de Camp_Quellaveco de noche cuando ws > 1.0 m/s:")
for a_s, b_s, l_s in [(0, 90, "0-90° (NE)"), (90, 180, "90-180° (SE)"), (180, 270, "180-270° (SO)"), (270, 360, "270-360° (NO)")]:
    print(f"    {l_s}: {((c_gt1 >= a_s) & (c_gt1 < b_s)).mean()*100:.1f}% (n={((c_gt1 >= a_s) & (c_gt1 < b_s)).sum()})")

# ==============================================================================
# AFIRMACION 9: Giros de Cortadera (2026-09-13) y Alto_Quellaveco (2026-09-15) + Alto_Tala
# ==============================================================================
print("\n======================================================================")
print("AFIRMACION 9: Análisis de los cambios en Cortadera, Alto_Quellaveco y Alto_Tala")
print("======================================================================")
# 1) Revisar intervenciones_meteorologia.csv en agosto-septiembre 2026
df_int = pd.read_csv(INT_FILE)
print("Intervenciones registradas desde 2026-08-01 en Cortadera, Alto_Quellaveco, Alto_Tala, Camp_Quellaveco, Sarallenque:")
print(df_int[df_int.iloc[:, 0].astype(str).str.contains("Cortadera|Quellaveco|Tala|Sarallenque", case=False, na=False) |
             df_int.apply(lambda r: any("2026-08" in str(v) or "2026-09" in str(v) for v in r), axis=1)].tail(35).to_string())

# 2) Prueba F de WIND_REVIEW.md para Cortadera (cambio 2026-09-13 11:00) y Alto_Quellaveco (cambio 2026-09-15 11:00) y Alto_Tala (2026-08-18 a 2026-09-23)
def test_shift(st_name, ref_name, t_before_start, t_before_end, t_after_start, t_after_end):
    print(f"\n--- Diagnóstico WIND_REVIEW (E y F): {st_name} (control: {ref_name}) ---")
    print(f"  Antes: {t_before_start} .. {t_before_end} | Después: {t_after_start} .. {t_after_end}")
    d_st = P["dir"][st_name]
    w_st = P["ws"][st_name]
    sd_st = P["sd1"][st_name] if st_name in P["sd1"] else pd.Series(np.nan, index=idx)
    d_ref = P["dir"][ref_name]
    w_ref = P["ws"][ref_name]
    
    mb = (idx >= t_before_start) & (idx < t_before_end) & (w_st >= 0.5) & d_st.notna()
    ma = (idx >= t_after_start) & (idx < t_after_end) & (w_st >= 0.5) & d_st.notna()
    
    for fr_name, fr_mask in [("Día (10-17h)", is_day), ("Noche (22-06h)", is_night), ("Todas (0-23h)", pd.Series(True, index=idx))]:
        b_s = d_st[mb & fr_mask]; a_s = d_st[ma & fr_mask]
        b_r = d_ref[mb & fr_mask & (w_ref >= 0.5)]; a_r = d_ref[ma & fr_mask & (w_ref >= 0.5)]
        dir_b = cmean_deg(b_s); dir_a = cmean_deg(a_s)
        ref_b = cmean_deg(b_r); ref_a = cmean_deg(a_r)
        # Correlación circular de histogramas girados cada 1°
        hb, _ = np.histogram(b_s, bins=np.arange(0, 361, 5), density=True)
        ha, _ = np.histogram(a_s, bins=np.arange(0, 361, 5), density=True)
        cos_0 = np.dot(hb, ha) / (np.linalg.norm(hb) * np.linalg.norm(ha) + 1e-12)
        best_rot, best_cos = 0, -1
        for k in range(-36, 36): # cada 5 grados
            ha_rot = np.roll(ha, -k) # si después sumó k*5 grados, para volver a antes rolamos -k
            c_val = np.dot(hb, ha_rot) / (np.linalg.norm(hb) * np.linalg.norm(ha_rot) + 1e-12)
            if c_val > best_cos:
                best_cos = c_val; best_rot = k * 5
        print(f"  {fr_name:15s}: Antes={dir_b:5.1f}° (n={len(b_s):3d}, ws={w_st[mb&fr_mask].mean():.2f}, sd1={sd_st[mb&fr_mask].mean():.1f}°) -> "
              f"Después={dir_a:5.1f}° (n={len(a_s):3d}, ws={w_st[ma&fr_mask].mean():.2f}, sd1={sd_st[ma&fr_mask].mean():.1f}°) | "
              f"Δ={sdiff(dir_a, dir_b):+6.1f}° | Giro hist={best_rot:+4d}° (cos {cos_0:.2f}->{best_cos:.2f}) | "
              f"Control {ref_name}: {ref_b:.0f}°->{ref_a:.0f}° (Δ={sdiff(ref_a, ref_b):+4.0f}°)")

    # Diferencia por bloques de 3 horas
    print("  Diferencia por bloque horario (Después - Antes):")
    blk_str = []
    for h0 in range(0, 24, 3):
        mh = (hr >= h0) & (hr < h0 + 3)
        db = cmean_deg(d_st[mb & mh]); da = cmean_deg(d_st[ma & mh])
        blk_str.append(f"{h0:02d}-{h0+2:02d}h:{db:3.0f}°->{da:3.0f}°({sdiff(da,db):+4.0f}°)")
    print("   ", " | ".join(blk_str[:4]))
    print("   ", " | ".join(blk_str[4:]))

test_shift("Cortadera", "Calientes1", "2026-07-15", "2026-09-13 10:00", "2026-09-13 12:00", "2026-11-03")
test_shift("Alto_Quellaveco", "Minas_Sur", "2026-07-15", "2026-09-15 10:00", "2026-09-15 12:00", "2026-11-03")
test_shift("Alto_Tala", "Tala-1", "2026-07-01", "2026-08-18 04:00", "2026-08-18 06:00", "2026-09-23 14:00")
test_shift("Alto_Tala", "Tala-1", "2026-07-01", "2026-08-18 04:00", "2026-09-23 16:00", "2026-11-03")

# 3) Comparación con años anteriores (2020-2026) en Octubre para Altarani, Cortadera y Alto_Quellaveco
print("\n--- Comparación histórica multianual (meses de Octubre, 2020-2026) ---")
df_oct = df_hist[df_hist.mo == 10].copy()
df_oct["dir"] = df_oct.d1.fillna(df_oct.a)
df_oct["fr"] = np.where((df_oct.hr >= 10) & (df_oct.hr <= 17), "Día",
               np.where((df_oct.hr >= 22) | (df_oct.hr <= 6), "Noche", "Trans"))
df_oct = df_oct[df_oct.fr.isin(["Día", "Noche"])]
for st_h in ["Altarani", "Cortadera", "Alto_Quellaveco", "Camp_Quellaveco"]:
    sub_h = df_oct[df_oct.st == st_h]
    piv_h = sub_h.groupby(["yr", "fr"]).agg(
        n=("dir", "size"),
        dir_m=("dir", lambda x: round(cmean_deg(x), 0)),
        ws_m=("ws", lambda x: round(x.mean(), 2)),
        sd1_m=("sd1", lambda x: round(x.mean(), 1))
    ).unstack("fr")
    print(f"\nHistórico Octubre - {st_h}:")
    print(piv_h.to_string())
