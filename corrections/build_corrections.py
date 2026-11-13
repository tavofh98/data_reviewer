"""Construye corrections.db desde cero a partir del registro y de los datos crudos.

La base cruda (database_duck/anglo_ambiental.db) solo se lee. corrections.db contiene:
- `corrections`: el registro de intervenciones (registry.py).
- `met_adjustments`: una fila por celda modificada, con el valor crudo, el corregido, el método y
  la marca de calidad.
- `met_corrected`: vista con las mismas columnas que `meteorologia`, donde cada celda ajustada
  toma el valor corregido, más la columna `adjustment_tags` (correction_id[:flag]).

Marca `north_risk`: algún registro de la hora, en el marco del sensor sin girar, está a menos de
NORTH_WINDOW° de 0/360. Una media aritmética del logger que cruzó ese corte queda falsa y girarla
no la arregla (FINDINGS.md §9).

Ejecutar desde explorar_qaqc: uv run python -m corrections.build_corrections
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from corrections.registry import CORRECTIONS, Correction
from corrections.store import CORRECTIONS_DB_PATH, connect_corrected

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "met_viewer"))
from stations import DB_PATH  # noqa: E402

REFERENCES = Path(__file__).resolve().parents[2] / "references"
# Registros de 5 min por estación (TOA5): permiten recalcular la hora como media vectorial.
FIVE_MIN_SOURCES = {"Mina_Norte": REFERENCES / "AAQ_Est_Mina_Norte_CR310_Table3.dat"}
WS, WD = "WS_ms_Avg", "WindDir_Avg"
NORTH_WINDOW = 30.0
MIN_RECORDS = 9   # de 12 registros de 5 min por hora
ADJUSTMENT_COLUMNS = ["station_id", "timestamp", "variable", "raw_value", "corrected_value",
                      "method", "flag", "correction_id"]


def read_toa5(path: Path) -> pd.DataFrame:
    """TOA5 indexado por TIMESTAMP, sin duplicados (gana el último) y ordenado."""
    df = pd.read_csv(path, skiprows=[0, 2, 3], na_values=["NAN", "nan", "NaN", ""], parse_dates=["TIMESTAMP"])
    return df.drop_duplicates("TIMESTAMP", keep="last").set_index("TIMESTAMP").sort_index()


def near_sensor_north(direction: pd.Series) -> pd.Series:
    return (direction < NORTH_WINDOW) | (direction > 360 - NORTH_WINDOW)


def hourly_vector_mean(five_min: pd.DataFrame, rotation: float) -> pd.DataFrame:
    """Dirección horaria como media de vectores unitarios de los registros de 5 min girados.

    Solo entran registros con velocidad > 0; la hora se etiqueta al final, como en la base, y
    necesita MIN_RECORDS registros.
    """
    records = five_min[[WS, WD]].astype(float).dropna()
    moving = records[records[WS] > 0]
    radians = np.deg2rad((moving[WD] + rotation) % 360)
    hourly = {"label": "right", "closed": "right"}
    sin_mean = np.sin(radians).resample("h", **hourly).mean()
    cos_mean = np.cos(radians).resample("h", **hourly).mean()
    out = pd.DataFrame({
        "direction": np.rad2deg(np.arctan2(sin_mean, cos_mean)) % 360,
        "north_risk": near_sensor_north(moving[WD]).resample("h", **hourly).max(),
        "records": moving[WD].resample("h", **hourly).count(),
    })
    return out[out["records"] >= MIN_RECORDS]


def load_raw(con, correction: Correction) -> pd.Series:
    """Valores crudos no vacíos de la variable en (start, end]."""
    df = con.execute(
        f'SELECT timestamp, "{correction.variable}" AS value FROM raw.meteorologia '
        "WHERE estacion_id = ? AND timestamp > ? AND timestamp <= ? ORDER BY timestamp",
        [correction.station_id, correction.start, correction.end]).df()
    return df.drop_duplicates("timestamp", keep="last").set_index("timestamp")["value"].dropna()


def rotation_adjustments(correction: Correction, raw: pd.Series) -> pd.DataFrame:
    rotation = float(correction.parameter)
    out = pd.DataFrame({"raw_value": raw})
    out["corrected_value"] = (raw + rotation) % 360
    out["method"] = "hourly_rotated"
    out["flag"] = np.where(near_sensor_north(raw), "north_risk", None)

    source = FIVE_MIN_SOURCES.get(correction.station_id)
    if source is not None:
        five_min = read_toa5(source).loc[correction.start:correction.end]
        vector = hourly_vector_mean(five_min, rotation).reindex(raw.index).dropna(subset=["direction"])
        out.loc[vector.index, "corrected_value"] = vector["direction"]
        out.loc[vector.index, "method"] = "5min_vector"
        out.loc[vector.index, "flag"] = np.where(vector["north_risk"].astype(bool), "north_risk", None)
    return out


def exclusion_adjustments(raw: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"raw_value": raw, "corrected_value": np.nan, "method": "excluded", "flag": "excluded"})


def check_no_overlap(corrections: tuple[Correction, ...]) -> None:
    by_key: dict[tuple[str, str], list[Correction]] = {}
    for c in corrections:
        by_key.setdefault((c.station_id, c.variable), []).append(c)
    for key, items in by_key.items():
        items.sort(key=lambda c: pd.Timestamp(c.start))
        for prev, nxt in zip(items, items[1:]):
            if pd.Timestamp(prev.end) > pd.Timestamp(nxt.start):
                raise ValueError(f"{key}: {prev.correction_id} se solapa con {nxt.correction_id}")


def build_adjustments(con) -> pd.DataFrame:
    parts = []
    for c in CORRECTIONS:
        raw = load_raw(con, c)
        if c.kind == "rotation":
            part = rotation_adjustments(c, raw)
        elif c.kind == "exclusion":
            part = exclusion_adjustments(raw)
        else:
            raise ValueError(f"{c.correction_id}: tipo desconocido {c.kind!r}")
        part = part.rename_axis("timestamp").reset_index()
        part["station_id"], part["variable"], part["correction_id"] = c.station_id, c.variable, c.correction_id
        parts.append(part[ADJUSTMENT_COLUMNS])
    return pd.concat(parts, ignore_index=True)


def create_view(con, adjusted_variables: list[str]) -> None:
    """Vista met_corrected: columnas de meteorologia con las celdas ajustadas sustituidas."""
    columns = [r[0] for r in con.execute("DESCRIBE raw.meteorologia").fetchall()]
    pivot = ", ".join(
        f"bool_or(variable = '{v}') AS \"{v}__adjusted\", "
        f"max(corrected_value) FILTER (WHERE variable = '{v}') AS \"{v}__value\""
        for v in adjusted_variables)
    select = [
        f'CASE WHEN a."{c}__adjusted" THEN a."{c}__value" ELSE m."{c}" END AS "{c}"'
        if c in adjusted_variables else f'm."{c}"'
        for c in columns]
    con.execute(f"""
        CREATE VIEW met_corrected AS
        WITH a AS (
            SELECT station_id, timestamp, {pivot},
                   string_agg(correction_id || coalesce(':' || flag, ''), ';' ORDER BY variable) AS adjustment_tags
            FROM met_adjustments
            GROUP BY station_id, timestamp
        )
        SELECT {', '.join(select)}, a.adjustment_tags
        FROM raw.meteorologia AS m
        LEFT JOIN a ON a.station_id = m.estacion_id AND a.timestamp = m.timestamp
    """)


def main() -> None:
    check_no_overlap(CORRECTIONS)
    CORRECTIONS_DB_PATH.unlink(missing_ok=True)
    con = connect_corrected(DB_PATH, read_only=False)
    try:
        registry = pd.DataFrame([asdict(c) for c in CORRECTIONS])
        registry["start"], registry["end"] = pd.to_datetime(registry["start"]), pd.to_datetime(registry["end"])
        registry = registry.rename(columns={"start": "start_ts", "end": "end_ts"})
        con.execute("CREATE TABLE corrections AS SELECT * FROM registry")

        adjustments = build_adjustments(con)
        if adjustments.duplicated(["station_id", "timestamp", "variable"]).any():
            raise ValueError("Hay celdas ajustadas por más de una intervención")
        con.execute("""
            CREATE TABLE met_adjustments AS
            SELECT station_id, timestamp, variable, CAST(raw_value AS DOUBLE) AS raw_value,
                   CAST(corrected_value AS DOUBLE) AS corrected_value, method, flag, correction_id
            FROM adjustments ORDER BY station_id, timestamp, variable
        """)
        create_view(con, sorted(adjustments["variable"].unique()))

        print(f"escrito {CORRECTIONS_DB_PATH}")
        print(con.execute("""
            SELECT correction_id, method, coalesce(flag, '') AS flag, count(*) AS hours,
                   min(timestamp) AS first_hour, max(timestamp) AS last_hour
            FROM met_adjustments GROUP BY ALL ORDER BY first_hour, method, flag
        """).df().to_string(index=False))
    finally:
        con.close()


if __name__ == "__main__":
    main()
