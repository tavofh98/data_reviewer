"""QC automático de meteorología: descarte fuerte antes de agrupar y graficar.

Cada regla devuelve una máscara booleana (True = descartar). `apply_qc` las aplica en orden
y guarda en cada celda descartada el código de la PRIMERA regla que la atrapó.

Reglas:
    ZERO_RECORD  T, HR y BP = 0 a la vez: el logger escribió el registro vacío en cero.
                 (BP = 0 sola no invalida T y HR: en Chancado 2022-2024 seguían siendo válidas.)
    RANGE        fuera del rango físico.
    STUCK        >= STUCK_HOURS horas con el mismo valor (sensor pegado). Niebla (HR >= 95) y
                 calma (WS < 0.5) quedan exentas mientras la racha dure menos de 24 h.
    SPIKE        Hampel (desvío de la mediana móvil de 24 h mayor que k·MAD, con piso) Y además
                 apartado de lo que marcan sus vecinas. Sin el segundo filtro, el 80 % de los
                 descartes eran subidas solares y tormentas reales que las vecinas también
                 registraban (medido 2024-2026). Sin 2 vecinas a menos de 17 km: Hampel solo.
    BARO_DEV     presión reducida a un nivel común que se aparta más de BARO_MAX_DEV de la
                 mediana de sus vecinas (reubicación, escalón grande del barómetro). Los desvíos
                 menores no se descartan: los muestra la figura de desvío de presión.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from data import BP, RH, TEMP, WD, WS
from stations import STATIONS

RANGES: dict[str, tuple[float, float]] = {
    TEMP: (-30.0, 45.0),
    RH: (0.0, 103.0),       # 100–103: saturación con error de calibración, no se descarta
    BP: (500.0, 1050.0),
    WS: (0.0, 40.0),
    WD: (0.0, 360.0),
}
STUCK_HOURS = 6
STUCK_HOURS_BP = 12              # barómetros de 1 mbar de resolución (Ilo) repiten 6–13 h sin fallar
SPIKE_VARS = (TEMP, RH)
STUCK_EXEMPT_MAX_HOURS = 24      # niebla o calma más larga que esto sí se trata como pegado
FOG_RH = 95.0                    # algunos sensores saturan en 97–99.4 % (Huachunta, Camp_Quellaveco)
SPIKE_WINDOW, SPIKE_K, SPIKE_FLOOR = "24h", 6.0, 1.0
SPIKE_NEIGHBOR_KM = 17.0         # cubre al trío de alta montaña (Huachunta–Titire a 16.3 km)
SPIKE_NEIGHBOR_TOL = {TEMP: 2.0, RH: 10.0}   # desvío respecto a lo esperado por las vecinas
CALM_WS = 0.5                    # con viento más débil la dirección no significa nada

# Reducción hidrostática de la presión
RD, G, LAPSE = 287.05, 9.80665, 0.0065
Z_REF = 4000.0                   # nivel común (m) al que se reduce toda la red de montaña
BARO_MAX_DEV = 2.0               # mbar, sobre la mediana móvil de 24 h del desvío
BARO_RADIUS_KM = 25.0            # vecinas con las que se compara (la alta montaña está a ~60 km
                                 # de la mina y su presión oscila ±0.8 mbar con la estación)
BARO_MIN_NEIGHBORS = 2           # vecinas con dato mínimas en una hora
BARO_EXCLUDE = {"Ilo"}           # a 16 m: reducirla 4 km hacia arriba no es comparable

RULES = ("ZERO_RECORD", "RANGE", "STUCK", "SPIKE", "BARO_DEV")


# ── física ────────────────────────────────────────────────────────────────────

def reduce_pressure(p, t_celsius, z, z_ref: float = Z_REF):
    """Presión reducida de la altitud z a z_ref (aproximación hipsométrica).

    La temperatura media de la columna se estima con la de la estación y un gradiente
    estándar. Conviene pasar T suavizada (24 h): la columna libre no sigue el ciclo diurno
    de la superficie.
    """
    tm = np.asarray(t_celsius) + 273.15 - LAPSE * (z_ref - np.asarray(z)) / 2
    return np.asarray(p) * np.exp(-G * (z_ref - np.asarray(z)) / (RD * tm))


def barometric_elevation(p_med: pd.Series, t_med: pd.Series, z_dem: pd.Series) -> pd.Series:
    """Altitud de cada estación que hace coherente su presión con la del resto.

    Para una presión de referencia P, z_i es la altitud con la que la mediana de la estación
    reduce exactamente a P. Se elige P de modo que la mediana de (z_i − z_dem_i) sea 0: la
    coherencia la dan los barómetros y el nivel absoluto lo ancla el DEM.
    """
    zs = np.arange(0.0, 5500.0, 0.5)

    def resolver(p_ref: float) -> pd.Series:
        return pd.Series({e: zs[np.argmin(np.abs(reduce_pressure(p_med[e], t_med[e], zs) - p_ref))]
                          for e in p_med.index})

    lo, hi = 550.0, 700.0
    for _ in range(40):
        mid = (lo + hi) / 2
        sesgo = (resolver(mid) - z_dem[p_med.index]).median()
        # a mayor presión de referencia, cada estación necesita estar más alta para reducir a ella
        lo, hi = (lo, mid) if sesgo > 0 else (mid, hi)
    return resolver((lo + hi) / 2)


# ── reglas por estación ───────────────────────────────────────────────────────

def _stuck(s: pd.Series, exempt: pd.Series | None = None, horas: int = STUCK_HOURS) -> pd.Series:
    """Rachas de valor idéntico >= horas. `exempt` marca valores tolerados (niebla, calma)
    siempre que su racha no llegue a STUCK_EXEMPT_MAX_HOURS."""
    run_id = s.ne(s.shift()).cumsum()
    largo = s.groupby(run_id).transform("size")
    m = (largo >= horas) & s.notna()
    if exempt is not None:
        m &= ~(exempt & (largo < STUCK_EXEMPT_MAX_HOURS))
    return m


def _spike(s: pd.Series) -> pd.Series:
    med = s.rolling(SPIKE_WINDOW, center=True, min_periods=6).median()
    dev = (s - med).abs()
    mad = dev.rolling(SPIKE_WINDOW, center=True, min_periods=6).median()
    return dev > np.maximum(SPIKE_K * 1.4826 * mad, SPIKE_FLOOR)


def station_rules(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Máscaras de las reglas que solo necesitan la propia estación."""
    vacio = pd.DataFrame(False, index=df.index, columns=df.columns)
    out = {r: vacio.copy() for r in ("ZERO_RECORD", "RANGE", "STUCK", "SPIKE")}

    if {TEMP, RH, BP} <= set(df.columns):
        cero = (df[BP] == 0) & (df[TEMP] == 0) & (df[RH] == 0)
        for v in (TEMP, RH, BP):
            out["ZERO_RECORD"][v] = cero

    for v in df.columns:
        lo, hi = RANGES[v]
        out["RANGE"][v] = df[v].notna() & ~df[v].between(lo, hi)

    ya = out["ZERO_RECORD"] | out["RANGE"]
    limpio = df.mask(ya)
    for v in df.columns:
        s = limpio[v]
        if v == RH:
            out["STUCK"][v] = _stuck(s, exempt=s >= FOG_RH) & ~(s >= 99.5)   # 100 % sostenido es normal
        elif v == WS:
            out["STUCK"][v] = _stuck(s, exempt=s < CALM_WS)
        elif v == WD and WS in df:
            out["STUCK"][v] = _stuck(s.where(limpio[WS] >= CALM_WS))
        elif v == BP:
            out["STUCK"][v] = _stuck(s, horas=STUCK_HOURS_BP)
        else:
            out["STUCK"][v] = _stuck(s)

    limpio = df.mask(ya | out["STUCK"])
    for v in SPIKE_VARS:
        if v in df:
            out["SPIKE"][v] = _spike(limpio[v])
    return out


# ── regla de red ──────────────────────────────────────────────────────────────

def baro_deviation(clean: dict[str, pd.DataFrame], smooth: bool = True) -> pd.DataFrame:
    """Desvío (mbar) de la presión reducida de cada estación respecto a la mediana de sus
    vecinas (radio BARO_RADIUS_KM, sin contarse a sí misma).

    Con smooth=True (la regla de QC) se suaviza con la mediana móvil de 24 h: busca cambios
    de nivel, no ruido horario. El visor usa smooth=False para mostrar el desvío horario.
    """
    red = {}
    for est, df in clean.items():
        z = STATIONS[est].z_baro
        if est in BARO_EXCLUDE or z is None or BP not in df or TEMP not in df:
            continue
        t24 = df[TEMP].rolling("24h", center=True, min_periods=6).mean()
        red[est] = pd.Series(reduce_pressure(df[BP], t24, z), index=df.index)
    if not red:
        return pd.DataFrame()
    w = pd.DataFrame(red)
    dev = {}
    for est in w.columns:
        a = STATIONS[est]
        vecinas = [o for o in w.columns if o != est and np.hypot(
            STATIONS[o].easting - a.easting, STATIONS[o].northing - a.northing) <= BARO_RADIUS_KM * 1000]
        if len(vecinas) < BARO_MIN_NEIGHBORS:
            continue
        ref = w[vecinas].median(axis=1).where(w[vecinas].notna().sum(axis=1) >= BARO_MIN_NEIGHBORS)
        dev[est] = w[est] - ref
    dev = pd.DataFrame(dev)
    return dev.rolling("24h", center=True, min_periods=6).median() if smooth else dev


def _vecinas(est: str, candidatas, km: float) -> list[str]:
    a = STATIONS[est]
    return [o for o in candidatas if o != est and np.hypot(
        STATIONS[o].easting - a.easting, STATIONS[o].northing - a.northing) <= km * 1000]


def confirm_spikes(datos: dict[str, pd.DataFrame], reglas_por_est: dict[str, dict[str, pd.DataFrame]],
                   limpio: dict[str, pd.DataFrame]) -> None:
    """Retira de SPIKE los valores que siguen a sus vecinas (modifica reglas_por_est).

    Valor esperado = mediana de las vecinas + el desfase habitual de la estación respecto a
    ellas (mediana móvil de 72 h). Si el valor está a menos de SPIKE_NEIGHBOR_TOL de lo
    esperado, las vecinas vivieron el mismo cambio: es dato real. Sin valor esperado (vecinas
    sin dato) el descarte se mantiene.
    """
    for est, reglas in reglas_por_est.items():
        spike = reglas["SPIKE"]
        for v in SPIKE_VARS:
            if v not in spike or not spike[v].any():
                continue
            vs = [o for o in _vecinas(est, limpio, SPIKE_NEIGHBOR_KM) if v in limpio[o]]
            if len(vs) < 2:
                continue
            ref = pd.DataFrame({o: limpio[o][v] for o in vs}).median(axis=1).reindex(datos[est].index)
            base = datos[est][v].mask(reglas["ZERO_RECORD"][v] | reglas["RANGE"][v] | reglas["STUCK"][v])
            desfase = (base - ref).rolling("72h", center=True, min_periods=12).median()
            coherente = (datos[est][v] - (ref + desfase)).abs() < SPIKE_NEIGHBOR_TOL[v]
            spike[v] = spike[v] & ~coherente


def apply_qc(datos: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    """Aplica todas las reglas.

    Devuelve (datos limpios, tabla larga de descartes, desvío de presión suavizado).
    La tabla de descartes tiene columnas estacion_id, timestamp, variable, valor, regla.
    """
    reglas_por_est = {est: station_rules(df) for est, df in datos.items()}

    def limpiar() -> dict[str, pd.DataFrame]:
        out = {}
        for est, df in datos.items():
            m = pd.DataFrame(False, index=df.index, columns=df.columns)
            for r in reglas_por_est[est].values():
                m |= r
            out[est] = df.mask(m)
        return out

    limpio = limpiar()
    confirm_spikes(datos, reglas_por_est, limpio)
    limpio = limpiar()

    dev = baro_deviation(limpio)
    for est in dev.columns:
        mask = pd.DataFrame(False, index=datos[est].index, columns=datos[est].columns)
        mask[BP] = dev[est].reindex(datos[est].index).abs() > BARO_MAX_DEV
        reglas_por_est[est]["BARO_DEV"] = mask
        limpio[est] = limpio[est].mask(mask)

    filas = []
    for est, reglas in reglas_por_est.items():
        asignado = pd.DataFrame(False, index=datos[est].index, columns=datos[est].columns)
        for regla in RULES:
            if regla not in reglas:
                continue
            nuevo = reglas[regla] & ~asignado
            asignado |= nuevo
            largo = nuevo.stack()
            largo = largo[largo]
            if largo.empty:
                continue
            idx = largo.index
            filas.append(pd.DataFrame({
                "estacion_id": est,
                "timestamp": idx.get_level_values(0),
                "variable": idx.get_level_values(1),
                "valor": [datos[est].at[t, v] for t, v in idx],
                "regla": regla,
            }))
    flags = pd.concat(filas, ignore_index=True) if filas else pd.DataFrame(
        columns=["estacion_id", "timestamp", "variable", "valor", "regla"])
    return limpio, flags, dev
