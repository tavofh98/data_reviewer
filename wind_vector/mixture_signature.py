"""¿Tiene WindDir_Avg de 5 min la firma de las mezclas del norte? Prueba sin D1 para las estaciones ClimaVUE.

Física: con viento de al menos MIN_WS m/s la dirección real no pasa del norte al sur en 5 min. Un promedio
aritmético con mezclas sí lo hace: un registro cerca del norte va seguido de otro en 90–270°.
Estadístico: P(siguiente en 90–270° | actual a ≤ 30° del norte), en pares consecutivos con velocidad ≥ MIN_WS.
Calibración: en las 6 estaciones con veleta se calcula sobre WindDir_Avg (que mezcla) y sobre D1 (vectorial)
del mismo sensor; la prueba sirve si separa claramente ambos. Después se aplica a WindDir_Avg de las ClimaVUE.

Uso (desde explorar_qaqc/, con los aligned_*.csv.gz ya creados):
    uv run python -m wind_vector.mixture_signature
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from wind_vector.analyze import OUT, to_md
from wind_vector.loader import DIR_5MIN_EXTRA, _deduplicate, _read_toa5
from wind_vector.north_mixture import to_5min
from wind_vector.north_sector import abs_diff
from wind_vector.protocol import ALL, DAYS

CLIMAVUE = {"salviani": "AAQ_Cerro_Salviani_CR310X", "calientes1": "AAQ_Est_Calientes1_CR310x",
            "sarallenque_mqg": "Sarallenque_MQG-15-02"}
MIN_WS = 2.0
NORTH = 30.0


def signature(direction: pd.Series, ws: pd.Series) -> dict:
    """Tasa de saltos norte → sur entre registros consecutivos (serie regular de 5 min)."""
    nxt, ws_n = direction.shift(-1), ws.shift(-1)
    ok = (ws >= MIN_WS) & (ws_n >= MIN_WS) & direction.notna() & nxt.notna()
    north = ok & (abs_diff(direction, 0.0) <= NORTH)
    south_next = (nxt >= 90) & (nxt <= 270)
    # Segunda firma, útil donde casi no hay A cerca del norte: una mezcla pura da A ≈ 180 y salta mucho;
    # un viento real del sur es estable.
    mid = ok & (direction >= 120) & (direction <= 240)
    jump = abs_diff(direction, nxt) > 60
    return {"pares": int(ok.sum()), "% registros cerca del norte": 100 * north.sum() / max(ok.sum(), 1),
            "n norte": int(north.sum()), "P(N→S) %": 100 * (north & south_next).sum() / max(north.sum(), 1),
            "n 120–240": int(mid.sum()), "P(salto > 60° | 120–240) %": 100 * (mid & jump).sum() / max(mid.sum(), 1)}


def climavue_5min(stem: str) -> pd.DataFrame:
    cols = ["TIMESTAMP", "WS_ms_Avg", "WindDir_Avg"]
    df = _deduplicate(_read_toa5(DIR_5MIN_EXTRA / f"{stem}_Table3.dat", cols))
    df = df[df.index > df.index.max() - pd.Timedelta(days=DAYS)]
    return df.asfreq("5min")


def main() -> None:
    rows = []
    for st in ALL:
        df = pd.read_csv(OUT / f"aligned_{st}.csv.gz", parse_dates=["TIMESTAMP"])
        df = df[df["TIMESTAMP"] > df["TIMESTAMP"].max() - pd.Timedelta(days=DAYS)]
        s = to_5min(df)
        rows.append({"estación": st, "sensor": "veleta", "dirección": "WindDir_Avg (A)", **signature(s["A"], s["ws"])})
        rows.append({"estación": st, "sensor": "veleta", "dirección": "D1 (vectorial)", **signature(s["D1"], s["ws"])})
    for st, stem in CLIMAVUE.items():
        s = climavue_5min(stem)
        rows.append({"estación": st, "sensor": "ClimaVUE", "dirección": "WindDir_Avg (A)",
                     **signature(s["WindDir_Avg"], s["WS_ms_Avg"]),
                     "periodo": f"{s.index.min():%Y-%m-%d} a {s.index.max():%Y-%m-%d}"})
    print(f"\n### Saltos norte → sur en 5 min (velocidad ≥ {MIN_WS} m/s, norte = ±{NORTH:.0f}°)\n")
    print(to_md(pd.DataFrame(rows).fillna("")))


if __name__ == "__main__":
    main()
