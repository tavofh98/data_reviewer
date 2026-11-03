"""¿Están alineados los relojes? Desfase (h) que maximiza la coincidencia del ciclo diario de dirección con Papujune."""
import warnings; warnings.filterwarnings("ignore")
import duckdb, numpy as np, pandas as pd
con = duckdb.connect(r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db", read_only=True)
df = con.execute("""select estacion_id st, timestamp ts, coalesce(WindDir_D1_WVT, WindDir_Avg) d, WS_ms_Avg ws, AirTC_Avg t
 from meteorologia where timestamp >= '2025-11-01' and WindDir_Avg is not null""").df()
D = df.pivot(index="ts", columns="st", values="d"); T = df.pivot(index="ts", columns="st", values="t")
ref = "Papujune"
rows = []
for s in D.columns:
    best = {}
    for lag in range(-6, 7):
        sh = D[s].shift(lag)
        c = np.cos(np.deg2rad(sh - D[ref])).mean()
        tc = T[s].shift(lag).corr(T[ref]) if s in T and T[s].notna().any() else np.nan
        best[lag] = (c, tc)
    ld = max(best, key=lambda k: best[k][0]); lt = max(best, key=lambda k: -np.inf if np.isnan(best[k][1]) else best[k][1])
    rows.append(dict(estacion=s, desfase_dir_h=ld, cos_en_0=round(best[0][0], 2), cos_mejor=round(best[ld][0], 2), desfase_temp_h=lt))
print(pd.DataFrame(rows).to_string(index=False))
