"""Exploración inicial de la base de datos, archivos en scratchpad y references,
y reproducción exacta de los scripts de referencia."""
import os
import sys
import glob
import subprocess
import duckdb
import pandas as pd
import numpy as np

SCRATCH = str(__import__("pathlib").Path(__file__).resolve().parent)
REFS = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/references"
DB = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db"
EXPLORAR = r"C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc"

print("=== 1. ARCHIVOS EN SCRATCHPAD ===")
for root, dirs, files in os.walk(SCRATCH):
    for f in sorted(files):
        p = os.path.join(root, f)
        print(os.path.relpath(p, SCRATCH), f"({os.path.getsize(p)} bytes)")

print("\n=== 2. ARCHIVOS EN REFERENCES ===")
for root, dirs, files in os.walk(REFS):
    for f in sorted(files):
        p = os.path.join(root, f)
        print(os.path.relpath(p, REFS), f"({os.path.getsize(p)} bytes)")

print("\n=== 3. ESQUEMA Y RESUMEN DE METEOROLOGIA EN DUCKDB ===")
con = duckdb.connect(DB, read_only=True)
cols = con.execute("DESCRIBE meteorologia").df()
print(cols.to_string(index=False))

summary = con.execute("""
SELECT
    estacion_id,
    MIN(timestamp) as min_ts,
    MAX(timestamp) as max_ts,
    COUNT(*) as n_total,
    COUNT(WindDir_Avg) as n_avg,
    COUNT(WindDir_D1_WVT) as n_d1,
    COUNT(WindDir_SD1_WVT) as n_sd1,
    COUNT(WS_ms_Avg) as n_ws
FROM meteorologia
WHERE timestamp >= '2025-11-01'
GROUP BY estacion_id
ORDER BY estacion_id
""").df()
print("\nResumen desde 2025-11-01:")
print(summary.to_string(index=False))

print("\n=== 4. REPRODUCCIÓN DE SCRIPTS EXISTENTES ===")
for script, args in [
    ("idw_all.py", []),
    ("calib.py", []),
    ("calib.py", ["--limpio"]),
    ("pairs_calib.py", []),
    ("pairs_calib.py", ["--limpio"]),
    ("diag.py", ["--limpio"]),
]:
    print(f"\n--- Ejecutando {script} {' '.join(args)} ---")
    cmd = [sys.executable, os.path.join(SCRATCH, script)] + args
    res = subprocess.run(cmd, cwd=EXPLORAR, capture_output=True, text=True, encoding="utf-8")
    print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)
