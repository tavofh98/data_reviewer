"""Utilidades compartidas por los análisis de viento de Mina_Norte.

El giro del tramo B y la media vectorial de 5 min vienen de corrections/, que es donde se aplica
la corrección; aquí solo se reutilizan para no tener dos versiones.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "met_viewer"))
from corrections.build_corrections import (  # noqa: E402
    FIVE_MIN_SOURCES, REFERENCES, WD, WS, hourly_vector_mean, read_toa5)
from corrections.registry import CORRECTIONS  # noqa: E402
from corrections.store import connect_corrected  # noqa: E402
from stations import DB_PATH  # noqa: E402

MN_5MIN = FIVE_MIN_SOURCES["Mina_Norte"]
OESTE1_DAT = REFERENCES / "AAQ_Est_OESTE_1_Table1_Oizom.dat"
SEGMENT_B = next(c for c in CORRECTIONS if c.correction_id == "MN-B-rotation")
DAY, NIGHT = range(10, 18), [22, 23, 0, 1, 2, 3, 4, 5]

__all__ = ["DAY", "DB_PATH", "MN_5MIN", "NIGHT", "OESTE1_DAT", "SEGMENT_B", "WD", "WS", "angle_diff",
           "hourly_from_5min", "load_station", "read_toa5"]


def angle_diff(a, b):
    """Diferencia circular a − b en (−180, 180]."""
    return ((a - b + 180) % 360) - 180


def load_station(station: str, start, end, corrected: bool = False) -> pd.DataFrame:
    """Velocidad y dirección horarias en (start, end], crudas o de la vista met_corrected."""
    table = "met_corrected" if corrected else "raw.meteorologia"
    con = connect_corrected(DB_PATH)
    try:
        df = con.execute(
            f"SELECT timestamp, {WS}, {WD} FROM {table} WHERE estacion_id = ? "
            "AND timestamp > ? AND timestamp <= ? ORDER BY timestamp",
            [station, pd.Timestamp(start).to_pydatetime(), pd.Timestamp(end).to_pydatetime()]).df()
    finally:
        con.close()
    return df.drop_duplicates("timestamp", keep="last").set_index("timestamp")


def hourly_from_5min(five_min: pd.DataFrame, rotation: float) -> pd.DataFrame:
    """Hora desde 5 min: velocidad escalar media y dirección vectorial de los registros girados."""
    vector = hourly_vector_mean(five_min, rotation)
    speed = five_min[WS].astype(float).resample("h", label="right", closed="right").mean()
    return pd.DataFrame({WS: speed.reindex(vector.index), WD: vector["direction"],
                         "north_risk": vector["north_risk"].astype(bool)})
