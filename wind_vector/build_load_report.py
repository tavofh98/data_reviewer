"""Genera ``output/CARGA.md`` con el informe de carga y la prueba de consistencia.

Ejecutar desde ``explorar_qaqc/``:  ``uv run python -m wind_vector.build_load_report``

Para cada estación calcula con los datos reales: rangos, filas, duplicados,
horas completas/incompletas, huecos largos, verificación de la convención de
tiempo (fin de intervalo) y la comparación entre las tablas de 5 y 60 min.
"""

import numpy as np
import pandas as pd

from wind_vector import loader

# Tolerancias de la prueba de consistencia.
TOL_DIR = 0.1  # grados; redondeo FP2 de las dos tablas
TOL_WS = 0.01  # m/s; resolución FP2 por encima de 10 m/s
EPS = 1e-9  # evita fallos espurios por coma flotante justo en el límite
LONG_GAP_HOURS = 6  # huecos de al menos esta duración se consideran largos
SLOT_COLUMNS = [f"{{}}_m{slot:02d}" for slot in range(1, loader.N_SLOTS + 1)]


def slot_matrix(aligned, variable):
    """Matriz (horas x 12) de una variable en los registros de 5 min."""
    return aligned[[template.format(variable) for template in SLOT_COLUMNS]]


def gap_summary(index, expected_step):
    """Huecos de un índice temporal: nº total, nº largos y los 5 más largos."""
    deltas = pd.Series(index[1:] - index[:-1], index=index[1:])
    gaps = deltas[deltas > expected_step]
    long_gaps = gaps[gaps >= pd.Timedelta(hours=LONG_GAP_HOURS)]
    top = long_gaps.sort_values(ascending=False).head(5)
    rows = [
        f"{end - gap} -> {end} ({gap.total_seconds() / 3600:.1f} h)"
        for end, gap in top.items()
    ]
    return len(gaps), len(long_gaps), rows


def time_convention(aligned, five_min):
    """% de coincidencia con convención fin de intervalo frente a inicio de intervalo.

    Se compara en horas completas: media de WS_ms_Avg de los 12 registros y
    máximo de WS_ms_Max de los 12 contra la tabla de 60 min.
    """
    full = aligned[aligned["n_5min"] == loader.N_SLOTS]
    result = {}
    for name, sign in [("fin", -1), ("inicio", 1)]:
        windows = {}
        for variable in ["WS_ms_Avg", "WS_ms_Max"]:
            windows[variable] = np.column_stack(
                [
                    five_min[variable]
                    .reindex(full.index + sign * pd.Timedelta(minutes=5 * k))
                    .to_numpy()
                    for k in range(loader.N_SLOTS)
                ]
            )
        mean_ok = np.abs(windows["WS_ms_Avg"].mean(axis=1) - full["WS_ms_Avg_h"]) <= TOL_WS + EPS
        max_ok = np.abs(windows["WS_ms_Max"].max(axis=1) - full["WS_ms_Max_h"]) <= 1e-6
        result[name] = (mean_ok.mean(), max_ok.mean())
    return result


def consistency(aligned):
    """Prueba de consistencia 5 min vs 60 min en horas completas.

    Devuelve un DataFrame con el error de dirección y de velocidad de cada hora
    completa, más banderas para explicar los fallos.
    """
    full = aligned[aligned["n_5min"] == loader.N_SLOTS].copy()
    direction = slot_matrix(full, "WindDir_Avg")
    speed = slot_matrix(full, "WS_ms_Avg")
    full["dir_diff"] = direction.mean(axis=1) - full["WindDir_Avg_h"]
    full["ws_diff"] = speed.mean(axis=1) - full["WS_ms_Avg_h"]
    full["north_cross"] = (direction.min(axis=1) < 90) & (direction.max(axis=1) > 270)
    full["has_calm"] = (speed == 0).any(axis=1)
    full["dir_ok"] = full["dir_diff"].abs() <= TOL_DIR + EPS
    full["ws_ok"] = full["ws_diff"].abs() <= TOL_WS + EPS
    return full


def failure_cause(row):
    """Causa (excluyente, por prioridad) de un fallo de dirección."""
    if not row["ws_ok"]:
        return "WS_ms_Avg también discrepa"
    if row["has_calm"]:
        return "WS coincide; algún registro de 5 min en calma (WS=0)"
    return "WS coincide, sin calma: sin causa identificada"


def pct(part, total):
    return f"{100 * part / total:.2f} %" if total else "n/d"


def station_section(station):
    """Texto Markdown con el informe de una estación."""
    raw_5min = loader._read_toa5(loader.DIR_5MIN / f"{loader.STATIONS[station]}_Table3.dat")
    raw_hourly = loader._read_toa5(loader.DIR_HOURLY / f"{loader.STATIONS[station]}_Table1.dat")
    five_min = loader.load_5min(station)
    hourly = loader.load_hourly(station)
    aligned = loader.aligned_hours(station)

    lines = [f"## {station.capitalize()}", ""]

    # Filas, rangos y duplicados.
    lines += [
        "### Tablas cargadas",
        "",
        "| Tabla | Desde | Hasta | Filas en fichero | Timestamps duplicados (filas sobrantes) | Duplicados con viento distinto | Filas tras deduplicar | Fuera de rejilla |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, raw, clean, step in [
        ("5 min (Table3)", raw_5min, five_min, 5),
        ("60 min (Table1)", raw_hourly, hourly, 60),
    ]:
        duplicated = raw[raw["TIMESTAMP"].duplicated(keep=False)]
        distinct = duplicated.groupby("TIMESTAMP")[loader.WIND_COLUMNS].nunique(dropna=False)
        conflicting = int((distinct > 1).any(axis=1).sum())
        off_grid = int(((clean.index.minute % step != 0) | (clean.index.second != 0)).sum())
        lines.append(
            f"| {name} | {clean.index.min()} | {clean.index.max()} | {len(raw)} "
            f"| {int(raw['TIMESTAMP'].duplicated().sum())} | {conflicting} "
            f"| {len(clean)} | {off_grid} |"
        )
    lines += [
        "",
        "Qué se hizo: de cada timestamp duplicado se conserva el último registro "
        "en orden de fichero (ver docstring de `loader._deduplicate`) y se ordena por tiempo.",
        "",
    ]
    # Comparación de reglas de deduplicación sobre la prueba de dirección.
    first = (
        raw_5min.drop_duplicates("TIMESTAMP", keep="first")
        .set_index("TIMESTAMP")
        .sort_index()["WindDir_Avg"]
    )
    full_idx = aligned.index[aligned["n_5min"] == loader.N_SLOTS]
    first_matrix = np.column_stack(
        [
            first.reindex(full_idx - pd.Timedelta(minutes=5 * k)).to_numpy()
            for k in range(loader.N_SLOTS)
        ]
    )
    first_ok = (
        np.abs(np.nanmean(first_matrix, axis=1) - aligned.loc[full_idx, "WindDir_Avg_h"])
        <= TOL_DIR + EPS
    ).mean()

    # Horas completas e incompletas.
    counts = aligned["n_5min"].value_counts().sort_index()
    complete = int(counts.get(loader.N_SLOTS, 0))
    hourly_nan = int(
        aligned[["WS_ms_Avg_h", "WindDir_Avg_h"]].isna().any(axis=1).sum()
    )
    lines += [
        "### Horas",
        "",
        f"- Horas en la tabla de 60 min: {len(aligned)}.",
        f"- Con los 12 registros de 5 min válidos: {complete} ({pct(complete, len(aligned))}).",
        f"- Incompletas: {len(aligned) - complete} ({pct(len(aligned) - complete, len(aligned))}); "
        f"de ellas sin ningún registro de 5 min: {int(counts.get(0, 0))}.",
        f"- Horas con WS_ms_Avg_h o WindDir_Avg_h nulos en la tabla de 60 min: {hourly_nan}.",
        "- Distribución de `n_5min`: "
        + ", ".join(f"{k}: {v}" for k, v in counts.items())
        + ".",
        "",
    ]

    # Huecos largos.
    lines += [f"### Huecos (>= {LONG_GAP_HOURS} h son largos)", ""]
    for name, index, step in [
        ("5 min", five_min.index, pd.Timedelta(minutes=5)),
        ("60 min", hourly.index, pd.Timedelta(hours=1)),
    ]:
        total, long_count, top = gap_summary(index, step)
        lines.append(f"- Tabla de {name}: {total} huecos en total, {long_count} largos.")
        lines += [f"  - {text}" for text in top]
    lines.append("")

    # Convención de tiempo.
    convention = time_convention(aligned, five_min)
    lines += [
        "### Verificación de la convención de tiempo (horas completas)",
        "",
        "| Convención | Media de 12 WS_ms_Avg = WS_ms_Avg_h | Máx. de 12 WS_ms_Max = WS_ms_Max_h |",
        "|---|---|---|",
        f"| Fin de intervalo (HH-1:05 ... HH:00) | {100 * convention['fin'][0]:.2f} % | {100 * convention['fin'][1]:.2f} % |",
        f"| Inicio de intervalo (HH:00 ... HH:55) | {100 * convention['inicio'][0]:.2f} % | {100 * convention['inicio'][1]:.2f} % |",
        "",
    ]

    # Prueba de consistencia.
    result = consistency(aligned)
    total = len(result)
    dir_ok = int(result["dir_ok"].sum())
    ws_ok = int(result["ws_ok"].sum())
    strict_ws = int((result["ws_diff"].abs() <= 0.002 + EPS).sum())
    lines += [
        "### Prueba de consistencia (horas con los 12 registros)",
        "",
        f"Horas evaluadas: {total}.",
        "",
        f"- **WindDir_Avg**: media aritmética de los 12 de 5 min = WindDir_Avg_h (|dif| <= {TOL_DIR}°): "
        f"{dir_ok} horas, {pct(dir_ok, total)}. Fallan {total - dir_ok}.",
        f"- **WS_ms_Avg**: media de los 12 de 5 min = WS_ms_Avg_h (|dif| <= {TOL_WS} m/s): "
        f"{ws_ok} horas, {pct(ws_ok, total)}. Fallan {total - ws_ok}. "
        f"(Con tolerancia estricta 0.002 m/s: {pct(strict_ws, total)}.)",
        f"- Regla de deduplicación alternativa (primer registro en vez del último), "
        f"cumplimiento de dirección: {100 * first_ok:.2f} % frente a {pct(dir_ok, total)} con el último.",
        "",
        "Cruce por el norte (algún WindDir_Avg de 5 min < 90° y otro > 270° en la hora):",
        "",
        "| Grupo | Horas | Cumplen dirección |",
        "|---|---|---|",
    ]
    for label, mask in [
        ("Con cruce por el norte", result["north_cross"]),
        ("Sin cruce por el norte", ~result["north_cross"]),
    ]:
        lines.append(f"| {label} | {int(mask.sum())} | {pct(int(result.loc[mask, 'dir_ok'].sum()), int(mask.sum()))} |")
    lines.append("")

    failures = result[~result["dir_ok"]]
    if len(failures):
        causes = failures.apply(failure_cause, axis=1).value_counts()
        lines += [
            "Por qué falla la dirección (causas excluyentes, por prioridad):",
            "",
            "| Causa | Horas |",
            "|---|---|",
        ]
        lines += [f"| {cause} | {count} |" for cause, count in causes.items()]
        lines += [
            "",
            f"Fallos con cruce por el norte: {int(failures['north_cross'].sum())} de {len(failures)}. "
            f"Error absoluto de los fallos (grados): mediana {failures['dir_diff'].abs().median():.2f}, "
            f"máximo {failures['dir_diff'].abs().max():.2f}.",
            "",
        ]
    return "\n".join(lines)


def build():
    header = [
        "# Informe de carga y alineación de viento",
        "",
        "Generado por `wind_vector/build_load_report.py`. Todas las cifras salen de los datos.",
        "",
        "- Convención: el TIMESTAMP de Campbell es el fin del intervalo; la hora HH:00 agrupa "
        "los registros de 5 min HH-1:05 (m01) ... HH:00 (m12).",
        f"- Registro de 5 min válido: WS_ms_Avg y WindDir_Avg no nulos. Hora completa: `n_5min` = {loader.N_SLOTS}.",
        f"- Tolerancias: dirección {TOL_DIR}° (redondeo FP2); velocidad {TOL_WS} m/s.",
        "- La prueba de consistencia solo se evalúa en horas completas: las incompletas "
        "no pueden compararse (faltan registros), así que NaN y huecos quedan fuera de ese porcentaje.",
        "",
    ]
    sections = [station_section(station) for station in loader.STATIONS]
    text = "\n".join(header + sections)
    (loader.OUTPUT_DIR / "CARGA.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    print(build())
