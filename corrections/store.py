"""Acceso de lectura a la base de correcciones con la base cruda adjunta.

La vista `met_corrected` lee `raw.meteorologia`, así que la base cruda tiene que estar adjunta con
el alias `raw` en cada conexión: ATTACH no se guarda en el fichero.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

CORRECTIONS_DB_PATH = Path(__file__).resolve().parent / "corrections.db"
RAW_ALIAS = "raw"


def connect_corrected(raw_db_path: Path, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Conexión a corrections.db con la base cruda adjunta en solo lectura."""
    con = duckdb.connect(str(CORRECTIONS_DB_PATH), read_only=read_only)
    con.execute(f"ATTACH '{raw_db_path}' AS {RAW_ALIAS} (READ_ONLY)")
    return con
