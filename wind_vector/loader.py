"""Cargador de datos de viento (TOA5 de Campbell) y alineación hora a hora.

Lee las tablas de 5 min (Table3) y de 60 min (Table1) de las estaciones del
estudio y construye un conjunto con una fila por hora de la tabla de 60 min,
junto a los 12 registros de 5 min que la componen.

Convención de tiempo: el TIMESTAMP de Campbell es el FIN del intervalo. La hora
HH:00 agrupa los registros de 5 min con sello HH-1:05, HH-1:10, ..., HH:00
(m01 ... m12). La convención se verifica con los datos en ``build_load_report.py``.
"""

from pathlib import Path

import pandas as pd

# Raíz del repositorio de trabajo (control_calidad) y carpetas de datos.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIR_5MIN = _PROJECT_ROOT / "references" / "val_wind_vector"
DIR_5MIN_EXTRA = _PROJECT_ROOT / "references"
DIR_HOURLY = _PROJECT_ROOT.parents[1] / "datafiles" / "data_1h"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# Nombre del fichero (sin sufijo de tabla) de cada estación.
STATIONS = {
    "cortadera": "AAQ_Est_Cortadera_CR1000X",
    "papujune": "AAQ_Est_Papujune_CR1000X",
    "quellaveco": "AAQ_Alto_Quellaveco_CR1000X",
}

# Estaciones de validación externa (también guardan D1 y SD1); sus Table3 están en references/.
EXTRA_STATIONS = {
    "tala1": "AAQ_Est_Tala-1_CR310X",
    "tala_legal": "AAQ_Tala_Legal",
    "minas_sur": "AAQ_Minas_Sur",
}
EXTRA_DAYS = 365  # de las estaciones externas basta el último año

WIND_COLUMNS = [
    "WS_ms_Avg",
    "WS_ms_Max",
    "WindDir_Avg",
    "WS_ms_S_WVT",
    "WindDir_D1_WVT",
    "WindDir_SD1_WVT",
]

# Un registro de 5 min es válido si tiene velocidad y dirección medias.
VALIDITY_COLUMNS = ["WS_ms_Avg", "WindDir_Avg"]

N_SLOTS = 12  # registros de 5 min por hora


def _read_toa5(path, usecols=None):
    """Lee un TOA5 con pandas y devuelve el DataFrame sin deduplicar.

    Fila 1 son metadatos, fila 2 los nombres, filas 3 y 4 unidades y agregación
    (se descartan). Todo se lee como texto y se convierte a float con
    ``errors="coerce"``: así un valor corrupto aislado (p. ej. ``277.0204S`` en
    SlrkJ_Tot de Papujune, fuera de las columnas de viento) pasa a NaN sin
    tumbar la carga. El orden de las filas es el del fichero. ``usecols``
    limita las columnas leídas (ahorra memoria en los ficheros grandes).
    """
    df = pd.read_csv(path, skiprows=[0, 2, 3], na_values=["NAN"], dtype=str, usecols=usecols)
    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
    for column in df.columns.drop("TIMESTAMP"):
        df[column] = pd.to_numeric(df[column], errors="coerce").astype(float)
    return df


def _deduplicate(df):
    """Deja un único registro por timestamp: el ÚLTIMO en orden de fichero.

    Los .dat son concatenaciones de descargas sucesivas y RECORD se reinicia
    (reinicios del logger), así que ni el RECORD ni el timestamp permiten
    ordenar la "frescura" de un registro; el orden de aparición sí: lo último
    del fichero es lo escrito más tarde. Además resuelve un caso real en
    Quellaveco (abril 2026), donde un bloque de 52 registros horarios quedó
    insertado dentro de la tabla de 5 min y después se reescribe la serie de
    5 min completa: al quedarse con el último, los registros intrusos se
    descartan. Tras deduplicar se ordena por tiempo y se indexa por TIMESTAMP.
    """
    df = df.drop_duplicates(subset="TIMESTAMP", keep="last")
    return df.sort_values("TIMESTAMP").set_index("TIMESTAMP")


def _file_stem(station):
    return STATIONS.get(station) or EXTRA_STATIONS[station]


def load_5min(station, usecols=None):
    """Tabla de 5 min (Table3) de la estación, indexada por TIMESTAMP (fin de intervalo).

    Deduplicada con la regla de ``_deduplicate`` (último registro del fichero).
    """
    folder = DIR_5MIN if station in STATIONS else DIR_5MIN_EXTRA
    return _deduplicate(_read_toa5(folder / f"{_file_stem(station)}_Table3.dat", usecols))


def load_hourly(station, usecols=None):
    """Tabla de 60 min (Table1) de la estación, indexada por TIMESTAMP (fin de intervalo).

    Deduplicada con la misma regla que los 5 min (último registro del fichero).
    Es la "verdad" horaria: el logger calcula Θ1 sobre 720 muestras de 5 s.
    """
    return _deduplicate(_read_toa5(DIR_HOURLY / f"{_file_stem(station)}_Table1.dat", usecols))


def aligned_hours(station, days=None):
    """Una fila por hora de la tabla de 60 min con sus 12 registros de 5 min.

    Formato ancho. Columnas:
      - ``<var>_h``: columnas de viento de la tabla de 60 min.
      - ``<var>_m01`` ... ``<var>_m12``: la misma variable en los registros de
        5 min con sello HH-1:05 (m01) ... HH:00 (m12), para la hora HH:00.
        Faltan (NaN) si el registro de 5 min no existe.
      - ``n_5min``: cuántos de los 12 registros existen y son válidos
        (WS_ms_Avg y WindDir_Avg no nulos).
    El índice es el TIMESTAMP (fin de la hora) de la tabla de 60 min. Con
    ``days`` se conservan solo los últimos ``days`` días que tienen 5 min.
    """
    cols = ["TIMESTAMP"] + WIND_COLUMNS
    hourly = load_hourly(station, cols)[WIND_COLUMNS].add_suffix("_h")
    five_min = load_5min(station, cols)[WIND_COLUMNS]
    if days is not None:
        start = five_min.index.max() - pd.Timedelta(days=days)
        five_min = five_min[five_min.index > start]
        hourly = hourly[(hourly.index > start) & (hourly.index <= five_min.index.max())]

    parts = [hourly]
    valid = pd.DataFrame(index=hourly.index)
    for slot in range(1, N_SLOTS + 1):
        # m01 está 55 min antes del fin de hora; m12 coincide con el fin de hora.
        offset = pd.Timedelta(minutes=5 * (N_SLOTS - slot))
        slot_data = five_min.reindex(hourly.index - offset)
        slot_data.index = hourly.index
        valid[slot] = slot_data[VALIDITY_COLUMNS].notna().all(axis=1)
        parts.append(slot_data.add_suffix(f"_m{slot:02d}"))

    aligned = pd.concat(parts, axis=1)
    aligned["n_5min"] = valid.sum(axis=1).astype(int)
    return aligned


def save_aligned(station, days=None):
    """Guarda el conjunto alineado en ``output/aligned_<station>.parquet``.

    Si falta pyarrow se guarda como ``aligned_<station>.csv.gz``.
    Devuelve la ruta escrita.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    aligned = aligned_hours(station, days)
    try:
        path = OUTPUT_DIR / f"aligned_{station}.parquet"
        aligned.to_parquet(path)
    except ImportError:
        path = OUTPUT_DIR / f"aligned_{station}.csv.gz"
        aligned.to_csv(path)
    return path


if __name__ == "__main__":
    import sys

    # "extra" prepara solo las estaciones externas (último año).
    if sys.argv[1:] == ["extra"]:
        for station_name in EXTRA_STATIONS:
            print(station_name, "->", save_aligned(station_name, EXTRA_DAYS))
    else:
        for station_name in STATIONS:
            print(station_name, "->", save_aligned(station_name))
