"""Incertidumbre de la dirección horaria según el sector del viento real, al acercarse al norte.

Lee las direcciones horarias de north_mixture.py y da el error circular (media, mediana, p95, % > 30°)
de V1 y del modelo por sector del viento real (Θ1 del logger):
  1. Mitades: 90–270° frente a 270–360° y 0–90°.
  2. Sectores que se estrechan hacia el norte: [x, 360) por el oeste y [0, x) por el este.
  3. Sector sur [x, 360 − x] que se amplía hacia el norte (x = 90, 80, …, 10) y su complemento (±x° del norte).

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.sector_error
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from wind_vector.analyze import OUT, to_md
from wind_vector.north_sector import abs_diff

WEST_EDGES = (270, 300, 315, 330, 340, 345, 350, 355)
EAST_EDGES = (90, 60, 45, 30, 20, 15, 10, 5)
SOUTH_EDGES = (90, 80, 70, 60, 50, 40, 30, 20, 10)


def stats(err: pd.DataFrame) -> pd.DataFrame:
    g = err.groupby(["sector", "station"], sort=False)
    out = pd.concat({
        "horas": g["V1"].size(),
        "V1 media": g["V1"].mean(), "modelo media": g["model"].mean(),
        "modelo mediana": g["model"].median(), "modelo p95": g["model"].quantile(0.95),
        "modelo % > 30°": g["model"].apply(lambda e: (e > 30).mean() * 100),
    }, axis=1)
    return out.reset_index()


def main() -> None:
    h = pd.read_csv(OUT / "north_mixture_hourly.csv.gz")
    err = pd.DataFrame({"station": h["station"], "truth": h["truth"],
                        "V1": abs_diff(h["V1"], h["truth"]), "model": abs_diff(h["model"], h["truth"])})
    t = err["truth"]
    halves = {"90–270°": (t >= 90) & (t < 270), "270–360°": t >= 270, "0–90°": t < 90}
    west = {f"{x}–360°": t >= x for x in WEST_EDGES}
    east = {f"0–{x}°": t < x for x in EAST_EDGES}
    south = {}
    for x in SOUTH_EDGES:
        inside = (t >= x) & (t <= 360 - x)
        south[f"{x}–{360 - x}°"] = inside
        south[f"complemento (±{x}° del norte)"] = ~inside
    for title, sectors in (("Mitades", halves), ("Oeste del norte, estrechando", west),
                           ("Este del norte, estrechando", east), ("Sector sur ampliándose y su complemento", south)):
        parts = [err[m].assign(sector=name) for name, m in sectors.items()]
        print(f"\n### {title}\n")
        print(to_md(stats(pd.concat(parts))))


if __name__ == "__main__":
    main()
