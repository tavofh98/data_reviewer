"""Contraste de los programas CRBasic con los datos: ¿el desfase de −7° y las correcciones del norte cambian el error?

Programas (references/val_wind_vector/): Alto Quellaveco no corrige la dirección salvo la zona muerta
(355–360° → 0°); Cortadera (desde 2024-06-03) y Papujune (desde 2024-09-05) restan 7° y fijan 353°/355°
cerca del norte. Para Quellaveco se usa como fecha de control la de Cortadera.

1. Huellas en los registros de 5 min con viento (por cada 100 000): D1 exactamente 0.0°, 353.0° y 355.0°.
2. Error de la dirección horaria estimada (V1) y de WindDir_Avg (V0) antes y después de esa fecha.

Uso (desde explorar_qaqc/):
    uv run python -m wind_vector.program_check

Salida: wind_vector/output/RESULTADOS_PROGRAMAS.md
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from wind_vector.analyze import BLOCKS, OUT, STATIONS, block, build_hourly, circ_diff, to_md, valid_mask
from wind_vector.north_sector import abs_diff, acceptance_rules, build_variants

OFFSET_DATE = {"cortadera": "2024-06-03", "papujune": "2024-09-05", "quellaveco": "2024-06-03"}
HAS_OFFSET = {"cortadera": "sí", "papujune": "sí", "quellaveco": "no (control)"}


def fingerprints(df: pd.DataFrame, cut: pd.Timestamp) -> list[dict]:
    rows = []
    for label, sel in (("antes", df["TIMESTAMP"] < cut), ("después", df["TIMESTAMP"] >= cut)):
        d1 = block(df[sel], "WindDir_D1_WVT").ravel()
        ws = block(df[sel], "WS_ms_Avg").ravel()
        d1 = d1[(ws > 0) & ~np.isnan(d1)].round(1)
        per = 1e5 / max(len(d1), 1)
        rows.append({"periodo": label, "registros con viento": len(d1), "D1 = 0.0 (por 100 mil)": (d1 == 0.0).sum() * per,
                     "D1 = 353.0": (d1 == 353.0).sum() * per, "D1 = 355.0": (d1 == 355.0).sum() * per,
                     "D1 en (355, 360]": ((d1 > 355.05) & (d1 <= 360)).sum() * per})
    return rows


def error_rows(df: pd.DataFrame, cut: pd.Timestamp) -> list[dict]:
    h = build_hourly(df)
    v, avg, usable = build_variants(df, h)
    mask = valid_mask(h) & v["MED"].notna()
    r4 = acceptance_rules(v, avg, usable)["R4 R2 y dispersión máx. a la mediana ≤ 45°"]
    north = abs_diff(v["truth"], 0.0) <= 45
    e0, e1 = abs_diff(v["V0"], v["truth"]), abs_diff(v["V1"], v["truth"])
    rows = []
    for label, per in (("antes", df["TIMESTAMP"] < cut), ("después", df["TIMESTAMP"] >= cut)):
        sel = mask & per
        n = sel & north
        acc = sel.to_numpy() & r4
        rows.append({"periodo": label, "horas": int(sel.sum()), "% horas con real a ≤ 45° del norte": n.sum() / sel.sum() * 100,
                     "V0 error medio (todas)": e0[sel].mean(), "V1 error medio (todas)": e1[sel].mean(),
                     "V0 error medio (norte)": e0[n].mean(), "V1 error medio (norte)": e1[n].mean(),
                     "V1 % > 30° (norte)": (e1[n] > 30).mean() * 100, "R4 % aceptadas": acc.sum() / sel.sum() * 100})
    return rows


def main() -> None:
    parts = ["# Programas CRBasic frente a los datos\n",
             "Desfase de −7° en Cortadera (2024-06-03) y Papujune (2024-09-05) según el historial de cada programa; "
             "Alto Quellaveco no lo tiene (fecha de control: 2024-06-03). Antes del desfase la zona muerta (355–360°) se lee "
             "como 0°; después, como 353°. Errores circulares frente al Θ1 horario del logger.\n"]
    for st in STATIONS:
        df = pd.read_csv(OUT / f"aligned_{st}.csv.gz", parse_dates=["TIMESTAMP"])
        cut = pd.Timestamp(OFFSET_DATE[st])
        parts += [f"\n## {st} · desfase: {HAS_OFFSET[st]} · fecha {cut:%Y-%m-%d}\n",
                  "### Huellas en los registros de 5 min\n\n" + to_md(pd.DataFrame(fingerprints(df, cut))) + "\n",
                  "### Error horario antes y después\n\n" + to_md(pd.DataFrame(error_rows(df, cut))) + "\n"]
        print(st, "ok")
    (OUT / "RESULTADOS_PROGRAMAS.md").write_text("\n".join(parts), encoding="utf-8")
    print("->", OUT / "RESULTADOS_PROGRAMAS.md")


if __name__ == "__main__":
    main()
