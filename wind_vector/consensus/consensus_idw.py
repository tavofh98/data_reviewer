"""Consenso IDW con toda la red local como vecinas (D1 donde existe, si no WindDir_Avg)."""
import warnings; warnings.filterwarnings("ignore")
import sys, duckdb, numpy as np, pandas as pd
import re, types
# Coordenadas leídas del texto de stations.py (su import depende de anglo_reporte/matrices.py, ausente)
_src = open(r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc/met_viewer/stations.py", encoding="utf-8").read()
STATIONS = {m[0]: types.SimpleNamespace(easting=float(m[1]), northing=float(m[2]))
            for m in re.findall(r'"([^"]+)":\s+Station\((\d+), (\d+)', _src)}
FAR = set()
EXCL = {"Dique_pie_botadero"}   # indicación del usuario: objetivamente no sirve
TARGETS = ["Altarani","Alto_Quellaveco","Camp_Quellaveco","Cortadera","Minas_Sur","Papujune","Tala-1","Tala_Legal"]
con = duckdb.connect(r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db", read_only=True)
df = con.execute("""select estacion_id st, timestamp ts, WindDir_Avg A, WindDir_D1_WVT D1, WS_ms_Avg ws
 from meteorologia where timestamp >= '2025-11-01' and WindDir_Avg is not null""").df()
df["dir"] = df.D1.fillna(df.A)
P = {c: df.pivot(index="ts", columns="st", values=c) for c in ("A", "D1", "ws", "dir")}
local = [s for s in P["dir"].columns if s not in FAR | EXCL and s in STATIONS]
u = -P["ws"] * np.sin(np.deg2rad(P["dir"])); v = -P["ws"] * np.cos(np.deg2rad(P["dir"]))
ang = lambda a, b: np.minimum(np.abs((a - b) % 360), 360 - np.abs((a - b) % 360))
xy = lambda s: (STATIONS[s].easting, STATIONS[s].northing)
def consensus(t, pool, maxkm):
    d = pd.Series({n: np.hypot(*np.subtract(xy(t), xy(n))) / 1000 for n in pool if n != t})
    d = d[d <= maxkm]; w = 1 / d**2; nb = list(d.index)
    m = u[nb].notna()
    U = (u[nb].fillna(0) * w).sum(axis=1) / (m * w).sum(axis=1); V = (v[nb].fillna(0) * w).sum(axis=1) / (m * w).sum(axis=1)
    return np.rad2deg(np.arctan2(-U, -V)) % 360, len(nb)
rows = []
for t in TARGETS:
    ok = (P["ws"][t] > 1) & P["D1"][t].notna()
    truth = P["D1"][t][ok]; north = ang(truth, 0) <= 45
    r = {"estacion": t, "V0 propia": f"{ang(P['A'][t][ok], truth).mean():.1f} / {ang(P['A'][t][ok], truth)[north].mean():.1f}"}
    for label, pool, km in (("8 con D1", TARGETS, 99), ("red local", local, 99), ("red local ≤4 km", local, 4)):
        c, n = consensus(t, pool, km); e = ang(c[ok], truth)
        r[f"{label} (n)"] = f"{e.mean():.1f} / {e[north].mean():.1f} ({n})"
    rows.append(r)
print("Error medio, todas / norte (grados); entre paréntesis, número de vecinas\n")
print(pd.DataFrame(rows).to_string(index=False))
print("\nRed local:", len(local), "estaciones:", ", ".join(sorted(local)))
