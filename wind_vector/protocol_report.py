"""Métricas del protocolo: selección en validación, resultado en prueba e intervalos de confianza pareados.

Lee output/protocol_hourly.csv.gz y output/protocol_sigma.csv (de wind_vector.protocol).
  1. Error de σ (MAE frente a SD1) por modelo y alcance, en validación.
  2. Validación: error horario por modelo (alcance|σ|clasificador), media macro de las 6 estaciones (cada estación
     pesa igual), para todas las horas, norte (real ≤ 45°) y sur (90–270°, donde V1 ya acierta).
     Se elige, para cada alcance, el modelo de menor media macro en todas las horas.
  3. Prueba: los elegidos, V1 y las referencias, por estación.
  4. Diferencias pareadas en prueba con IC 95 % por bootstrap de días (2000 remuestreos).
Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.protocol_report
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from wind_vector.analyze import OUT, to_md
from wind_vector.north_sector import abs_diff

FIXED = ["station", "TIMESTAMP", "fold", "truth"]
SCOPES = ("estación", "global", "loso")
RNG = np.random.default_rng(0)


def strata(t: pd.Series) -> dict[str, pd.Series]:
    dn = abs_diff(t, 0.0)
    return {"todas": dn >= 0, "norte": dn <= 45, "sur": dn >= 90}


def per_station(h: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    rows = []
    for st, g in h.groupby("station", sort=False):
        for sname, sel in strata(g["truth"]).items():
            for m in methods:
                e = abs_diff(g.loc[sel, m], g.loc[sel, "truth"])
                rows.append({"station": st, "estrato": sname, "método": m, "n": int(sel.sum()), "media": np.mean(e),
                             "mediana": np.median(e), "p95": np.quantile(e, 0.95), "% > 30°": 100 * np.mean(e > 30)})
    return pd.DataFrame(rows)


def bootstrap_diff(g: pd.DataFrame, a: str, b: str, n_boot: int = 2000) -> tuple[float, float, float]:
    """Media de (error a − error b) y su IC 95 % remuestreando días completos."""
    d = abs_diff(g[a], g["truth"]) - abs_diff(g[b], g["truth"])
    day = pd.to_datetime(g["TIMESTAMP"]).dt.floor("D").to_numpy()
    agg = pd.DataFrame({"day": day, "d": d}).groupby("day")["d"].agg(["sum", "count"])
    s, c = agg["sum"].to_numpy(), agg["count"].to_numpy()
    idx = RNG.integers(0, len(s), size=(n_boot, len(s)))
    boots = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    return s.sum() / c.sum(), *np.quantile(boots, [0.025, 0.975])


def main() -> None:
    h = pd.read_csv(OUT / "protocol_hourly.csv.gz")
    models = [c for c in h.columns if c not in FIXED]
    sig = pd.read_csv(OUT / "protocol_sigma.csv")

    print("## 1. Error de σ en validación (MAE frente a SD1, grados; media de las estaciones)\n")
    sv = sig[sig["split"] == "val"].pivot_table(index="sigma", columns="alcance", values="MAE", aggfunc="mean")
    print(to_md(sv.reset_index()))
    print("\nPor estación (alcance loso):\n")
    print(to_md(sig[(sig["split"] == "val") & (sig["alcance"] == "loso")]
                .pivot_table(index="station", columns="sigma", values="MAE").reset_index()))

    val = h[h["fold"] == 3]
    ps = per_station(val, models)
    macro = ps.pivot_table(index="método", columns="estrato", values="media", aggfunc="mean")
    worst = ps[ps["estrato"] == "todas"].groupby("método")["media"].max().rename("peor estación")
    table = macro.join(worst)[["todas", "norte", "sur", "peor estación"]].sort_values("todas")
    print("\n## 2. Validación: error horario medio (media macro de 6 estaciones, grados)\n")
    print(to_md(table.reset_index()))

    chosen = {}
    for sc in SCOPES:
        cand = [m for m in table.index if m.startswith(sc + "|") and not m.endswith("|perfecta")]
        chosen[sc] = min(cand, key=lambda m: table.loc[m, "todas"])
        lr = [m for m in cand if "|lr" in m]
        chosen[sc + " (mejor lr)"] = min(lr, key=lambda m: table.loc[m, "todas"])
    print("\nElegidos en validación:", chosen)

    test = h[h["fold"] == 4]
    best_sigma = chosen["global"].split("|")[1]
    refs = ["V1", "oracle", f"global|{best_sigma}|perfecta"]
    methods = refs + list(dict.fromkeys(chosen.values()))
    pt = per_station(test, methods)
    print("\n## 3. Prueba: error horario por estación (grados)\n")
    for sname in ("todas", "norte", "sur"):
        print(f"\n### {sname}\n")
        w = pt[pt["estrato"] == sname].pivot_table(index="station", columns="método", values="media")[methods]
        w.loc["media macro"] = w.mean()
        print(to_md(w.reset_index()))
    print("\n### % horas norte con error > 30°\n")
    w = pt[pt["estrato"] == "norte"].pivot_table(index="station", columns="método", values="% > 30°")[methods]
    print(to_md(w.reset_index()))

    print("\n## 4. Diferencias pareadas en prueba (a − b, grados; IC 95 % por días)\n")
    # Entre alcances, clasificadores o puertas se compara cambiando una sola cosa a la vez.
    rest = "|".join(chosen["global"].split("|")[2:])          # p. ej. hgb2|t0.1|ctx
    other_sigma = next(s for s in ("gust_ws", "hgb") if s != best_sigma)
    pairs = [(chosen["loso"], "V1"), (chosen["global"], "V1"),
             (f"loso|{best_sigma}|{rest}", f"global|{best_sigma}|{rest}"),
             (f"estación|{best_sigma}|{rest}", f"global|{best_sigma}|{rest}"),
             (f"loso|{best_sigma}|{rest.replace('hgb2', 'lr2')}", f"loso|{best_sigma}|{rest}"),
             (f"loso|{other_sigma}|{rest}", f"loso|{best_sigma}|{rest}"),
             (f"loso|{best_sigma}|hgb2|t0.0", f"loso|{best_sigma}|{rest}")]
    rows = []
    for a, b in dict.fromkeys(pairs):
        if a == b or a not in h or b not in h:   # p. ej. una σ que esta ejecución no calculó
            continue
        for st, g in test.groupby("station", sort=False):
            for sname, sel in strata(g["truth"]).items():
                if sname == "norte" or sname == "todas" or (sname == "sur" and b == "V1"):
                    m, lo, hi = bootstrap_diff(g[sel], a, b)
                    rows.append({"a": a, "b": b, "station": st, "estrato": sname, "Δ media": m, "IC 2.5 %": lo,
                                 "IC 97.5 %": hi, "signif.": "sí" if hi < 0 or lo > 0 else "no"})
    print(to_md(pd.DataFrame(rows)))


if __name__ == "__main__":
    main()
