"""Prueba de flujo de valle-montaña: ¿es el ciclo diario de cada estación coherente con su terreno?

Es la prueba que distinguió el régimen de sitio de Chalsos de un fallo (FINDINGS §9), llevada a toda la red.
Un régimen térmico de valle-montaña deja tres huellas:
1. Noche (0–6 h): el viento llega desde terreno más alto (drenaje, viento de montaña): Δz a barlovento > 0.
2. Día (11–16 h): el viento llega desde terreno más bajo (viento de valle o de ladera): Δz a barlovento < 0.
3. Transiciones: el paso noche → día (6–11 h) y día → noche (16–22 h) recorre el círculo en un sentido; las
   vecinas que comparten valle o vertiente giran igual. Un espejo invierte el sentido, un giro del sensor no.
Una estación que no cumple 1 y 2 no es por fuerza un fallo: puede estar dominada por el flujo regional, por
una quebrada que no se ve a esta escala o por un obstáculo. La prueba da los datos; la lectura va en FINDINGS.

Dirección: WindDir_D1_WVT donde existe; si no, WindDir_Avg de met_corrected (Chalsos: reconstruida desde 5 min;
Mina_Norte: girada). En el resto el aritmético se desvía cuando la hora cruza el N, sobre todo en transiciones.
Régimen = resultante de vectores ponderados por velocidad (horas ≥ 0.5 m/s); constancia = |resultante| / velocidad
media. Ciclo = media vectorial unitaria por hora del día. Quedan fuera los tramos de stations.WIND_EXCLUDED
(salvo SITE_REGIME, excluidas por régimen y no por fallo) y los giros sin corregir de congruence.REF_EXCLUDED.

Terreno: SRTM 30 m (OpenTopoData, caché en tiles_cache/dem_srtm30.json). Para cada régimen, siete cortes cada
5° en ±15° alrededor de su dirección; se da la mediana de los cortes del desnivel respecto a la estación.

Uso (desde explorar_qaqc):
    uv run python met_viewer/valley_flow.py                      # últimos 365 días
    uv run python met_viewer/valley_flow.py --inicio 2025-01-01 --fin 2026-01-01
Salida en met_viewer/output/: valle_montana.csv y valle_montana.html.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

from congruence import REF_EXCLUDED, mask_segments
from stations import DB_PATH, STATIONS, WIND_EXCLUDED

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corrections.store import connect_corrected  # noqa: E402

OUT = Path(__file__).parent / "output"
DEM_CACHE = Path(__file__).parent / "tiles_cache" / "dem_srtm30.json"
SITE_REGIME = {"Chalsos"}             # en WIND_EXCLUDED por régimen propio, no por fallo
NIGHT, DAY = range(0, 7), range(11, 17)
MORNING, EVENING = range(6, 12), range(16, 23)
MIN_WS = 0.5
MIN_HOURS = 200
UPWIND_M = (500, 1000, 2500)
CUTS = range(-15, 16, 5)
NEIGHBOUR_KM = 10.0
MAX_STEP = 120.0                      # salto horario del ciclo medio a partir del cual el sentido es ambiguo
# Dirección que llega de corrections.db en lugar del WindDir_Avg crudo.
CORRECTED_SOURCE = {"Chalsos": "5 min", "Mina_Norte": "Avg girada"}
_TO_LL = Transformer.from_crs("EPSG:32719", "EPSG:4326", always_xy=True)


def srtm(points: list[tuple[float, float]], cache: dict[str, float]) -> np.ndarray:
    """Cota SRTM 30 m de puntos UTM 19S, con caché en disco (OpenTopoData: 100 puntos por petición, 1 por s)."""
    keys = [f"{x:.0f},{y:.0f}" for x, y in points]
    todo = [k for k in dict.fromkeys(keys) if k not in cache]
    for i in range(0, len(todo), 100):
        chunk = todo[i:i + 100]
        ll = [_TO_LL.transform(*map(float, k.split(","))) for k in chunk]
        url = "https://api.opentopodata.org/v1/srtm30m?locations=" + "|".join(f"{la:.6f},{lo:.6f}" for lo, la in ll)
        for attempt in range(6):
            try:
                res = json.load(urllib.request.urlopen(url, timeout=60))["results"]
                break
            except Exception as e:  # noqa: BLE001 - servicio público: reintentar ante cualquier fallo de red
                print("reintento DEM:", e)
                time.sleep(3 + 3 * attempt)
        else:
            raise RuntimeError("OpenTopoData no responde")
        for k, r in zip(chunk, res):
            cache[k] = r["elevation"]
        DEM_CACHE.write_text(json.dumps(cache))
        time.sleep(1.1)
    return np.array([cache[k] for k in keys], float)


def load_wind(start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
    con = connect_corrected(DB_PATH)
    try:
        df = con.execute(
            "SELECT estacion_id AS st, timestamp AS ts, coalesce(WindDir_D1_WVT, WindDir_Avg) AS wd, "
            "WindDir_D1_WVT IS NOT NULL AS has_d1, WS_ms_Avg AS ws FROM met_corrected "
            "WHERE timestamp >= ? AND timestamp < ? AND WS_ms_Avg IS NOT NULL",
            [start.to_pydatetime(), end.to_pydatetime()]).df()
    finally:
        con.close()
    df = df[df["st"].isin(STATIONS)].drop_duplicates(["st", "ts"], keep="last")
    with_d1 = set(df.loc[df["has_d1"], "st"])
    wd = df.pivot(index="ts", columns="st", values="wd")
    ws = df.pivot(index="ts", columns="st", values="ws")
    excluded = {k: v for k, v in WIND_EXCLUDED.items() if k not in SITE_REGIME}
    wd = mask_segments(mask_segments(wd, excluded), REF_EXCLUDED)
    return wd.where(ws >= MIN_WS), ws, with_d1


def regime(wd: pd.Series, ws: pd.Series, hours: range) -> tuple[float, float, int]:
    """(dirección de la resultante ponderada por velocidad, constancia, horas)."""
    sel = wd.notna() & ws.notna() & wd.index.hour.isin(hours)
    r, s = np.deg2rad(wd[sel]), ws[sel]
    if sel.sum() < MIN_HOURS:
        return np.nan, np.nan, int(sel.sum())
    u, v = (s * np.sin(r)).mean(), (s * np.cos(r)).mean()
    return float(np.rad2deg(np.arctan2(u, v)) % 360), float(np.hypot(u, v) / s.mean()), int(sel.sum())


def hourly_cycle(wd: pd.Series) -> pd.Series:
    r = np.deg2rad(wd.dropna())
    g = pd.DataFrame({"s": np.sin(r), "c": np.cos(r)}).groupby(r.index.hour).mean()
    return (np.rad2deg(np.arctan2(g["s"], g["c"])) % 360).reindex(range(24))


def rotation(cycle: pd.Series, hours: range) -> float:
    """Giro acumulado (°, + = sentido horario) del ciclo medio a lo largo de las horas dadas.

    NaN si algún paso entre horas consecutivas llega a MAX_STEP: con un salto de casi 180° el sentido es
    arbitrario (el ciclo medio no dice por qué lado pasa)."""
    path = cycle.reindex(list(hours)).to_numpy()
    if np.isnan(path).any():
        return np.nan
    steps = ((np.diff(path) + 180) % 360) - 180
    return np.nan if np.abs(steps).max() >= MAX_STEP else float(steps.sum())


def terrain(st: str, direction: float, cache: dict[str, float]) -> dict[int, float]:
    """Mediana de los cortes del desnivel (m) a barlovento, por distancia."""
    x, y = STATIONS[st].easting, STATIONS[st].northing
    dist = np.array(UPWIND_M)
    pts = [(x, y)] + [(x + d * np.sin(np.deg2rad(direction + off)), y + d * np.cos(np.deg2rad(direction + off)))
                      for off in CUTS for d in dist]   # azimut = de donde viene el viento
    z = srtm(pts, cache)
    med = np.median((z[1:] - z[0]).reshape(len(CUTS), len(dist)), axis=0)
    return {int(d): float(m) for d, m in zip(dist, med)}


def neighbours(st: str, pool: list[str]) -> list[str]:
    x, y = STATIONS[st].easting, STATIONS[st].northing
    return [o for o in pool if o != st and np.hypot(STATIONS[o].easting - x, STATIONS[o].northing - y) <= NEIGHBOUR_KM * 1000]


def analyse(start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    wd, ws, with_d1 = load_wind(start, end)
    DEM_CACHE.parent.mkdir(exist_ok=True)
    cache = json.loads(DEM_CACHE.read_text()) if DEM_CACHE.exists() else {}
    rows, cycles = [], {}
    for st in sorted(wd.columns):
        n_dir, c_n, h_n = regime(wd[st], ws[st], NIGHT)
        d_dir, c_d, h_d = regime(wd[st], ws[st], DAY)
        if np.isnan(n_dir) or np.isnan(d_dir):
            continue
        cyc = hourly_cycle(wd[st])
        cycles[st] = cyc
        tn, td = terrain(st, n_dir, cache), terrain(st, d_dir, cache)
        source = "D1" if st in with_d1 else CORRECTED_SOURCE.get(st, "Avg")
        row = {"station": st, "source": source, "night_dir": n_dir, "night_const": c_n,
               "night_h": h_n, "day_dir": d_dir, "day_const": c_d, "day_h": h_d,
               "day_night_angle": float(abs((d_dir - n_dir + 180) % 360 - 180)),
               "morning_turn": rotation(cyc, MORNING), "evening_turn": rotation(cyc, EVENING)}
        row.update({f"night_dz_{d}": v for d, v in tn.items()})
        row.update({f"day_dz_{d}": v for d, v in td.items()})
        rows.append(row)
        print(f"{st}: noche {n_dir:.0f}° Δz1km {tn[1000]:+.0f} m | día {d_dir:.0f}° Δz1km {td[1000]:+.0f} m")
    res = pd.DataFrame(rows)
    # Sentido de las transiciones frente a las vecinas con datos en la misma ventana.
    sign = lambda v: 0 if pd.isna(v) or abs(v) < 45 else np.sign(v)   # sin sentido: ambiguo o < 45°
    for col in ("morning_turn", "evening_turn"):
        same, total = [], []
        for st in res["station"]:
            me = sign(res.set_index("station").at[st, col])
            nb = [sign(res.set_index("station").at[o, col]) for o in neighbours(st, list(res["station"]))]
            nb = [s for s in nb if s != 0]   # solo vecinas con sentido definido
            total.append(len(nb))
            same.append(np.nan if me == 0 or not nb else sum(s == me for s in nb) / len(nb) * 100)
        res[col.replace("turn", "same_pct")], res[col.replace("turn", "nb")] = same, total
    return res, cycles


def page(res: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> str:
    def fmt(v, spec):
        return "" if pd.isna(v) else format(v, spec)

    head = ("<tr><th rowspan=2>Estación</th><th rowspan=2>Dir.</th><th colspan=5>Noche (0–6 h)</th>"
            "<th colspan=5>Día (11–16 h)</th><th rowspan=2>Ángulo<br>día–noche</th>"
            "<th colspan=2>Giro mañana (6→11 h)</th><th colspan=2>Giro tarde (16→22 h)</th></tr>"
            "<tr><th>de</th><th>const.</th><th>Δz 0.5 km</th><th>1 km</th><th>2.5 km</th>"
            "<th>de</th><th>const.</th><th>Δz 0.5 km</th><th>1 km</th><th>2.5 km</th>"
            "<th>°</th><th>% vecinas igual</th><th>°</th><th>% vecinas igual</th></tr>")
    body = []
    for _, r in res.iterrows():
        cells = [html.escape(r.station), r.source, fmt(r.night_dir, ".0f") + "°", fmt(r.night_const, ".2f")]
        cells += [fmt(r[f"night_dz_{d}"], "+.0f") for d in UPWIND_M]
        cells += [fmt(r.day_dir, ".0f") + "°", fmt(r.day_const, ".2f")]
        cells += [fmt(r[f"day_dz_{d}"], "+.0f") for d in UPWIND_M]
        cells += [fmt(r.day_night_angle, ".0f") + "°", fmt(r.morning_turn, "+.0f"),
                  f"{fmt(r.morning_same_pct, '.0f')} ({r.morning_nb})", fmt(r.evening_turn, "+.0f"),
                  f"{fmt(r.evening_same_pct, '.0f')} ({r.evening_nb})"]
        cls = []
        for k, d in enumerate(UPWIND_M):
            cls.append("pos" if r[f"night_dz_{d}"] > 0 else "neg")
        for k, d in enumerate(UPWIND_M):
            cls.append("neg" if r[f"day_dz_{d}"] < 0 else "pos")
        tds = []
        for i, c in enumerate(cells):
            klass = ""
            if 4 <= i <= 6:
                klass = "ok" if cls[i - 4] == "pos" else "no"
            elif 9 <= i <= 11:
                klass = "ok" if cls[i - 6] == "neg" else "no"
            tds.append(f'<td class="{klass}">{c}</td>')
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Flujo de valle-montaña</title>
<style>
 :root{{--ink:#1f1f1c;--ink2:#5c5b56;--grid:#e4e2dc;--bg:#f9f9f7;--ok:#e3efe6;--no:#f6e2dc}}
 body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--ink);margin:0;padding:12px}}
 h1{{font-size:19px;margin:0 0 4px}} p{{color:var(--ink2);font-size:13px;margin:4px 0 10px;max-width:1100px}}
 .wrap{{overflow-x:auto}} table{{border-collapse:collapse;font-size:13px;background:#fff}}
 th,td{{border:1px solid var(--grid);padding:3px 7px;text-align:right;white-space:nowrap}}
 th{{background:#f1f0ec;text-align:center}} td:first-child{{text-align:left}}
 td.ok{{background:var(--ok)}} td.no{{background:var(--no)}}
</style></head><body>
<h1>Flujo de valle-montaña · {start:%Y-%m-%d} → {end:%Y-%m-%d}</h1>
<p>Régimen = resultante ponderada por velocidad (horas ≥ {MIN_WS} m/s); «de» es la dirección de procedencia y «const.»
la constancia (|resultante| / velocidad media). Δz = desnivel del terreno a barlovento respecto a la estación
(SRTM 30 m, mediana de siete cortes en ±15°). Verde: lo que espera un régimen térmico (noche desde más alto, día desde
más bajo); rojo: lo contrario. Giro = recorrido acumulado del ciclo horario medio (+ horario, − antihorario); «% vecinas
igual» = vecinas a ≤ {NEIGHBOUR_KM:.0f} km con el mismo sentido (giros ≥ 45°; entre paréntesis, cuántas con sentido
definido). Giro en blanco: el ciclo medio salta ≥ {MAX_STEP:.0f}° entre dos horas y el sentido es ambiguo. «Dir.»: D1 =
media vectorial del logger; 5 min = reconstruida desde 5 min; Avg = media aritmética horaria (se desvía cuando la hora
cruza el N). El SRTM es del año 2000: no ve el tajo, los botaderos ni las plataformas posteriores.</p>
<div class="wrap"><table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inicio"); ap.add_argument("--fin")
    a = ap.parse_args()
    end = pd.Timestamp(a.fin) if a.fin else pd.Timestamp.now().normalize()
    start = pd.Timestamp(a.inicio) if a.inicio else end - pd.Timedelta(days=365)
    res, _ = analyse(start, end)
    OUT.mkdir(exist_ok=True)
    res.round(2).to_csv(OUT / "valle_montana.csv", index=False)
    (OUT / "valle_montana.html").write_text(page(res, start, end), encoding="utf-8")
    print(f"\n{OUT / 'valle_montana.csv'}\n{OUT / 'valle_montana.html'}")


if __name__ == "__main__":
    main()
