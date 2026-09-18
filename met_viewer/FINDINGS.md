# Visor de meteorología por grupos — hallazgos y decisiones

_Actualizado: 2026-09-18 · Base: `database_duck/anglo_ambiental.db` (datos 2019-09 → 2026-09-18)_

Objetivo: un visor HTML por matriz donde las estaciones se comparan dentro de grupos de
comportamiento similar, sobre datos que pasaron un control de calidad automático fuerte.
Se empezó por meteorología (temperatura, humedad, presión; viento en curso).

Antecedentes: `control_calidad_aaq` (6 capas de QC sobre datos sin limpiar) y
`visualization_explore` (bandas por nivel, todas las estaciones en un eje) se estancaron.
Este visor reutiliza sus ideas pero parte de un QC mínimo y medido.

---

## 1. Uso

```bash
uv run python met_viewer/grouping.py            # propone grupos -> met_viewer/groups_draft.py
uv run python met_viewer/main.py --ultimos 30   # HTML + qc_flags.csv en met_viewer/output/
uv run python met_viewer/calibrate_baro.py      # recalcula z_baro (NO por rutina, ver §3)
```

`main.py` acepta `--ultimos N --corte H` o `--inicio/--fin` (intervalo `[inicio, fin)`, como
`anglo_reporte`). Genera dos vistas:

- `meteorologia_por_grupo.html` — **la preferida**. Una sección por grupo (`GROUPS_COMBINED`)
  con temperatura, humedad, viento y desvío de presión.
- `meteorologia_por_variable.html` — una sección por variable con sus propios grupos (`GROUPS`).

Los grupos salen de `groups.py` si existe (curado a mano) o de `groups_draft.py`.

| Archivo | Qué hace |
|---|---|
| `stations.py` | coordenadas, altitud DEM y barométrica, historial de sensores |
| `data.py` | lectura de la base en solo lectura, limitada a `VARIABLES_REPORTE` |
| `qc.py` | reglas de descarte |
| `grouping.py` | agrupamiento por correlación de anomalías |
| `viewer.py`, `main.py` | HTML y CLI |
| `calibrate_baro.py` | altitud barométrica de cada estación |

La norma de qué variables importan es `anglo_reporte/matrices.py` → `VARIABLES_REPORTE`. El
Excel de `anglo_reporte` no se toca.

---

## 2. Coordenadas y altitudes

- **Las coordenadas y altitudes de `control_calidad_aaq/config.py` no sirven.** Con un DEM
  (SRTM/ASTER 30 m) el terreno en esos puntos queda 1 000–2 000 m por debajo de la estación, y
  las altitudes declaradas difieren de las barométricas hasta en 1 495 m (Calacaja). La tabla
  tiene además valores copiados (Calientes1 y Charaque comparten este; dos pares comparten
  altitud).
- **Fuente válida: `Estaciones AAQ.kmz`** (raíz del workspace, ubicado en Google Earth). Con sus
  coordenadas, DEM y altitud barométrica coinciden en las 24 estaciones con barómetro.
- **Altitud de trabajo: la barométrica** (`z_baro`), anclada al DEM: |z_baro − z_dem| ≤ 30 m,
  mediana 10 m.
- Por confirmar: en el KMZ, «Campamento Quellaveco» tiene la misma coordenada que «Botadero
  Altaranito Norte».

---

## 3. Presión: reducción hidrostática

Cada presión se reduce a 4 000 m con la ecuación hipsométrica (temperatura de la columna a
partir de la T de la estación suavizada 24 h y un gradiente estándar) usando `z_baro` fija.

- Con la altitud declarada las estaciones difieren 160 mbar por hora; con la barométrica, 2.3 mbar
  (IQR 0.4). **La presión no necesita grupos**: se muestra como desvío respecto a las vecinas.
- `z_baro` se calculó el 2026-09-18 con los últimos 365 días y **no debe recalcularse por
  rutina**: si se recalcula, un cambio de nivel del barómetro se absorbe y deja de verse.
- La alta montaña (a ~60 km de la mina) oscila ±0.8 mbar con la estación respecto a la mina: es
  diferencia regional real. Por eso cada estación se compara solo con vecinas a < 25 km.

---

## 4. Control de calidad (`qc.py`)

| Regla | Qué descarta | Detalle |
|---|---|---|
| `ZERO_RECORD` | T, HR y BP = 0 a la vez (registro vacío del logger) | BP = 0 sola no invalida T y HR: en Chancado 2022-2024 seguían válidas |
| `RANGE` | fuera de rango físico | T [−30, 45], HR [0, 103], BP [500, 1050], WS [0, 40], WD [0, 360] |
| `STUCK` | ≥ 6 h con el mismo valor (12 h en presión) | niebla (HR ≥ 95) y calma (WS < 0.5) exentas si duran < 24 h; HR ≥ 99.5 siempre exenta |
| `SPIKE` | Hampel 24 h (k = 6, piso 1) **y** apartado de sus vecinas (< 17 km) más de 2 °C / 10 % HR | sin el filtro de vecinas, el 80 % de los descartes eran subidas solares y tormentas reales |
| `BARO_DEV` | presión reducida a > 2 mbar de la mediana de sus vecinas (mediana móvil 24 h) | detecta reubicaciones y escalones; los desvíos menores se ven en la figura |

Descarte en el último año: T 0.17 %, HR 0.17 %, BP 3 % (casi todo Apacheta), viento < 0.2 %.

Casos conocidos que el QC detecta (verificados sobre el historial completo):

- Barómetro de Apacheta pegado en ~654 mbar (dic-2025 → hoy).
- Registros en cero de Apacheta (2019-11 → 2021-04).
- Minas_Sur con desvío de +24 a +55 mbar hasta 2023-11 (reubicación de ~280 m).
- Camp_Quellaveco (hasta 2022) y Cortadera (hasta 2022-09): escalones de presión de 5–7 mbar.
- Temperatura pegada de Chancado (2023-01 → 2024-04, racha de 2 268 h).
- Temperaturas de −517 °C (Tala-1, Calientes1) y excursión de presión de Vizcachas (2023).
- Barómetro de Ilo con resolución de 1 mbar: repite 6–13 h sin fallar (por eso 12 h en presión).

---

## 5. Agrupamiento (`grouping.py`)

- **Métrica:** correlación de anomalías, donde anomalía = valor − media de esa misma hora del día
  en ±15 días de la propia estación. Restar la mediana de toda la red agrupa peor (pares a 16.6 km
  y 383 m de desnivel de media contra 5.0 km y 165 m).
- **Vista por grupo: solo temperatura y humedad.** Con viento, la correlación interna de los grupos
  era 0.66–0.86 y juntaba estaciones que en T no se parecen (Camp con Chancado); sin viento
  sube a 0.84–0.93.
- **Corte:** dendrograma de enlace promedio, partiendo solo las ramas de más de 6 estaciones. Una
  estación suelta se une al grupo de su pareja más correlacionada o, si está lleno, forma grupo
  con sus 2 más parecidas (puede aparecer en dos grupos). Ilo va aparte.
- La distancia y el desnivel pesan parecido en la similitud entre pares (Spearman: velocidad
  −0.55 / −0.50, lluvia −0.67 / −0.46). Con coordenadas malas parecía que solo importaba el desnivel.

Grupos actuales (vista por grupo, T + HR, 2025-09 → 2026-09):

| Grupo | r interno | Estaciones |
|---|---|---|
| G1 | 0.90 | Altarani, Alto_Tala, Camp_Quellaveco, Charaque, Dique_pie_botadero, Tala_Legal |
| G2 | 0.75 | Calacaja, Calientes1, Chalsos, Cortadera, DME3_Cortadera |
| G3 | 0.93 | Alto_Quellaveco, Minas_Sur, Sarallenque_MQG-15-02 |
| G4 | 0.85 | Alto_Tala, Cerro_Salviani, Papujune |
| G5 | 0.91 | Apacheta, Papujune, Planta_Concentradora |
| G6 | 0.86 | Camp_Quellaveco, Chancado_primario, Dique_pie_botadero |
| G7 | 0.86 | Dique_pie_botadero, Minas_Sur, Tala-1 |
| G8 | 0.91 | Huachunta, Titire, Vizcachas |

Nota: la métrica del agrupamiento quita el ciclo diario; el ojo, con el botón «centrado», ve el
ciclo diario. Dos estaciones pueden compartir el tiempo del día a día y aun así verse distintas si
su ciclo diario difiere (caso Chancado).

---

## 6. Visor

- Botón «Valores: reales / centrados»: resta a cada estación su mediana de la ventana (sin dividir
  por la desviación, para no deformar la amplitud). Solo redibuja las figuras en pantalla o cerca
  de ella; las demás se ponen al día al entrar en pantalla.
- Descartes del QC: huecos en la línea y cruces en la traza «Descartado por QC» (oculta al abrir).
- Leyenda de viento con el tipo de sensor: «ClimaVUE ~2 m» o «torre».

---

## 7. Sensores

ClimaVUE (fuente: partes de campo): Chalsos, MQG-15-02, DME3-Cortadera, Calacaja, DPB-1,
Apacheta, Planta Concentradora, EHA-TIT-1, Chancado Primario, Cerro Salviani, Minas Norte (desde
2026-08-28), Calientes 1, Charaque, Ilo (sin confirmar). El resto son torres a 10 m.

El pluviómetro deja huella: ClimaVUE registra en pasos de 0.017 mm y la cubeta Young en 0.1 mm.
Con eso se fecharon los cambios al pluviómetro Young (`# inferido` en `stations.py` cuando no hay
parte que lo respalde):

| Estación | Lluvia de la Young desde |
|---|---|
| Chancado Primario | 2025-03-15 (con barómetro nuevo; la presión reducida cambia de nivel ese trimestre) |
| Calientes 1 | 2025-05 (inferido) |
| Ilo | 2025-07 (inferido) |
| Charaque, Apacheta | 2025-12 (inferido) |
| Planta Concentradora | 2026-02-01 |
| EHA-TIT-1 | 2026-02-11 |
| Cerro Salviani | 2026-02-12 (también T y HR de un HygroVUE) |

Altura del anemómetro: entre Camp (torre) y Chancado (ClimaVUE), a 1 km, las medianas de
velocidad son casi iguales, pero la torre sopla ~2× entre 10 y 18 h y ~0.65× de noche. El efecto
de la altura está en el ciclo diario, no en la mediana. No se corrige a 10 m (depende de una
rugosidad que no se conoce).

---

## 8. Fallos de sensor por revisar con partes de campo

| Estación | Variable | Síntoma | Hipótesis |
|---|---|---|---|
| Camp_Quellaveco | T | mismo ciclo diario que Charaque, pero la diferencia mensual salta entre ~+0.4 y −3 °C (dic-2024 → feb-2026) y sube a +1.5 desde mar-2026 | cambios de calibración o de sensor; el QC no detecta escalones en T |
| Chancado_primario | T | +2.2 a +2.6 °C de día respecto a sus vecinas, igual de noche; amplitud diaria de ~10 °C (2025) a 14–15 °C (jun–jul 2026) | radiación sobre el sensor (protector solar), empeorando |
| Dique_pie_botadero | viento | ciclo invertido (fuerte de noche 4.7–5.1 m/s, flojo a mediodía 2.2), nunca baja de ~1.1 m/s, constancia direccional 0.98, no correlaciona con ninguna vecina | flujo de drenaje real al pie del botadero o fallo del anemómetro |
| Chalsos | dirección | ~270° de noche y 120–160° de día, al revés que Calientes1/Cortadera/Tala_Legal (~100° / ~270°) | veleta invertida o mal orientada |
| Huachunta | dirección | veleta pegada en ~152° (mar–may 2026); constancia direccional = 1.00 | fallo mecánico |
| Papujune | T | 132 h con 0.0 exacto (abr-2026) | sensor caído (descartado por `STUCK`) |
| Charaque | HR | 752 h en 101.2 % (ene–abr 2025), aceptadas por el rango | calibración |
| Apacheta / Minas_Sur | HR | cambio de nivel en ene-2026 / may-2026 | cambio de sensor (Apacheta: mismo mes que su pluviómetro) |
| Calientes1 | T, HR | jul-2025: 64 % de valores redondeados a un decimal (normal ~10 %) | cambio de programa |

Calacaja no es un fallo: está ~800 m más abajo que Calientes1 y es constantemente +4.5 °C más
cálida, con el mismo ciclo diario. Sus parejas son Calientes1, Chalsos y DME3.

---

## 9. Viento (en curso)

La serie horaria de velocidad se ve demasiado ruidosa. Propuesta, contrastada con fallos
conocidos:

1. **Ciclo diario medio de velocidad** — delata el ciclo invertido de Dique y el efecto 2 m / 10 m.
2. **Ciclo diario de dirección por media vectorial** — delata la orientación de Chalsos y el
   patrón valle-montaña, sin saltos falsos en 0°/360°.
3. **Mapa de calor hora del día × día** — ubica cuándo empieza un fallo.
4. **Constancia direccional diaria** (|vector medio| / velocidad media) como indicador: vale 1.00
   con la veleta pegada. El rango normal depende de la estación (mediana 0.26–0.90), así que el
   umbral no puede ser único.

Las rosas de viento día/noche quedan para después: con 6 estaciones son 12 gráficos polares y en
ventanas de 7–30 días repiten lo que muestra el ciclo diario.

Referencias verificadas (EPA):

- _Meteorological Monitoring Guidance for Regulatory Modeling Applications_ (EPA-454/R-99-005):
  «Some problems that may escape detection during an audit (e.g., a wind vane that occasionally
  gets stuck) are often easily identified during data validation.»
  https://www.epa.gov/sites/default/files/2020-10/documents/mmgrma_0.pdf
- _QA Handbook Vol. IV: Meteorological Measurements_ (EPA-454/B-08-002): «A significant change in
  wind rose plots may indicate a problem with the monitoring system … For example, a misalignment
  of the w[ind vane] …»
  https://www.epa.gov/sites/default/files/2020-10/documents/volume_iv_meteorological_measurements.pdf

---

## 10. Pendientes

- Implementar la sección de viento (§9).
- Curar `groups_draft.py` → `groups.py`.
- Regla de QC para escalones de nivel en T y HR (caso Camp_Quellaveco), comparando con vecinas.
- Confirmar con partes de campo los casos de §8 y la coordenada de Campamento Quellaveco.
- Lluvia y radiación: pendientes.
