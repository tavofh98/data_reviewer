"""Validación de la corrección del tramo B de Mina_Norte contra Oeste 1, de día y de noche.

La corrección se aplica en corrections.db (intervención MN-B-rotation). Aquí se compara, en las
horas con registros de 5 min, la dirección cruda, la cruda girada (media aritmética) y la
corregida (media vectorial de 5 min girados), con y sin las horas marcadas north_risk. El tramo C
(ClimaVUE, sin girar) sirve de referencia.

Ejecutar desde explorar_qaqc: uv run python mina_norte_wind/validate_segment_b.py
"""
from __future__ import annotations

import pandas as pd

from common import (DAY, DB_PATH, MN_5MIN, NIGHT, OESTE1_DAT, SEGMENT_B, WD, WS, angle_diff,
                    hourly_from_5min, load_station, read_toa5)
from corrections.store import connect_corrected

SEGMENT_C_START = pd.Timestamp("2026-08-28")


def summarize(label: str, direction: pd.Series, speed: pd.Series, oeste1: pd.DataFrame) -> list[dict]:
    """Mediana, IQR y fracción |d| < 30° de la diferencia con Oeste 1, ambas ≥ 1 m/s."""
    x = pd.DataFrame({"dir": direction, "ws": speed}).join(oeste1, how="inner").dropna()
    x = x[(x["ws"] >= 1) & (x[WS] >= 1)]
    rows = []
    for period, hours in (("día", DAY), ("noche", NIGHT)):
        d = angle_diff(x.loc[x.index.hour.isin(hours), "dir"], x.loc[x.index.hour.isin(hours), WD])
        rows.append({"serie": label, "franja": period, "horas": len(d), "mediana": d.median(),
                     "IQR": d.quantile(.75) - d.quantile(.25), "|d|<30 %": 100 * (d.abs() < 30).mean()})
    return rows


def load_segment_b() -> pd.DataFrame:
    """Ajustes del tramo B con la velocidad cruda, desde corrections.db."""
    con = connect_corrected(DB_PATH)
    try:
        df = con.execute(f"""
            SELECT a.timestamp, m.{WS}, a.raw_value, a.corrected_value, a.method, a.flag
            FROM met_adjustments AS a
            JOIN raw.meteorologia AS m ON m.estacion_id = a.station_id AND m.timestamp = a.timestamp
            WHERE a.correction_id = ? ORDER BY a.timestamp""", [SEGMENT_B.correction_id]).df()
    finally:
        con.close()
    return df.set_index("timestamp")


def main() -> None:
    rotation = float(SEGMENT_B.parameter)
    oeste1 = read_toa5(OESTE1_DAT)[[WS, WD]]
    seg_b = load_segment_b()
    print(seg_b.groupby(["method", seg_b["flag"].fillna("")]).size().rename("horas").to_string())

    five = seg_b[seg_b["method"] == "5min_vector"]
    clean = five[five["flag"].isna()]
    rows = []
    rows += summarize("cruda", five["raw_value"], five[WS], oeste1)
    rows += summarize(f"cruda girada +{rotation:g} (aritmética)", (five["raw_value"] + rotation) % 360, five[WS], oeste1)
    rows += summarize("corregida (5 min + vector)", five["corrected_value"], five[WS], oeste1)
    rows += summarize("corregida, sin north_risk", clean["corrected_value"], clean[WS], oeste1)
    pd.set_option("display.width", 200)
    print(f"\nTramo B, horas con 5 min ({five.index.min()} → {five.index.max()}), diferencia con Oeste 1:")
    print(pd.DataFrame(rows).round(1).to_string(index=False))

    five_c = read_toa5(MN_5MIN).loc[SEGMENT_C_START:]
    vector_c = hourly_from_5min(five_c, 0.0)
    raw_c = load_station("Mina_Norte", SEGMENT_C_START, vector_c.index.max()).reindex(vector_c.index)
    print("\nReferencia, tramo C con ClimaVUE (desde 2026-08-28):")
    print(pd.DataFrame(summarize("C cruda (aritmética)", raw_c[WD], raw_c[WS], oeste1)
                       + summarize("C 5 min + vector", vector_c[WD], vector_c[WS], oeste1)).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
