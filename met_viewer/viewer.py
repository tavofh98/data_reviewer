"""HTML de meteorología en dos vistas, para comparar:

- por variable: una sección por variable y una figura por grupo; cada variable usa sus propios
  grupos (la presión usa los de temperatura, porque su desvío no define parecido).
- por grupo: un agrupamiento único; una sección por grupo con sus cuatro figuras.

Variables: temperatura, humedad relativa, velocidad del viento y desvío de presión (presión
reducida a 4 000 m menos la mediana de las vecinas; ver qc.baro_deviation).
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


VARIABLES_VISTA = (data.TEMP, data.RH, data.WS, "BP_DEV")


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
        divs = []
        for n, grupo in enumerate(grupos[data.TEMP if var == "BP_DEV" else var], 1):
            fig = _figura_de(grupo, var, limpio, flags, dev_horario, fin, f"G{n} · {', '.join(grupo)}")
            if fig is not None:
                divs.append(h.div(fig))
        if divs:
            nombre = data.BP if var == "BP_DEV" else var
            secciones.append(f'<section id="{var}"><h2>{html.escape(TITULOS[var])}</h2>'
                             + _resumen_qc(flags[flags.variable == nombre]) + "".join(divs) + "</section>")
    indice = [(v, TITULOS[v].split(" (")[0]) for v in VARIABLES_VISTA]
    return _pagina("Meteorología por variable", indice, secciones, ini, fin, borrador)


def construir_por_grupo(grupos: list[list[str]], limpio, flags, dev_horario, ini, fin, borrador: bool) -> str:
    """Vista por grupo: un agrupamiento único; una sección por grupo con sus cuatro figuras."""
    h, secciones, indice = _Html(), [], []
    for n, grupo in enumerate(grupos, 1):
        divs = [h.div(f) for var in VARIABLES_VISTA
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
 .est{{color:{INK_2};margin:4px 0}} .qc{{color:{MUTED};font-size:13px;margin:0 0 8px}}
 .aviso{{color:{CRITICO};font-weight:600}}
 #modo{{font:inherit;font-size:13px;padding:4px 10px;margin:4px 0 6px;border:1px solid {MUTED};border-radius:6px;
        background:{SUPERFICIE};color:{INK};cursor:pointer}}
 #modo[aria-pressed="true"]{{background:#2a78d6;border-color:#2a78d6;color:#fff}}
</style></head><body>
<header><h1>{titulo} · {ini:%Y-%m-%d %H:%M} → {fin:%Y-%m-%d %H:%M}</h1>{aviso}
<button id="modo" type="button" aria-pressed="false" title="Alterna entre valores reales y centrados (cada estación menos su mediana en la ventana). No afecta al desvío de presión, que ya está centrado.">Valores: reales</button>
<nav>{nav}</nav></header>
{"".join(secciones)}
<script>{JS_CENTRAR}</script>
</body></html>"""


def guardar(html_txt: str, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(html_txt, encoding="utf-8")
