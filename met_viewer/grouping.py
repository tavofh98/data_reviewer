"""Propone grupos de estaciones meteorológicas POR VARIABLE (T, HR y viento).

Uso:
    uv run python met_viewer/grouping.py [--dias 365] [--max 6]

Para cada variable, distancia entre dos estaciones = 1 − r, donde r es la correlación de sus
ANOMALÍAS: cada valor menos la media de esa misma hora del día en ±15 días de la propia
estación. Así se quitan el ciclo diario y la estación de cada una, y lo que se correlaciona es
el tiempo que comparten. (Restar la mediana de toda la red se probó y agrupa peor: pares a
16.6 km y 383 m de desnivel de media contra 5.0 km y 165 m.) Solo cuentan los pares con al
menos MIN_DIAS_COMUNES días en común.

El viento se agrupa por RÉGIMEN, no por anomalías: distancia = 1 − coseno entre los ciclos diarios
medios del vector de procedencia (u y v por hora). El coseno no depende de la escala, así que la
altura del sensor (2 m / 10 m) no manda; lo que se compara es de dónde viene el viento a cada hora.
La correlación de anomalías de velocidad era débil (r típica 0.15–0.35 a < 25 km) y quita el ciclo
diario, que es donde se ven los fallos de orientación (ver WIND_REVIEW.md). Los tramos de
stations.WIND_EXCLUDED no cuentan; una estación sin 60 días útiles va aparte, en su propia figura.

Agrupar por variable y no con una distancia combinada: una estación puede parecerse a unas
en temperatura y a otras en humedad o viento, y así ninguna se queda sin comparación.
Enlace promedio; se parte solo la rama que supera MAX_POR_GRUPO estaciones. Una estación que
queda sola se une al grupo de su estación más correlacionada; si ese grupo está lleno, forma
un grupo propio con sus 2 estaciones más correlacionadas (que aparecen así en dos grupos).
Ilo, única estación costera, va aparte.

Además calcula un agrupamiento ÚNICO (GROUPS_COMBINED) con la media de las distancias de T y
HR (sin viento; ver VARS_COMBINADO), con la misma regla para las estaciones sueltas: es el
que usa la vista por grupo.

Escribe groups_draft.py con un informe por variable (mediana de la estación en la ventana y
sus 3 estaciones más correlacionadas). El usuario lo revisa y lo guarda como groups.py (este
script nunca sobrescribe groups.py).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, to_tree
from scipy.spatial.distance import squareform

import data
import qc
from stations import STATIONS, WIND_EXCLUDED

VARS_GRUPO = (data.TEMP, data.RH, data.WS)
# El viento queda fuera del agrupamiento único: juntaba estaciones que en T no se parecen
# (Camp_Quellaveco con Chancado, RMSE 1.96 °C) y dejaba solas a Calacaja y Dique. Solo con T y
# HR la correlación interna de los grupos sube de 0.66–0.86 a 0.84–0.93 (medido 2025-2026).
VARS_COMBINADO = (data.TEMP, data.RH)
MIN_DIAS_COMUNES = 60
# Viento: parecido medio (coseno) mínimo con el resto del grupo para quedarse en él. Separa a
# Dique_pie_botadero (0.55, arrastrado al altiplano a 66 km) y conserva al miembro real más
# débil, Planta_Concentradora (0.68; medido 2025-09 → 2026-09).
MIN_PARECIDO_VIENTO = 0.60
MAX_POR_GRUPO = 6
APARTE = ("Ilo",)
SALIDA = Path(__file__).parent / "groups_draft.py"


def anomalia(s: pd.Series, dias: int = 31) -> pd.Series:
    """Valor menos la media de esa misma hora del día en una ventana centrada de `dias` días."""
    s = s.asfreq("h")
    tabla = s.groupby([s.index.normalize(), s.index.hour]).first().unstack()   # día × hora
    clim = tabla.rolling(dias, center=True, min_periods=10).mean()
    a = (tabla - clim).stack()
    a.index = a.index.get_level_values(0) + pd.to_timedelta(a.index.get_level_values(1), unit="h")
    return a


def distancia(limpio: dict[str, pd.DataFrame], var: str, rellenar: bool = True) -> pd.DataFrame:
    """Matriz 1 − r de las anomalías de `var`. Pares sin datos en común: 1 (o NaN si rellenar=False)."""
    w = pd.DataFrame({e: anomalia(df[var]) for e, df in limpio.items() if var in df and e not in APARTE})
    w = w.loc[:, w.notna().sum() >= 24 * MIN_DIAS_COMUNES]
    d = (1 - w.corr(min_periods=24 * MIN_DIAS_COMUNES)).clip(lower=0)
    d = (d.fillna(1.0) if rellenar else d).to_numpy(copy=True)
    np.fill_diagonal(d, 0.0)
    return pd.DataFrame(d, index=w.columns, columns=w.columns)


def viento_util(est: str, df: pd.DataFrame) -> pd.DataFrame:
    """Quita a la estación sus tramos de stations.WIND_EXCLUDED."""
    fuera = pd.Series(False, index=df.index)
    for a, b in WIND_EXCLUDED.get(est, []):
        tramo = pd.Series(True, index=df.index)
        if a:
            tramo &= df.index >= pd.Timestamp(a)
        if b:
            tramo &= df.index < pd.Timestamp(b)
        fuera |= tramo
    return df[~fuera]


def ciclo_viento(df: pd.DataFrame) -> np.ndarray | None:
    """Ciclo diario medio del vector de procedencia: 24 valores de u y luego 24 de v.
    Las calmas pesan cero. None si hay menos de MIN_DIAS_COMUNES días o falta alguna hora."""
    df = df[[data.WS, data.WD]].dropna()
    if len(df) < 24 * MIN_DIAS_COMUNES:
        return None
    rad = np.deg2rad(df[data.WD])
    ws = df[data.WS].where(df[data.WS] >= qc.CALM_WS, 0.0)
    uv = pd.DataFrame({"u": ws * np.sin(rad), "v": ws * np.cos(rad)}).groupby(df.index.hour).mean()
    uv = uv.reindex(range(24))
    return None if uv.isna().any().any() else np.concatenate([uv.u.to_numpy(), uv.v.to_numpy()])


def distancia_regimen(limpio: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, list[str]]:
    """Matriz 1 − coseno entre ciclos diarios del vector de viento, y estaciones que quedan fuera
    (sin datos útiles tras WIND_EXCLUDED)."""
    ciclos, fuera = {}, []
    for e, df in sorted(limpio.items()):
        if e in APARTE or data.WS not in df or data.WD not in df:
            continue
        c = ciclo_viento(viento_util(e, df))
        if c is None:
            fuera.append(e)
        else:
            ciclos[e] = c
    m = pd.DataFrame(ciclos)
    m = m / np.linalg.norm(m, axis=0)
    d = (1 - m.T @ m).clip(lower=0).to_numpy(copy=True)
    np.fill_diagonal(d, 0.0)
    return pd.DataFrame(d, index=m.columns, columns=m.columns), fuera


def separar_sueltas(dist: pd.DataFrame, grupos: list[list[str]], minimo: float) -> tuple[list[list[str]], list[str]]:
    """Saca de su grupo a la estación cuyo parecido medio (1 − distancia) con el resto es < minimo."""
    quedan, sueltas = [], []
    for g in grupos:
        par = 1 - dist.loc[g, g]
        medio = (par.sum() - 1) / max(len(g) - 1, 1)
        sueltas += [e for e in g if len(g) > 1 and medio[e] < minimo]
        resto = [e for e in g if e not in sueltas]
        if resto:
            quedan.append(resto)
    return quedan, sueltas


def distancia_combinada(dists: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Media de las distancias por variable (sin rellenar); cada par promedia solo las variables
    en que ambos tienen datos en común. Sin ninguna en común: 1."""
    est = sorted(set().union(*(d.index for d in dists.values())))
    pilas = [d.reindex(index=est, columns=est).to_numpy() for d in dists.values()]
    with np.errstate(invalid="ignore"):
        m = np.nanmean(np.stack(pilas), axis=0)
    m = np.where(np.isnan(m), 1.0, m)
    np.fill_diagonal(m, 0.0)
    return pd.DataFrame(m, index=est, columns=est)


def cortar(dist: pd.DataFrame, max_por_grupo: int, absorber: bool = True) -> list[list[str]]:
    """Parte el dendrograma de arriba abajo, solo las ramas con más de max_por_grupo hojas.
    Con absorber=True une cada estación suelta al grupo de su estación más correlacionada."""
    raiz = to_tree(linkage(squareform(dist.to_numpy(), checks=False), "average"))
    grupos, pendientes = [], [raiz]
    while pendientes:
        nodo = pendientes.pop()
        if nodo.get_count() <= max_por_grupo:
            grupos.append(sorted(dist.index[i] for i in nodo.pre_order()))
        else:
            pendientes += [nodo.get_left(), nodo.get_right()]

    for suelta in [g[0] for g in grupos if len(g) == 1] if absorber else []:
        grupos = [g for g in grupos if g != [suelta]]
        cercanas = dist[suelta].drop(suelta).nsmallest(2).index.tolist()
        destino = next(g for g in grupos if cercanas[0] in g)
        if len(destino) < max_por_grupo:
            destino.append(suelta)
            destino.sort()
        else:
            # grupo lleno: grupo propio con sus 2 más correlacionadas, que quedan en dos grupos
            grupos.append(sorted([suelta] + cercanas))
    return sorted(grupos, key=lambda g: (-len(g), g[0]))


def _km(a: str, b: str) -> float:
    sa, sb = STATIONS[a], STATIONS[b]
    return float(np.hypot(sa.easting - sb.easting, sa.northing - sb.northing) / 1000)


def informe(var: str, dist: pd.DataFrame, grupos: list[list[str]], mediana: pd.Series,
            medida: str = "r") -> list[str]:
    """Por grupo: parecido medio interno (1 − distancia). Por estación: su mediana y sus 3
    estaciones más parecidas. `medida` nombra el parecido: r (correlación) o cos (régimen)."""
    lineas = [f"== {var}"]
    for i, g in enumerate(grupos, 1):
        interna = dist.loc[g, g].to_numpy()[np.triu_indices(len(g), 1)]
        lineas.append(f"G{i} ({len(g)}), {medida} medio {1 - interna.mean():.2f}: {', '.join(g)}")
    lineas.append("")
    for e in mediana.sort_values().index:
        if e not in dist:
            continue
        cerca = dist[e].drop(e).nsmallest(3)
        txt = "; ".join(f"{o} {medida}={1 - d:.2f} ({_km(e, o):.0f} km)" for o, d in cerca.items())
        lineas.append(f"{e:22s} mediana {mediana[e]:6.1f} -> {txt}")
    return lineas


def escribir_borrador(por_var: dict[str, list[list[str]]], combinados: list[list[str]],
                      lineas: list[str], periodo: str) -> None:
    bloques = []
    for var, grupos in por_var.items():
        cuerpo = "\n".join(f"        {g!r}," for g in grupos)
        bloques.append(f"    {var!r}: [\n{cuerpo}\n        {list(APARTE)!r},\n    ],")
    cuerpo_comb = "\n".join(f"    {g!r}," for g in combinados + [list(APARTE)])
    comentario = "\n".join(f"# {l}" if l else "#" for l in lineas)
    SALIDA.write_text(
        '"""Borrador de grupos generado por grouping.py. Revisar y guardar como groups.py.\n\n'
        "GROUPS: por variable. Clave = variable; valor = lista de grupos (una figura por grupo).\n"
        "    Una estación puede estar en más de un grupo de la misma variable.\n"
        "GROUPS_COMBINED: un solo agrupamiento para todas las variables (distancia combinada de\n"
        '    T y HR). Lo usa la vista por grupo."""\n\n'
        f"# Periodo: {periodo}\n{comentario}\n\n"
        "GROUPS: dict[str, list[list[str]]] = {\n" + "\n".join(bloques) + "\n}\n\n"
        f"GROUPS_COMBINED: list[list[str]] = [\n{cuerpo_comb}\n]\n",
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dias", type=int, default=365)
    ap.add_argument("--max", type=int, default=MAX_POR_GRUPO, help="estaciones máximas por grupo")
    args = ap.parse_args()

    fin = pd.Timestamp.now().normalize() + pd.Timedelta(days=1)
    ini = fin - pd.Timedelta(days=args.dias)
    limpio, _, _ = qc.apply_qc(data.load(ini, fin))

    por_var, dists, lineas = {}, {}, []
    for var in VARS_GRUPO:
        fuera = []
        if var == data.WS:
            dists[var], fuera = distancia_regimen(limpio)
        else:
            dists[var] = distancia(limpio, var)
        grupos = cortar(dists[var], args.max)
        sueltas = []
        if var == data.WS:
            grupos, sueltas = separar_sueltas(dists[var], grupos, MIN_PARECIDO_VIENTO)
        mediana = pd.Series({e: df[var].median() for e, df in limpio.items() if var in df})
        lineas += informe(var, dists[var], grupos, mediana, "cos" if var == data.WS else "r")
        if sueltas:
            lineas.append(f"Sin pareja (parecido medio < {MIN_PARECIDO_VIENTO}), una figura cada una: {', '.join(sueltas)}")
        if fuera:
            lineas.append(f"Fuera del agrupamiento (stations.WIND_EXCLUDED), una figura cada una: {', '.join(fuera)}")
        por_var[var] = grupos + [[e] for e in sueltas + fuera]
        lineas.append("")

    # agrupamiento único (vista por grupo): solo T y HR, con las sueltas unidas a su pareja
    comb = distancia_combinada({v: distancia(limpio, v, rellenar=False) for v in VARS_COMBINADO})
    combinados = cortar(comb, args.max)
    lineas.append("== combinado (T, HR)")
    for i, g in enumerate(combinados, 1):
        interna = comb.loc[g, g].to_numpy()[np.triu_indices(len(g), 1)]
        media = f"{1 - interna.mean():.2f}" if len(g) > 1 else "—"
        lineas.append(f"G{i} ({len(g)}), r medio {media}: {', '.join(g)}")
    print("\n".join(lineas))
    escribir_borrador(por_var, combinados, lineas, f"{ini:%Y-%m-%d} → {fin:%Y-%m-%d}")
    print(f"Borrador: {SALIDA}")


if __name__ == "__main__":
    main()
