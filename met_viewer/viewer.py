"""HTML de meteorología en dos vistas, para comparar:

- por variable: las variables que no caben en la vista por grupo, cada una con sus propios
  grupos. Hoy, solo el viento.
- por grupo: un agrupamiento único (de T y HR); una sección por grupo con temperatura, humedad y
  desvío de presión. El viento no va aquí: dentro de esos grupos no guarda relación.

Variables: temperatura, humedad relativa, viento y desvío de presión (presión reducida a 4 000 m
menos la mediana de las vecinas; ver qc.baro_deviation). El viento, solo en la vista por
variable: mapas de rosas por zona (rose_maps.py) y, por cada grupo de viento, la serie horaria
de velocidad y su ciclo diario medio.
Los huecos en las líneas son horas sin dato o descartadas; los descartes del QC se ven como
cruces en la traza «Descartado por QC», oculta al abrir (clic en la leyenda para verla).
"""
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio

import data
import rose_maps
import wind
from stations import STATIONS, sensor_at

# Paleta categórica de referencia (skill dataviz), orden fijo; validada para 6 series.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
CRITICO = "#d03b3b"          # color de estado: solo para los descartes
INK, INK_2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SUPERFICIE = "#fcfcfb"

TITULOS = {
    data.TEMP: "Temperatura del aire (°C)",
    data.RH: "Humedad relativa (%)",
    data.WS: "Velocidad del viento (m/s)",
    "BP_DEV": "Desvío de presión respecto a las vecinas (mbar)",
}
NOMBRE_SENSOR = {"climavue": "ClimaVUE", "windsonic": "WindSonic", "torre": "torre"}
ALTURA_TIPICA = {"climavue": 2.0, "windsonic": 2.0, "torre": 10.0}   # m, si el sensor no declara la suya


def _layout(fig: go.Figure, titulo: str) -> None:
    fig.update_layout(
        height=380,
        margin=dict(l=60, r=150, t=50, b=40),
        title=dict(text=titulo, x=0.01, font=dict(size=15, color=INK)),
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=12, color=INK_2),
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE,
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15, font=dict(size=11)),
        xaxis=dict(gridcolor=GRID, linecolor=MUTED, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=GRID, linecolor=MUTED, tickfont=dict(color=MUTED), zeroline=False),
    )


def _nombre(est: str, var: str, fin: pd.Timestamp) -> str:
    if var != data.WS:
        return est
    s = sensor_at(est, "viento", f"{fin:%Y-%m-%d}")
    if s is None or s.kind not in NOMBRE_SENSOR:
        return f"{est} · s/d"
    return f"{est} · {NOMBRE_SENSOR[s.kind]} ~{s.height_m or ALTURA_TIPICA[s.kind]:g} m"


def _lista(s: pd.Series) -> list[float | None]:
    """Valores como lista JSON simple (None = hueco). Con arrays de NumPy, plotly los codifica en
    base64 y el script del botón no podría leerlos desde gd.data."""
    return [None if pd.isna(v) else round(float(v), 3) for v in s]


def figura(grupo: list[str], var: str, series: dict[str, pd.Series],
           descartes: pd.DataFrame, fin: pd.Timestamp, titulo: str, rango_y=None) -> go.Figure | None:
    """Una figura con una línea por estación del grupo (color fijo por posición en el grupo).

    Cada traza lleva en `meta.med` la mediana de su estación en la ventana (una lista, en la
    traza de descartes) y el layout lleva `meta.anot_med`: con eso el botón «centrado» de la
    página resta la mediana propia a cada estación sin recalcular nada en el navegador.
    """
    fig = go.Figure()
    medianas: dict[str, float] = {}
    for i, est in enumerate(grupo):
        s = series.get(est)
        if s is None or s.notna().sum() == 0:
            continue
        medianas[est] = float(s.median())
        color = SERIES[i % len(SERIES)]
        fig.add_trace(go.Scatter(x=s.index, y=_lista(s), name=_nombre(est, var, fin), mode="lines",
                                 line=dict(width=2, color=color), connectgaps=False,
                                 meta={"med": medianas[est]}))
        ultimo = s.last_valid_index()
        fig.add_annotation(x=ultimo, y=s[ultimo], text=est, xanchor="left", showarrow=False,
                           xshift=6, font=dict(size=11, color=INK_2))
    if not fig.data:
        return None
    if not descartes.empty:
        fig.add_trace(go.Scatter(
            x=descartes["timestamp"], y=_lista(descartes["valor"]), name="Descartado por QC", mode="markers",
            marker=dict(symbol="x-thin", size=9, line=dict(width=2, color=CRITICO)),
            text=[f"{e}: {r}" for e, r in zip(descartes["estacion_id"], descartes["regla"])],
            hovertemplate="%{text}<br>%{y}<extra></extra>", visible="legendonly",
            meta={"med": [medianas.get(e) for e in descartes["estacion_id"]]}))
    _layout(fig, titulo)
    if var != "BP_DEV":
        unidad = TITULOS[var].rsplit("(", 1)[-1].rstrip(")")
        fig.update_layout(meta={"centrable": True, "anot_med": list(medianas.values()),
                                "ytitulo_centrado": f"− mediana de la estación ({unidad})"})
    if rango_y is not None:
        fig.update_yaxes(range=rango_y)
    if var == "BP_DEV":
        fig.add_hline(y=0, line=dict(color=MUTED, width=1))
    return fig


VARIABLES_VISTA = (data.WS,)      # T, HR y presión van solo en la vista por grupo
VARIABLES_GRUPO = (data.TEMP, data.RH, "BP_DEV")

# --- Viento (vista por variable) -------------------------------------------------------------

TITULO_VIENTO = "Viento"
NOCHE = "rgba(137, 135, 129, 0.12)"      # franja de noche (22–06 h) en el ciclo diario
NOTA_MAPAS = (
    "Rosas de procedencia: cada pétalo es el % de las horas de la franja en que el viento vino de "
    "ese sector de 22.5°, apilado por velocidad. Las calmas (< 0.5 m/s) no tienen pétalo; su % "
    "está en el cursor sobre cada estación. Día y noche comparten escala dentro de cada zona, no "
    "entre zonas, y la escala se recalcula con el periodo. La noche cuenta en el día en que empieza.")
NOTA_GRUPOS = (
    "Grupos de viento (groups*.py): por régimen de dirección y forma del ciclo diario de velocidad; "
    "ver grouping.py. La leyenda indica el sensor y su altura. Banda gris del ciclo diario: noche "
    "(22–06 h). Criterios de revisión en WIND_REVIEW.md.")


def fig_ciclo_velocidad(grupo: list[str], limpio, fin) -> go.Figure | None:
    """Velocidad media por hora del día; mismo color por estación que la serie del grupo."""
    fig = go.Figure()
    for i, est in enumerate(grupo):
        if est not in limpio or data.WS not in limpio[est] or limpio[est][data.WS].notna().sum() == 0:
            continue
        fig.add_trace(go.Scatter(x=list(range(24)), y=_lista(wind.ciclo_velocidad(limpio[est])),
                                 name=_nombre(est, data.WS, fin), mode="lines+markers",
                                 line=dict(width=2, color=SERIES[i % len(SERIES)]), marker=dict(size=5)))
    if not fig.data:
        return None
    _layout(fig, "Ciclo diario medio de velocidad (m/s)")
    fig.update_layout(showlegend=True)       # con una sola estación plotly la oculta, y lleva el sensor
    fig.update_xaxes(range=[-0.5, 23.5], tickvals=list(range(0, 24, 3)), title_text="Hora del día")
    for x0, x1 in ((-0.5, 6), (22, 23.5)):
        fig.add_vrect(x0=x0, x1=x1, fillcolor=NOCHE, line_width=0, layer="below")
    return fig


CONTROL_PERIODO = """<div class="periodo">
<label>Periodo de las rosas: desde <input type="date" id="r_ini"></label>
<label>durante <select id="r_dias">{opciones}</select></label>
<button type="button" id="r_todo">Toda la ventana</button>
<span id="r_txt"></span></div>"""
MAX_DIAS_PERIODO = 5


def _seccion_viento(grupos: list[list[str]], limpio, flags, dev_horario, h: "_Html", ini, fin) -> str:
    mapas = [h.div(f) for z in rose_maps.ZONAS if (f := rose_maps.mapa_zona(z, limpio, ini, fin)) is not None]
    if mapas:
        opciones = "".join(f'<option value="{n}"{" selected" if n == MAX_DIAS_PERIODO else ""}>'
                           f'{n} día{"s" if n > 1 else ""}</option>' for n in range(1, MAX_DIAS_PERIODO + 1))
        mapas.insert(0, CONTROL_PERIODO.format(opciones=opciones))
    bloques = []
    for n, grupo in enumerate(grupos, 1):
        figs = [f for f in (_figura_de(grupo, data.WS, limpio, flags, dev_horario, fin, TITULOS[data.WS]),
                            fig_ciclo_velocidad(grupo, limpio, fin)) if f is not None]
        if figs:
            bloques.append(f'<h3>G{n} · {html.escape(", ".join(grupo))}</h3>' + "".join(h.div(f) for f in figs))
    if not (mapas or bloques):
        return ""
    return (f'<section id="{data.WS}"><h2>{TITULO_VIENTO}</h2>'
            + _resumen_qc(flags[flags.variable.isin([data.WS, data.WD])])
            + f'<h3>Rosas por zona</h3><p class="est">{html.escape(NOTA_MAPAS)}</p>' + "".join(mapas)
            + f'<h3>Velocidad por grupo</h3><p class="est">{html.escape(NOTA_GRUPOS)}</p>' + "".join(bloques)
            + "</section>")


class _Html:
    """Convierte figuras a <div>; plotly.js se carga (CDN) solo con la primera."""

    def __init__(self) -> None:
        self.primera = True

    def div(self, fig: go.Figure) -> str:
        out = pio.to_html(fig, full_html=False, include_plotlyjs="cdn" if self.primera else False,
                          config={"displaylogo": False})
        self.primera = False
        return out


def _figura_de(grupo, var, limpio, flags, dev_horario, fin, titulo) -> go.Figure | None:
    if var == "BP_DEV":
        series = {e: dev_horario[e] for e in grupo if e in dev_horario}
        return figura(grupo, var, series, pd.DataFrame(), fin, titulo, [-3, 3])
    series = {e: limpio[e][var] for e in grupo if e in limpio and var in limpio[e]}
    desc = flags[(flags.variable == var) & flags.estacion_id.isin(grupo)]
    return figura(grupo, var, series, desc, fin, titulo)


def _resumen_qc(sel: pd.DataFrame) -> str:
    txt = " · ".join(f"{r}: {c}" for r, c in sel.groupby("regla").size().items()) or "sin descartes"
    return f'<p class="qc">Descartes QC en la ventana: {html.escape(txt)}</p>'


def construir_por_variable(grupos: dict[str, list[list[str]]], limpio, flags, dev_horario,
                           ini, fin, borrador: bool) -> str:
    """Vista por variable: una sección por variable, una figura por grupo de esa variable.
    `grupos` es {variable: [grupo, ...]}; la presión usa los grupos de temperatura."""
    h, secciones = _Html(), []
    for var in VARIABLES_VISTA:
        if var == data.WS:
            if sec := _seccion_viento(grupos[var], limpio, flags, dev_horario, h, ini, fin):
                secciones.append(sec)
            continue
        divs = []
        for n, grupo in enumerate(grupos[data.TEMP if var == "BP_DEV" else var], 1):
            fig = _figura_de(grupo, var, limpio, flags, dev_horario, fin, f"G{n} · {', '.join(grupo)}")
            if fig is not None:
                divs.append(h.div(fig))
        if divs:
            nombre = data.BP if var == "BP_DEV" else var
            secciones.append(f'<section id="{var}"><h2>{html.escape(TITULOS[var])}</h2>'
                             + _resumen_qc(flags[flags.variable == nombre]) + "".join(divs) + "</section>")
    indice = [(v, TITULO_VIENTO if v == data.WS else TITULOS[v].split(" (")[0]) for v in VARIABLES_VISTA]
    return _pagina("Meteorología por variable", indice, secciones, ini, fin, borrador)


def construir_por_grupo(grupos: list[list[str]], limpio, flags, dev_horario, ini, fin, borrador: bool) -> str:
    """Vista por grupo: un agrupamiento único; una sección por grupo con T, HR y desvío de presión."""
    h, secciones, indice = _Html(), [], []
    for n, grupo in enumerate(grupos, 1):
        divs = [h.div(f) for var in VARIABLES_GRUPO
                if (f := _figura_de(grupo, var, limpio, flags, dev_horario, fin, TITULOS[var])) is not None]
        if divs:
            indice.append((f"g{n}", f"G{n}"))
            secciones.append(f'<section id="g{n}"><h2>Grupo {n}</h2><p class="est">{html.escape(", ".join(grupo))}</p>'
                             + _resumen_qc(flags[flags.estacion_id.isin(grupo)]) + "".join(divs) + "</section>")
    return _pagina("Meteorología por grupo", indice, secciones, ini, fin, borrador)


# Botón de la cabecera: alterna las figuras centrables entre valores reales y centrados (cada
# estación menos su propia mediana en la ventana). Resta o devuelve meta.med, así que pulsar dos
# veces deja los datos exactamente como estaban.
# Rendimiento: redibujar las ~30 figuras de golpe era lento. Se redibujan al momento solo las
# que están en pantalla o cerca (IntersectionObserver); cada figura guarda el modo que tiene
# aplicado y se pone al día cuando entra en pantalla. Pulsar dos veces sin llegar a una figura
# no la redibuja nunca.
JS_CENTRAR = r"""
(function () {
  const nulo = v => v === null || v === undefined || Number.isNaN(v);
  function desplazar(y, med, signo) {
    return Array.from(y, (v, i) => {
      const m = Array.isArray(med) ? med[i] : med;
      return (nulo(v) || nulo(m)) ? v : v + signo * m;
    });
  }
  let centrado = false;
  const btn = document.getElementById("modo");
  const figuras = Array.from(document.querySelectorAll(".js-plotly-plot"))
    .filter(gd => gd.layout && gd.layout.meta && gd.layout.meta.centrable);
  figuras.forEach(gd => { gd._centrado = false; });

  function aplicar(gd) {
    if (gd._centrado === centrado) return;
    const signo = centrado ? -1 : 1, meta = gd.layout.meta;
    const idx = [], ys = [];
    gd.data.forEach((t, i) => {
      if (t.meta && t.meta.med !== undefined) { idx.push(i); ys.push(desplazar(t.y, t.meta.med, signo)); }
    });
    const lay = {"yaxis.title.text": centrado ? meta.ytitulo_centrado : ""};
    (gd.layout.annotations || []).forEach((a, i) => {
      const m = meta.anot_med[i];
      if (!nulo(m)) lay[`annotations[${i}].y`] = a.y + signo * m;
    });
    Plotly.update(gd, {y: ys}, lay, idx);
    gd._centrado = centrado;
  }

  const visibles = new Set();
  if ("IntersectionObserver" in window) {
    const obs = new IntersectionObserver(entradas => entradas.forEach(e => {
      if (e.isIntersecting) { visibles.add(e.target); aplicar(e.target); }
      else visibles.delete(e.target);
    }), {rootMargin: "600px 0px"});
    figuras.forEach(gd => obs.observe(gd));
  } else {
    figuras.forEach(gd => visibles.add(gd));      // navegador sin observer: todas a la vez
  }

  btn.addEventListener("click", () => {
    centrado = !centrado;
    visibles.forEach(aplicar);
    btn.textContent = centrado ? "Valores: centrados (− mediana de cada estación)" : "Valores: reales";
    btn.setAttribute("aria-pressed", String(centrado));
  });
})();
"""


# Selector de periodo de las rosas: suma en el navegador los conteos diarios que cada mapa lleva en
# layout.meta.rosas (rose_maps._datos_periodo) y redibuja rosas, cursor y rótulo de escala, con la
# misma geometría y el mismo criterio de escala (percentil de los pétalos máximos) que Python.
JS_ROSAS = r"""
(function () {
  const mapas = Array.from(document.querySelectorAll(".js-plotly-plot"))
    .filter(gd => gd.layout && gd.layout.meta && gd.layout.meta.rosas);
  if (!mapas.length) return;
  const dias = mapas[0].layout.meta.rosas.dias;
  const ini = document.getElementById("r_ini"), nd = document.getElementById("r_dias");
  const todo = document.getElementById("r_todo"), txt = document.getElementById("r_txt");
  const NS = 16, ANCHO = 360 / NS;
  ini.min = dias[0]; ini.max = dias[dias.length - 1];
  ini.value = dias[Math.max(0, dias.length - Number(nd.value))];

  function percentil(v, p) {                     // interpolación lineal, como numpy
    if (!v.length) return NaN;
    const s = v.slice().sort((a, b) => a - b), h = (s.length - 1) * p / 100, lo = Math.floor(h);
    return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (h - lo);
  }
  const pct = (a, n) => n ? Math.round(100 * a / n) + " %" : "–";

  function dibujar(gd, a, b) {                   // días [a, b)
    const m = gd.layout.meta.rosas, NC = m.nclases;
    const suma = {}, maximos = [];
    m.est.forEach((e, i) => {
      let mx = 0, hay = false;
      for (const fr of m.franjas) {
        const acc = new Array(NS * NC + 2).fill(0);
        for (let d = a; d < b; d++) m.c[fr][i][d].forEach((v, j) => { acc[j] += v; });
        suma[fr + i] = acc;
        const n = acc[NS * NC + 1];
        if (!n) continue;
        hay = true;
        for (let s = 0; s < NS; s++) {
          let f = 0;
          for (let k = 0; k < NC; k++) f += acc[s * NC + k];
          mx = Math.max(mx, 100 * f / n);
        }
      }
      if (hay) maximos.push(mx);
    });
    const ref = percentil(maximos, m.ref_percentil);
    const escala = ref > 0 ? m.petalo_m / Math.sqrt(ref) : 0;

    const xs = [], ys = [], idx = [];
    for (const fr of m.franjas) for (let k = NC - 1; k >= 0; k--) {
      const x = [], y = [];
      m.est.forEach((e, i) => {
        const acc = suma[fr + i], n = acc[NS * NC + 1];
        if (!n) return;
        for (let s = 0; s < NS; s++) {
          let f = 0;
          for (let q = 0; q <= k; q++) f += acc[s * NC + q];
          if (f <= 0) continue;
          const r = escala * Math.sqrt(100 * f / n) * e.k;
          x.push(e.x); y.push(e.y);
          for (let j = 0; j < 6; j++) {
            const ang = (s * ANCHO - ANCHO / 2 + j * ANCHO / 5) * Math.PI / 180;
            x.push(e.x + r * Math.sin(ang)); y.push(e.y + r * Math.cos(ang));
          }
          x.push(e.x, null); y.push(e.y, null);
        }
      });
      xs.push(x); ys.push(y); idx.push(m.trazas[fr][k]);
    }
    const hover = m.est.map((e, i) => {
      const d = suma[m.franjas[0] + i], n = suma[m.franjas[1] + i], cd = d[NS * NC + 1], cn = n[NS * NC + 1];
      return `<b>${e.n}</b><br>${e.sensor}<br>` + (cd + cn
        ? `calma: día ${pct(d[NS * NC], cd)} (${cd} h) · noche ${pct(n[NS * NC], cn)} (${cn} h)`
        : "sin datos de viento en el periodo");
    });
    Plotly.restyle(gd, {x: xs, y: ys}, idx);
    Plotly.restyle(gd, {hovertext: [hover]}, [m.traza_puntos]);
    const rotulo = Number.isFinite(ref)
      ? `<b>Zona ${m.zona}</b> · pétalo de ${m.petalo_m} m = ${Math.round(ref)} % de las horas de la franja`
      : `<b>Zona ${m.zona}</b> · sin datos en el periodo`;
    Plotly.relayout(gd, {[`annotations[${m.anot_zona}].text`]: rotulo});
  }

  function aplicar(a, b) {
    mapas.forEach(gd => dibujar(gd, a, b));
    txt.textContent = b - a === dias.length ? `toda la ventana (${dias.length} días)`
      : `${dias[a]} → ${dias[b - 1]} (${b - a} día${b - a > 1 ? "s" : ""})`;
  }
  function desdeControles() {
    let a = dias.indexOf(ini.value);
    if (a < 0) a = Math.max(0, dias.length - Number(nd.value));
    aplicar(a, Math.min(dias.length, a + Number(nd.value)));
  }
  ini.addEventListener("change", desdeControles);
  nd.addEventListener("change", desdeControles);
  todo.addEventListener("click", () => aplicar(0, dias.length));
  txt.textContent = `toda la ventana (${dias.length} días)`;
})();
"""


def _pagina(titulo: str, indice: list[tuple[str, str]], secciones: list[str],
            ini: pd.Timestamp, fin: pd.Timestamp, borrador: bool) -> str:
    nav = "".join(f'<a href="#{i}">{html.escape(t)}</a>' for i, t in indice)
    aviso = ('<p class="aviso">Grupos del borrador automático (groups_draft.py): '
             'revísalos y guárdalos como groups.py.</p>') if borrador else ""
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
 body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:#f9f9f7;color:{INK};margin:0;padding:16px}}
 header{{position:sticky;top:0;background:#f9f9f7;padding:8px 0;border-bottom:1px solid {GRID};z-index:10}}
 header a{{margin-right:12px;color:#2a78d6;text-decoration:none}}
 section{{background:{SUPERFICIE};border:1px solid rgba(11,11,11,.1);border-radius:8px;padding:12px;margin:16px 0}}
 h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:17px;margin:0}}
 h3{{font-size:15px;margin:20px 0 4px;padding-top:12px;border-top:1px solid {GRID}}}
 .est{{color:{INK_2};margin:4px 0}} .qc{{color:{MUTED};font-size:13px;margin:0 0 8px}}
 .aviso{{color:{CRITICO};font-weight:600}}
 #modo{{font:inherit;font-size:13px;padding:4px 10px;margin:4px 0 6px;border:1px solid {MUTED};border-radius:6px;
        background:{SUPERFICIE};color:{INK};cursor:pointer}}
 .periodo{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;font-size:13px;margin:8px 0}}
 .periodo input,.periodo select,.periodo button{{font:inherit;padding:3px 6px;border:1px solid {MUTED};
        border-radius:6px;background:{SUPERFICIE};color:{INK}}}
 .periodo button{{cursor:pointer}} #r_txt{{color:{INK_2}}}
 #modo[aria-pressed="true"]{{background:#2a78d6;border-color:#2a78d6;color:#fff}}
</style></head><body>
<header><h1>{titulo} · {ini:%Y-%m-%d %H:%M} → {fin:%Y-%m-%d %H:%M}</h1>{aviso}
<button id="modo" type="button" aria-pressed="false" title="Alterna entre valores reales y centrados (cada estación menos su mediana en la ventana). No afecta al desvío de presión, que ya está centrado.">Valores: reales</button>
<nav>{nav}</nav></header>
{"".join(secciones)}
<script>{JS_CENTRAR}</script>
<script>{JS_ROSAS}</script>
</body></html>"""


def guardar(html_txt: str, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(html_txt, encoding="utf-8")
