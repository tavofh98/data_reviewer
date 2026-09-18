"""Carga de meteorología desde DuckDB (solo lectura), limitada a lo que marca VARIABLES_REPORTE."""
from __future__ import annotations

import duckdb
import pandas as pd

from stations import DB_PATH, REPORTED, STATIONS

TEMP, RH, BP, WS, WD = "AirTC_Avg", "RH_Avg", "BP_mbar_Avg", "WS_ms_Avg", "WindDir_Avg"
VARIABLES = [TEMP, RH, BP, WS, WD]


def load(start: pd.Timestamp, end: pd.Timestamp) -> dict[str, pd.DataFrame]:
    """Devuelve {estacion_id: DataFrame horario indexado por timestamp} en [start, end).

    Solo entran las estaciones con metadato y las variables de VARIABLES que la estación
    reporta; el resto de columnas no se lee.
    """
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        df = con.execute(
            f"SELECT estacion_id, timestamp, {', '.join(VARIABLES)} FROM meteorologia "
            "WHERE timestamp >= ? AND timestamp < ? ORDER BY estacion_id, timestamp",
            [start.to_pydatetime(), end.to_pydatetime()],
        ).df()
    finally:
        con.close()

    datos: dict[str, pd.DataFrame] = {}
    for est, g in df.groupby("estacion_id"):
        if est not in STATIONS or est not in REPORTED:
            continue
        cols = [v for v in VARIABLES if v in REPORTED[est]]
        if cols:
            datos[est] = g.set_index("timestamp")[cols].astype("float64")
    return datos
