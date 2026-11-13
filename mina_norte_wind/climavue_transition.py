"""Congruencia del viento de Mina_Norte antes y después del cambio WindSonic → ClimaVUE (2026-08-28).

La referencia no es una estación vecina tomada como patrón, sino la relación de Mina_Norte con cada
vecina en el tramo C (ClimaVUE): si el tramo B girado reproduce esa relación con Oeste 1, Charaque y
MQG-15-02 a la vez, el sesgo propio de cada vecina se cancela.

Mina_Norte: dirección media de vectores unitarios de 5 min (sin girar) + θ. Girar cada registro y
promediar es igual que girar la media, así que el barrido de θ no recalcula nada.
Vecinas: WindDir_Avg horario (Oeste 1 desde su .dat; Charaque y MQG desde la base cruda).

Ejecutar desde explorar_qaqc: uv run python mina_norte_wind/climavue_transition.py
"""
from __future__ import annotations

import pandas as pd

from common import DAY, MN_5MIN, NIGHT, OESTE1_DAT, WD, WS, angle_diff, hourly_from_5min, load_station, read_toa5

WINDOWS = {   # (B antes, C después), mismos días a cada lado; fuera 26–27/08 (cable cortado, sensor retirado)
    "25 días": (("2026-08-01", "2026-08-26 00:00"), ("2026-08-28 01:00", "2026-09-22 00:00")),
    "12 días": (("2026-08-14", "2026-08-26 00:00"), ("2026-08-28 01:00", "2026-09-09 00:00")),
}
ANGLES = range(30, 81, 1)
PERIODS = (("día", DAY), ("noche", NIGHT))


def neighbors() -> dict[str, pd.DataFrame]:
    start, end = pd.Timestamp("2025-11-25"), pd.Timestamp("2026-11-13")
    return {"Oeste 1": read_toa5(OESTE1_DAT)[[WS, WD]],
            "Charaque": load_station("Charaque", start, end)[[WS, WD]],
            "MQG": load_station("Sarallenque_MQG-15-02", start, end)[[WS, WD]]}


def offset(mn: pd.DataFrame, ref: pd.DataFrame, hours, theta: float = 0.0) -> tuple[float, float, int]:
    """Mediana, IQR y horas de (Mina_Norte + θ) − vecina, ambas ≥ 1 m/s."""
    x = mn.join(ref.add_suffix("_r"), how="inner").dropna()
    x = x[x.index.hour.isin(hours) & (x[WS] >= 1) & (x[f"{WS}_r"] >= 1)]
    d = angle_diff(x[WD] + theta, x[f"{WD}_r"])
    return d.median(), d.quantile(.75) - d.quantile(.25), len(d)


def main() -> None:
    mn = hourly_from_5min(read_toa5(MN_5MIN), 0.0)[[WS, WD]]
    refs = neighbors()
    pd.set_option("display.width", 220)

    for name, (b, c) in WINDOWS.items():
        mn_b, mn_c = mn.loc[b[0]:b[1]], mn.loc[c[0]:c[1]]
        rows = []
        for ref_name, ref in refs.items():
            for period, hours in PERIODS:
                med_c, iqr_c, n_c = offset(mn_c, ref, hours)
                med_b, iqr_b, n_b = offset(mn_b, ref, hours)
                rows.append({"vecina": ref_name, "franja": period, "C ClimaVUE": med_c, "IQR C": iqr_c, "h C": n_c,
                             "B sin girar": med_b, "IQR B": iqr_b, "h B": n_b,
                             "giro que iguala B a C": angle_diff(med_c, med_b)})
        table = pd.DataFrame(rows)
        print(f"\n=== Ventana {name}: B {b[0]}→{b[1]} · C {c[0]}→{c[1]} ===")
        print(table.round(1).to_string(index=False))
        turn = table["giro que iguala B a C"]
        print("giro (mediana de las 6 combinaciones):", round(turn.median(), 1),
              "| solo día:", round(turn[table["franja"] == "día"].median(), 1),
              "| solo noche:", round(turn[table["franja"] == "noche"].median(), 1))
        speed_rows = []
        for ref_name, ref in refs.items():
            for period, hours in PERIODS:
                row = {"vecina": ref_name, "franja": period}
                for label, m in (("B", mn_b), ("C", mn_c)):
                    x = m.join(ref.add_suffix("_r"), how="inner").dropna()
                    x = x[x.index.hour.isin(hours)]
                    row[f"razón vel {label}"] = (x[WS] / x[f"{WS}_r"].where(x[f"{WS}_r"] >= 0.5)).median()
                    row[f"r vel {label}"] = x[WS].corr(x[f"{WS}_r"])
                speed_rows.append(row)
        print(pd.DataFrame(speed_rows).round(2).to_string(index=False))

    # Barrido de θ en todo el tramo B con 5 min: discrepancia con la relación de C, por franja
    mn_b = mn.loc["2026-01-11":"2026-08-26 00:00"]
    mn_c = mn.loc["2026-08-28 01:00":]
    target = {(r, p): offset(mn_c, ref, hours)[0] for r, ref in refs.items() for p, hours in PERIODS}
    rows = []
    for theta in ANGLES:
        err = {(r, p): angle_diff(offset(mn_b, ref, hours, theta)[0], target[(r, p)])
               for r, ref in refs.items() for p, hours in PERIODS}
        rows.append({"θ": theta, **{f"{p[:1]}-{r}": v for (r, p), v in err.items()},
                     "máx |día|": max(abs(v) for (r, p), v in err.items() if p == "día"),
                     "máx |noche|": max(abs(v) for (r, p), v in err.items() if p == "noche"),
                     "máx |todo|": max(abs(v) for v in err.values())})
    table = pd.DataFrame(rows)
    print("\n=== Barrido de θ en todo B (2026-01-11 → 2026-08-26) frente a la relación de C (desviación de la mediana) ===")
    print(table[table["θ"] % 5 == 0].round(1).to_string(index=False))
    for col in ("máx |día|", "máx |noche|", "máx |todo|"):
        k = table[col].idxmin()
        print(f"mínimo de {col}: θ = {table.loc[k, 'θ']} ({table.loc[k, col]:.1f}°)")


if __name__ == "__main__":
    main()
