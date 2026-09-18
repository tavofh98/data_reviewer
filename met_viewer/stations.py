"""Metadato de las estaciones meteorológicas: ubicación, altitud y sensores.

Fuentes:
- Coordenadas: `Estaciones AAQ.kmz` (raíz del workspace), convertidas a UTM 19S (EPSG:32719).
  Las de `control_calidad_aaq/config.py` están desplazadas entre 8 y 69 km: no usarlas.
- `z_dem`: SRTM 30 m (OpenTopoData) en el punto del KMZ, consultado el 2026-09-18.
- `z_baro`: altitud que hace coherente la presión de la estación con la red (ver
  `qc.barometric_elevation`). Es la que usa la reducción de presión.
- Sensores: tabla de partes de campo del usuario, completada con la huella de resolución de
  los datos (pluviómetro ClimaVUE 0.017 mm vs cubeta 0.1 mm). `# inferido` = fecha deducida
  de los datos, sin parte que la respalde.
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT.parents[2] / "database_duck" / "anglo_ambiental.db"

# Variables que se reportan: la norma vive en anglo_reporte/matrices.py (sin dependencias).
_spec = importlib.util.spec_from_file_location("_matrices", ROOT.parent / "anglo_reporte" / "matrices.py")
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]
REPORTED: dict[str, list[str]] = _mod.VARIABLES_REPORTE["meteorologia"]


@dataclass(frozen=True)
class Sensor:
    group: str   # "viento", "lluvia", "termohigro", "presion"
    kind: str    # "climavue", "torre", "young", "hygrovue", "barometro"
    since: str   # fecha ISO desde la que el programa toma la variable de este sensor


@dataclass(frozen=True)
class Station:
    easting: float
    northing: float
    z_dem: float
    z_baro: float | None          # None: sin barómetro, o fuera de la reducción (Ilo, a 16 m)
    sensors: tuple[Sensor, ...] = field(default_factory=tuple)


_INICIO = "2019-01-01"


def _cv(*extra: Sensor) -> tuple[Sensor, ...]:
    """Estación ClimaVUE: por defecto todo sale del ClimaVUE; `extra` añade cambios posteriores."""
    base = tuple(Sensor(g, "climavue", _INICIO) for g in ("viento", "lluvia", "termohigro", "presion"))
    return base + extra


def _torre(*extra: Sensor) -> tuple[Sensor, ...]:
    return (Sensor("viento", "torre", _INICIO), Sensor("lluvia", "young", _INICIO)) + extra


# z_baro: salida de calibrate_baro.py el 2026-09-18 (últimos 365 días); |z_baro − z_dem| ≤ 30 m.
# No recalcular por rutina: si se recalcula, un cambio de nivel del barómetro se absorbe.
STATIONS: dict[str, Station] = {
    "Altarani":              Station(330585, 8107323, 3744, 3744, _torre()),
    "Alto_Quellaveco":       Station(328544, 8106357, 4139, 4129, _torre()),
    "Alto_Tala":             Station(321934, 8108393, 3454, 3452, (Sensor("viento", "torre", _INICIO),)),
    "Apacheta":              Station(325432, 8100352, 3736, 3750,
                                     _cv(Sensor("lluvia", "young", "2025-12-01"))),  # inferido
    "Calacaja":              Station(306544, 8096668, 2329, 2336, _cv()),
    "Calientes1":            Station(317381, 8103660, 3097, 3116,
                                     _cv(Sensor("lluvia", "young", "2025-05-01"))),  # inferido
    "Camp_Quellaveco":       Station(326534, 8107949, 3598, 3628, _torre()),
    # En el KMZ, Campamento Quellaveco comparte coordenada con Botadero Altaranito Norte: por confirmar.
    "Cerro_Salviani":        Station(321190, 8104830, 3580, 3571,
                                     _cv(Sensor("lluvia", "young", "2026-02-12"),
                                         Sensor("termohigro", "hygrovue", "2026-02-12"))),
    "Chalsos":               Station(322381, 8095276, 3336, 3337, _cv()),
    "Chancado_primario":     Station(326017, 8108351, 3468, 3452,
                                     _cv(Sensor("lluvia", "young", "2025-03-15"),
                                         Sensor("presion", "barometro", "2025-03-15"))),  # año inferido
    "Charaque":              Station(324788, 8110108, 3637, 3660,
                                     _cv(Sensor("lluvia", "young", "2025-12-01"))),  # inferido
    "Cortadera":             Station(321591, 8099288, 3385, 3374, _torre()),
    "DME3_Cortadera":        Station(314708, 8097374, 2900, 2922, _cv()),
    "Dique_pie_botadero":    Station(323267, 8108169, 3330, 3320, _cv()),
    "Huachunta":             Station(355567, 8153330, 4410, 4410, _torre()),
    "Ilo":                   Station(267774, 8034132, 46, None,
                                     _cv(Sensor("lluvia", "young", "2025-07-01"))),  # inferido; ClimaVUE sin confirmar
    "Mina_Norte":            Station(327257, 8110014, 3972, None,
                                     (Sensor("viento", "torre", _INICIO), Sensor("lluvia", "young", _INICIO),
                                      Sensor("viento", "climavue", "2026-08-28"))),
    "Minas_Sur":             Station(329299, 8106779, 4119, 4110, _torre()),
    "PMC-4_met":             Station(316969, 8096187, 2884, None, (Sensor("lluvia", "young", _INICIO),)),
    "Papujune":              Station(322640, 8106523, 3777, 3775, _torre()),
    "Planta_Concentradora":  Station(324023, 8105777, 3868, 3873,
                                     _cv(Sensor("lluvia", "young", "2026-02-01"))),
    "Sarallenque":           Station(328371, 8108822, 3718, None, _torre()),
    "Sarallenque_MQG-15-02": Station(328939, 8110942, 4251, 4263, _cv()),
    "Tala-1":                Station(322943, 8108610, 3568, 3573, _torre()),
    "Tala_Legal":            Station(321308, 8108678, 3306, 3317, _torre()),
    "Titire":                Station(350186, 8168738, 4342, 4327,
                                     _cv(Sensor("lluvia", "young", "2026-02-11"))),
    "Vizcachas":             Station(355630, 8159304, 4387, 4388, _torre()),
}


def sensor_at(station: str, group: str, when: str) -> str | None:
    """Tipo de sensor vigente para `group` en la fecha `when` (ISO), o None si no consta."""
    vigentes = [s for s in STATIONS[station].sensors if s.group == group and s.since <= when]
    return max(vigentes, key=lambda s: s.since).kind if vigentes else None
