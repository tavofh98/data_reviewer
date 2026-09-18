"""Calcula la altitud barométrica (z_baro) de cada estación y la compara con el DEM.

Uso:
    uv run python met_viewer/calibrate_baro.py [--dias 365]

Imprime la tabla de control y las líneas `"estacion": z_baro,` para copiar a mano en
stations.py. No escribe ningún archivo: fijar z_baro es una decisión, no un efecto colateral.
"""
from __future__ import annotations

import argparse

import pandas as pd

import data
import qc
from stations import STATIONS


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dias", type=int, default=365)
    args = ap.parse_args()

    fin = pd.Timestamp.now().normalize()
    datos = data.load(fin - pd.Timedelta(days=args.dias), fin)
    p_med, t_med = {}, {}
    for est, df in datos.items():
        if est in qc.BARO_EXCLUDE or data.BP not in df or data.TEMP not in df:
            continue
        reglas = qc.station_rules(df)
        m = reglas["ZERO_RECORD"] | reglas["RANGE"] | reglas["STUCK"] | reglas["SPIKE"]
        limpio = df.mask(m)
        if limpio[data.BP].count() < 24 * 30:
            print(f"  {est}: menos de 30 días de presión válida, se omite")
            continue
        p_med[est], t_med[est] = limpio[data.BP].median(), limpio[data.TEMP].median()

    p_med, t_med = pd.Series(p_med), pd.Series(t_med)
    z_dem = pd.Series({e: s.z_dem for e, s in STATIONS.items()})
    z = qc.barometric_elevation(p_med, t_med, z_dem)

    tabla = pd.DataFrame({"p_mediana": p_med.round(1), "z_dem": z_dem[z.index], "z_baro": z.round(0),
                          "dif": (z - z_dem[z.index]).round(0)}).sort_values("dif")
    print(tabla.to_string())
    print(f"\n|dif| máx = {tabla['dif'].abs().max():.0f} m · mediana |dif| = {tabla['dif'].abs().median():.0f} m")
    print("\n# para stations.py")
    for e, v in z.round(0).items():
        print(f'    "{e}": {v:.0f},')


if __name__ == "__main__":
    main()
