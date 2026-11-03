"""Consenso calibrado por estación: desfase angular aprendido por sector del consenso (16) y franja (día/noche/transición).
Entrenamiento con semanas pares, prueba con semanas impares."""
import warnings; warnings.filterwarnings("ignore")
import re, duckdb, numpy as np, pandas as pd
src = open("met_viewer/stations.py", encoding="utf-8").read()
XY = {m[0]: (float(m[1]), float(m[2])) for m in re.findall(r'"([^"]+)":\s+Station\((\d+), (\d+)', src)}
con = duckdb.connect("../../database_duck/anglo_ambiental.db", read_only=True)
df = con.execute("select estacion_id st, timestamp ts, WindDir_D1_WVT d1, WindDir_Avg a, WS_ms_Avg ws from meteorologia where timestamp>='2025-11-01' and WindDir_Avg is not null").df()
import sys
CLEAN = "--limpio" in sys.argv
if CLEAN:
    drop = {"Dique_pie_botadero", "Chalsos", "Mina_Norte", "Planta_Concentradora", "Ilo", "Huachunta", "Vizcachas", "Titire"}
    df = df[df.st.isin(XY) & ~df.st.isin(drop)]
    df = df[~((df.st == "Sarallenque") & (df.ts < "2026-09-25 21:00"))]
    df = df[df.ws >= 0.5]   # regla de calma en toda la red (WIND_REVIEW §1)
    # Tramos fuera de patrón (contraste del agente, verificados Cortadera y Alto_Quellaveco)
    for st, a, b in [("Alto_Quellaveco", "2026-09-15 11:00", "2099"), ("Cortadera", "2026-09-13 11:00", "2099"),
                     ("Alto_Tala", "2026-08-18 05:00", "2026-09-23 15:00"),
                     ("Charaque", "2026-01-14 14:00", "2026-01-15 12:00"), ("Charaque", "2026-01-28 14:00", "2026-01-29 07:00"),
                     ("Sarallenque_MQG-15-02", "2026-02-16 14:00", "2026-02-17 09:00")]:
        df = df[~((df.st == st) & (df.ts >= a) & (df.ts <= b))]
else:
    df = df[df.st.isin(XY) & (df.st != "Dique_pie_botadero")]
df["dir"] = df.d1.fillna(df.a)
P = {c: df.pivot(index="ts", columns="st", values=c) for c in ("dir", "ws", "d1", "a")}
u = P["ws"] * np.sin(np.deg2rad(P["dir"])); w = P["ws"] * np.cos(np.deg2rad(P["dir"]))
ang = lambda a, b: np.minimum(np.abs((a - b) % 360), 360 - np.abs((a - b) % 360))
sdiff = lambda a, b: (a - b + 180) % 360 - 180
idx = P["dir"].index; week = ((idx - idx[0]) // pd.Timedelta(days=7)) % 2
hr = idx.hour; band = np.where((hr >= 10) & (hr <= 17), 0, np.where((hr >= 22) | (hr <= 6), 1, 2))
rows = []
for t in [s for s in P["d1"].columns if P["d1"][s].notna().sum() > 1000 and s not in ("Huachunta", "Vizcachas")]:
    nb = [s for s in P["dir"].columns if s != t]
    p = pd.Series({s: 1 / (np.hypot(XY[t][0] - XY[s][0], XY[t][1] - XY[s][1]) / 1000) ** 2 for s in nb})
    m = u[nb].notna()
    U = (u[nb].fillna(0) * p).sum(axis=1) / (m * p).sum(axis=1); W = (w[nb].fillna(0) * p).sum(axis=1) / (m * p).sum(axis=1)
    c = pd.Series(np.rad2deg(np.arctan2(U, W)) % 360, index=idx)
    truth = P["d1"][t]; ok = (P["ws"][t] > 1) & truth.notna() & c.notna() & P["a"][t].notna()
    sec = (((c + 11.25) % 360) // 22.5).astype(int)
    key = pd.Series(sec.astype(str) + "_" + band.astype(str), index=idx)
    off = sdiff(truth, c)
    tr = ok & (week == 0); te = ok & (week == 1)
    # desfase circular medio por clave (entrenamiento)
    z = np.exp(1j * np.deg2rad(off[tr])); g = z.groupby(key[tr]).mean(); med = pd.Series(np.rad2deg(np.angle(g.to_numpy())), index=g.index)
    cal = (c + key.map(med).fillna(0)) % 360
    n = ang(truth, 0) <= 45
    e0, e1, eo = ang(c, truth), ang(cal, truth), ang(P["a"][t], truth)
    f = lambda e, mk: f"{e[te & mk].mean():.1f}"
    rows.append(dict(estacion=t, horas_prueba=int(te.sum()), propio_A=f(eo, n | ~n) + " / " + f(eo, n),
                     consenso=f(e0, n | ~n) + " / " + f(e0, n), consenso_calibrado=f(e1, n | ~n) + " / " + f(e1, n),
                     calibrado_mas_30=f"{100 * (e1[te] > 30).mean():.0f} %"))
print("Error medio en semanas de prueba, todas / norte (grados)\n"); print(pd.DataFrame(rows).to_string(index=False))
