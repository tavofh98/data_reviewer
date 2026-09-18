"""Visor de meteorología agrupado por asociación.

Uso:
    uv run python met_viewer/main.py                       # últimos 30 días, corte 08:00
    uv run python met_viewer/main.py --ultimos 7 --corte 0
    uv run python met_viewer/main.py --inicio "2026-08-01" --fin "2026-09-01"

El intervalo es semiabierto [inicio, fin), como en anglo_reporte. Salida en met_viewer/output/:
    meteorologia_por_variable.html   una sección por variable, una figura por grupo (GROUPS)
    meteorologia_por_grupo.html      una sección por grupo, cuatro figuras (GROUPS_COMBINED)
    qc_flags.csv                     descartes del QC dentro de la ventana
Los grupos salen de groups.py; si no existe, de groups_draft.py.
"""
from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import pandas as pd

import data
import qc
import viewer

SALIDA = Path(__file__).parent / "output"
MARGEN = pd.Timedelta(days=2)     # contexto para las reglas móviles (24 h) y las rachas


def periodo(argv: list[str] | None = None) -> tuple[pd.Timestamp, pd.Timestamp]:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inicio"); ap.add_argument("--fin")
    ap.add_argument("--ultimos", type=int); ap.add_argument("--corte", type=int)
    a = ap.parse_args(argv)
    if a.inicio or a.fin:
        if a.ultimos is not None or a.corte is not None:
            ap.error("no mezclar --inicio/--fin con --ultimos/--corte")
        if not (a.inicio and a.fin):
            ap.error("el modo explícito requiere --inicio y --fin")
        ini, fin = pd.Timestamp(a.inicio), pd.Timestamp(a.fin)
        if fin <= ini:
            ap.error("fin debe ser posterior a inicio")
        return ini, fin
    n, h = a.ultimos or 30, 8 if a.corte is None else a.corte
    if n <= 0 or not 0 <= h <= 23:
        ap.error("--ultimos > 0 y --corte entre 0 y 23")
    fin = pd.Timestamp.now().normalize() + pd.Timedelta(hours=h)
    return fin - pd.Timedelta(days=n), fin


def cargar_grupos() -> tuple[dict[str, list[list[str]]], list[list[str]] | None, bool]:
    """(GROUPS por variable, GROUPS_COMBINED o None, es_borrador) de groups.py o groups_draft.py.

    Un GROUPS que sea una lista simple se usa para todas las variables y como agrupamiento único.
    """
    for modulo, borrador in (("groups", False), ("groups_draft", True)):
        if (Path(__file__).parent / f"{modulo}.py").exists():
            m = importlib.import_module(modulo)
            por_var, combinados = m.GROUPS, getattr(m, "GROUPS_COMBINED", None)
            if isinstance(por_var, list):
                combinados = combinados or por_var
                por_var = {v: por_var for v in (data.TEMP, data.RH, data.WS)}
            return por_var, combinados, borrador
    raise SystemExit("No hay groups.py ni groups_draft.py: corre antes met_viewer/grouping.py")


def main() -> None:
    ini, fin = periodo()
    por_var, combinados, borrador = cargar_grupos()
    datos = data.load(ini - MARGEN, fin)
    limpio, flags, _ = qc.apply_qc(datos)
    dev = qc.baro_deviation(limpio, smooth=False)

    recorte = lambda x: x[(x.index >= ini) & (x.index < fin)]
    limpio = {e: recorte(df) for e, df in limpio.items()}
    dev = recorte(dev)
    flags = flags[(flags.timestamp >= ini) & (flags.timestamp < fin)]

    for var, gs in por_var.items():
        con_dato = {e for e, df in limpio.items() if var in df and df[var].notna().any()}
        sin_grupo = sorted(con_dato - {e for g in gs for e in g})
        if sin_grupo:
            print(f"Aviso [{var}]: estaciones con datos que no están en ningún grupo: {', '.join(sin_grupo)}")

    salidas = [("meteorologia_por_variable.html",
                viewer.construir_por_variable(por_var, limpio, flags, dev, ini, fin, borrador))]
    if combinados:
        salidas.append(("meteorologia_por_grupo.html",
                        viewer.construir_por_grupo(combinados, limpio, flags, dev, ini, fin, borrador)))
    else:
        print("Aviso: el archivo de grupos no tiene GROUPS_COMBINED; no se genera la vista por grupo")
    for nombre, html_txt in salidas:
        viewer.guardar(html_txt, SALIDA / nombre)
    flags.to_csv(SALIDA / "qc_flags.csv", index=False)

    n_grupos = " · ".join(f"{v}: {len(g)}" for v, g in por_var.items())
    print(f"Periodo {ini} → {fin} | grupos por variable {n_grupos} | combinados "
          f"{len(combinados) if combinados else '-'}{' (borrador)' if borrador else ''} | {len(flags)} descartes")
    print(flags.groupby(["regla", "variable"]).size().unstack(fill_value=0).to_string() if len(flags) else "sin descartes")
    for nombre, _ in salidas:
        print(f"HTML: {SALIDA / nombre}")


if __name__ == "__main__":
    main()
