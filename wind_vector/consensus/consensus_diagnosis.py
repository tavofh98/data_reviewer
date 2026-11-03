"""Diagnóstico del consenso por pares: error por franja, velocidad y mes (Altarani, Camp_Quellaveco, Cortadera, Tala-1).
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
def pair_consensus(t):
    truth = P["d1"][t]; base = (P["ws"][t] > 1) & truth.notna()
    tr = base & (week == 0)
    U = pd.Series(0.0, index=idx); W = U.copy(); S_ = U.copy()
    for s in [s for s in D.columns if s != t]:
        pred = calibrated(D[s], truth, tr); e_tr = ang(pred[tr], truth[tr]).mean()
        if not np.isfinite(e_tr): continue
        wgt = 1 / max(e_tr, 5) ** 2; m = pred.notna()
        U[m] += wgt * np.sin(np.deg2rad(pred[m])); W[m] += wgt * np.cos(np.deg2rad(pred[m])); S_[m] += wgt
    return (np.rad2deg(np.arctan2(U, W)) % 360).where(S_ > 0), base & (week == 1)
bname = pd.Series(np.select([band == 0, band == 1], ["día", "noche"], "transición"), index=idx)
out = []
for t in ["Altarani", "Camp_Quellaveco", "Cortadera", "Tala-1"]:
    c, te = pair_consensus(t); truth = P["d1"][t]; ws = P["ws"][t]
    e = ang(c, truth)[te]; n = (ang(truth, 0) <= 45)[te]
    d = pd.DataFrame({"e": e, "n": n, "b": bname[te], "ws": pd.cut(ws[te], [1, 2, 4, 99], labels=["1-2", "2-4", ">4"]),
                      "mes": idx[te].strftime("%Y-%m"), "dir": truth[te]})
    print(f"\n===== {t}: horas de prueba {len(d)}, norte {n.mean()*100:.0f} %")
    print("Por franja (error medio | % horas | % norte):")
    print(d.groupby("b").agg(err=("e", "mean"), horas=("e", "size"), norte=("n", "mean")).assign(
        horas=lambda x: (100 * x.horas / len(d)).round(0), norte=lambda x: (100 * x.norte).round(0), err=lambda x: x.err.round(1)).T.to_string())
    print("Por velocidad:"); print(d.groupby("ws").e.agg(["mean", "size"]).round(1).T.to_string())
    print("Norte por franja y velocidad (error medio, n):")
    print(d[d.n].groupby(["b", "ws"]).e.agg(["mean", "size"]).round(1).unstack(0).to_string())
    print("Por mes:"); print(d.groupby("mes").e.mean().round(0).to_frame().T.to_string())
