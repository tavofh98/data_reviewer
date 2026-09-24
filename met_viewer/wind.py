"""Indicadores de viento para el visor (convenciones de WIND_REVIEW.md §1).

- Dirección de procedencia, en grados desde el norte y en sentido horario.
- Las calmas (WS < qc.CALM_WS) no tienen dirección: en las rosas cuentan aparte.
- Franjas: día 10–17 h y noche 22–05 h; las horas de transición no entran en las rosas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import data
import qc

MIN_HORAS_CICLO = 3     # valores mínimos en una hora del día para dar su media
FRANJAS = {"día": list(range(10, 18)), "noche": [22, 23, 0, 1, 2, 3, 4, 5]}
SECTORES = 16
CLASES_VEL = [qc.CALM_WS, 2, 4, 6, np.inf]
ETIQUETAS_VEL = ["0.5–2 m/s", "2–4 m/s", "4–6 m/s", "≥ 6 m/s"]


def ciclo_velocidad(df: pd.DataFrame) -> pd.Series:
    """Velocidad media por hora del día (0–23), calmas incluidas. NaN con pocas horas."""
    s = df[data.WS].dropna()
    g = s.groupby(s.index.hour)
    return g.mean().where(g.size() >= MIN_HORAS_CICLO).reindex(range(24))


def rosa(df: pd.DataFrame, franja: str) -> tuple[pd.DataFrame, float, int]:
    """Frecuencia de procedencia en la franja: tabla sector × clase de velocidad en % de todas
    las horas con dato (calmas incluidas en el total), % de calma y horas con dato."""
    d = df[df.index.hour.isin(FRANJAS[franja])][[data.WS, data.WD]].dropna()
    n = len(d)
    if n == 0:
        return pd.DataFrame(0.0, index=range(SECTORES), columns=ETIQUETAS_VEL), float("nan"), 0
    viento = d[d[data.WS] >= qc.CALM_WS]
    ancho = 360 / SECTORES
    sector = ((viento[data.WD] + ancho / 2) % 360 // ancho).astype(int)
    clase = pd.cut(viento[data.WS], CLASES_VEL, labels=ETIQUETAS_VEL, right=False)
    tabla = pd.crosstab(sector, clase).reindex(index=range(SECTORES), columns=ETIQUETAS_VEL, fill_value=0)
    return tabla / n * 100, (1 - len(viento) / n) * 100, n
