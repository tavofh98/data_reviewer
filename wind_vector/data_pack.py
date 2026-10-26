"""Crea el paquete de datos versionado en data/: último año, columnas de viento.

Contenido, para las 9 estaciones (6 con veleta y D1, 3 ClimaVUE):
  - <fichero>_Table3_wind.csv.gz: tabla de 5 min deduplicada (último registro del fichero por timestamp).
  - <fichero>_Table1_wind.csv.gz: tabla de 60 min deduplicada con la misma regla.
  Columnas: TIMESTAMP (fin del intervalo) y las de loader.WIND_COLUMNS que tenga la estación.
  - aligned_<estación>.csv.gz (solo las 6 con D1): una fila por hora con sus 12 registros de 5 min
    (formato de loader.aligned_hours); es lo que leen protocol, north_mixture y mixture_signature.
El año se cuenta hacia atrás desde el último registro de 5 min de cada estación.
Necesita los .dat de references/ y datafiles/data_1h (solo en el equipo de origen).

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.data_pack
"""
from __future__ import annotations

import pandas as pd

from wind_vector.analyze import DATA
from wind_vector.loader import EXTRA_STATIONS, STATIONS, WIND_COLUMNS, _file_stem, aligned_hours, load_5min, load_hourly
from wind_vector.mixture_signature import CLIMAVUE
from wind_vector.protocol import DAYS

COLUMNS = set(["TIMESTAMP"] + WIND_COLUMNS)


def wind_columns(name: str) -> bool:
    return name in COLUMNS


def save(df: pd.DataFrame, name: str) -> None:
    path = DATA / name
    df.to_csv(path, float_format="%.6g")
    print(f"{path.name}: {len(df)} filas, {path.stat().st_size / 2**20:.1f} MB")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    stations = {st: _file_stem(st) for st in list(STATIONS) + list(EXTRA_STATIONS)} | CLIMAVUE
    for st, stem in stations.items():
        if st in CLIMAVUE:   # sus .dat están en references/, como los de EXTRA_STATIONS
            EXTRA_STATIONS.setdefault(st, stem)
        five = load_5min(st, wind_columns)
        start = five.index.max() - pd.Timedelta(days=DAYS)
        save(five[five.index > start], f"{stem}_Table3_wind.csv.gz")
        hourly = load_hourly(st, wind_columns)
        save(hourly[(hourly.index > start) & (hourly.index <= five.index.max())], f"{stem}_Table1_wind.csv.gz")
        if st not in CLIMAVUE:
            save(aligned_hours(st, DAYS), f"aligned_{st}.csv.gz")


if __name__ == "__main__":
    main()
