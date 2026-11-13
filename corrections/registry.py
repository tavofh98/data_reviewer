"""Registro de intervenciones sobre los datos crudos: qué se corrige, dónde, cómo y por qué.

Cada intervención afecta a una variable de una estación en un intervalo de horas (start, end],
con la misma convención de la base: la marca de tiempo es el final de la hora. Los intervalos de
una misma estación y variable no pueden solaparse (build_corrections.py lo comprueba).

Tipos:
- "rotation": suma `parameter` grados a la dirección. Si hay registros de 5 min de la estación,
  la hora se recalcula como media vectorial de los registros girados; si no, se gira la media
  horaria de la base.
- "exclusion": la celda queda vacía en la vista; el valor crudo se conserva en la tabla de ajustes.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Correction:
    correction_id: str
    station_id: str
    variable: str
    start: str               # exclusivo, final de hora
    end: str                 # inclusivo, final de hora
    kind: str                # "rotation" | "exclusion"
    parameter: float | None  # grados para "rotation"; None para "exclusion"
    reason: str
    reference: str


CORRECTIONS: tuple[Correction, ...] = (
    Correction(
        "MN-2025-11-transition", "Mina_Norte", "WindDir_Avg", "2025-11-14 00:00", "2025-11-26 00:00",
        "exclusion", None,
        "Traslado del shelter tras el daño de paneles: el giro aparece en dos pasos y la orientación "
        "de cada día es incierta.",
        "FINDINGS.md §9, Mina_Norte frente a Oeste 1"),
    Correction(
        "MN-B-rotation", "Mina_Norte", "WindDir_Avg", "2025-11-26 00:00", "2026-08-26 00:00",
        "rotation", 53.0,
        "WindSonic con la marca N girada en el tramo B. Giro estimado contra el tramo C (ClimaVUE) "
        "con Oeste 1 por sectores: −53.6°. Se aplica a todas las horas porque el giro es del sensor.",
        "FINDINGS.md §9, Corrección del tramo B"),
    Correction(
        "MN-2026-08-sensor-swap", "Mina_Norte", "WindDir_Avg", "2026-08-26 00:00", "2026-08-28 00:00",
        "exclusion", None,
        "Cable cortado y WindSonic retirado antes de instalar el ClimaVUE: orientación desconocida.",
        "FINDINGS.md §9, Mina_Norte frente a Oeste 1"),
)
