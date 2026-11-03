"""Consenso por pares: cada vecina calibrada por separado (sector × franja) y combinada por su acierto en entrenamiento.
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
week = ((idx - idx[0]) // pd.Timedelta(days=7)) % 2
hr = idx.hour; band = np.where((hr >= 10) & (hr <= 17), 0, np.where((hr >= 22) | (hr <= 6), 1, 2))
D = P["dir"]
def calibrated(src, truth, tr):
    """Predicción de la verdad desde una dirección `src`, con desfase aprendido por sector de src × franja."""
    sec = (((src + 11.25) % 360) // 22.5)
    key = pd.Series(sec.astype("Int64").astype(str) + "_" + band.astype(str), index=idx)
    ok = tr & src.notna()
    z = np.exp(1j * np.deg2rad(sdiff(truth[ok], src[ok]))); g = z.groupby(key[ok]).mean()
    off = pd.Series(np.rad2deg(np.angle(g.to_numpy())), index=g.index)
    return (src + key.map(off)) % 360
rows = []
for t in ["Altarani","Alto_Quellaveco","Camp_Quellaveco","Cortadera","Minas_Sur","Papujune","Tala-1","Tala_Legal"]:
    truth = P["d1"][t]; base = (P["ws"][t] > 1) & truth.notna() & P["a"][t].notna()
    tr, te = base & (week == 0), base & (week == 1)
    nbs = [s for s in D.columns if s != t]
    U = pd.Series(0.0, index=idx); W = U.copy(); S_ = U.copy(); info = []
    for s in nbs:
        pred = calibrated(D[s], truth, tr)
        e_tr = ang(pred[tr], truth[tr]).mean()
        if not np.isfinite(e_tr): continue
        wgt = 1 / max(e_tr, 5) ** 2
        info.append((s, e_tr))
        m = pred.notna()
        U[m] += wgt * np.sin(np.deg2rad(pred[m])); W[m] += wgt * np.cos(np.deg2rad(pred[m])); S_[m] += wgt
    comb = (np.rad2deg(np.arctan2(U, W)) % 360).where(S_ > 0)
    best = sorted(info, key=lambda x: x[1])[:3]
    n = ang(truth, 0) <= 45
    e = ang(comb, truth); eo = ang(P["a"][t], truth)
    rows.append(dict(estacion=t, propio_A=f"{eo[te].mean():.1f} / {eo[te & n].mean():.1f}",
                     por_pares=f"{e[te].mean():.1f} / {e[te & n].mean():.1f}",
                     mejores_vecinas=", ".join(f"{s} {v:.0f}°" for s, v in best)))
print("Error medio en semanas de prueba, todas / norte (grados)\n"); print(pd.DataFrame(rows).to_string(index=False))
