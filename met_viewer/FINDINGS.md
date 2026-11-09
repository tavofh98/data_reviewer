# Visor de meteorología por grupos — hallazgos y decisiones

_Actualizado: 2026-09-28 · Base: `database_duck/anglo_ambiental.db` (datos 2019-09 → 2026-09-28)_

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
| `WIND_REVIEW.md` | metodología y criterios para revisar los datos de viento |

La norma de qué variables importan es `anglo_reporte/matrices.py` → `VARIABLES_REPORTE`. El
Excel de `anglo_reporte` no se toca.

---

## 2. Coordenadas y altitudes

- **Las coordenadas y altitudes de `control_calidad_aaq/config.py` no sirven.** Con un DEM
  (SRTM/ASTER 30 m) el terreno en esos puntos queda 1 000–2 000 m por debajo de la estación, y
  las altitudes declaradas difieren de las barométricas hasta en 1 495 m (Calacaja). La tabla
  tiene además valores copiados (Calientes1 y Charaque comparten este; dos pares comparten
  altitud).
- **Fuente válida: `references/Estaciones AAQ.kmz`** (ubicado en Google Earth). Con sus
  coordenadas, DEM y altitud barométrica coinciden en las 24 estaciones con barómetro.
- **Altitud de trabajo: la barométrica** (`z_baro`), anclada al DEM: |z_baro − z_dem| ≤ 30 m,
  mediana 10 m.
- Por confirmar: en el KMZ, «Campamento Quellaveco» tiene la misma coordenada que «Botadero
  Altaranito Norte».

### Datos de campo: el datum antes que el número

SRTM (EGM96), ASTER (EGM96) y Copernicus (EGM2008) son ortométricos, igual que `z_baro`, que
sale de la presión: se comparan entre sí sin corrección. **Un GPS de mano, no.** Muchos dan
altura elipsoidal, y aquí el geoide está unos +40 m por encima del elipsoide (N = +28 en Ilo,
+38 a +42 en la mina, +44 en Vizcachas/Huachunta, EGM2008). Antes de aceptar una altitud de
campo: si difiere de `z_baro` en ~40 m, es elipsoidal; réstale N. Dos equipos distintos del
mismo contratista venían configurados al revés, así que la comprobación va estación por
estación, no por equipo.

Verificado el 2026-09-21 con datos de campo:

| Estación | Dato de campo | Veredicto |
|---|---|---|
| Vizcachas | cartel 355636 E, 8159328 N, 4390 m; GPS a 3 m, 4382.8 m (ortométrico) | **aceptado**: dos fuentes a 3 m entre sí, altitud a −5 m de `z_baro`. `stations.py` actualizado |
| Vizcachas | primer GPS: 208 m al oeste, 4172 m | descartado: la posición es plausible (terreno llano), la altitud está 216 m baja |
| Cortadera | cartel 321300 E, 8099690 N, 3295 m | **descartado**: su altitud queda 111 m por debajo del terreno en su propia coordenada |
| Cortadera | fotos de GPS de varios meses, 3405–3420 m (elipsoidal) | al restar N = +40.2 dan 3365–3380, de acuerdo con Copernicus (3370–3380) y con `z_baro` (3374) |
| DME3_Cortadera | dos GPS a 9 m entre sí, 30 m al oeste del KMZ: 2911.4 m (ortométrico) y 2949–2960 m (elipsoidal) | **aceptado**: leído cada uno en su datum convergen en 2910–2921, con `z_baro` = 2922 en el borde. `stations.py` actualizado |
| Camp_Quellaveco | cartel idéntico al KMZ (0 m) y dos GPS a 10–16 m; altitudes de 3590 a 3640 | coordenada **confirmada**; altitudes descartadas por dispersión. La cerró el certificado del barómetro, no el GPS |
| Charaque | GPS a 6 m del KMZ, 3627–3634 m | coordenada **confirmada**; la altitud es ortométrica sin duda (como elipsoidal caería 44–52 m bajo el terreno) y contradice `z_baro` = 3660. Ver la predicción abajo |
| Calientes1 | GPS a 12 m del KMZ, sin altitud | coordenada **confirmada** |
| Mina_Norte | GPS 326497 E, 8110200 N, 4004–4015 m (elipsoidal) | altitud **aceptada**: menos N ≈ 40 da 3964–3975, igual que SRTM (3969 en ese punto, 3972 en el KMZ) y 8–19 m bajo `z_baro` = 3983. Coordenada **en duda**: cae a 782 m del KMZ, que no es error de GPS; posible reubicación al instalar el ClimaVUE (2026-08-28). No se cambia hasta confirmarlo |

**Mina_Norte ya tiene barómetro** (ClimaVUE, en la base desde 2026-08-30; antes la ingesta no
cargaba su T, HR y presión). Con 22 días, reducida contra 22 estaciones con `z_baro` fijada
(T media de 24 h, gravedad real), da `z_baro` = 3983 m: 3974–3986 con las 14 vecinas a ≤ 10 km y
3974–3988 con toda la red hasta 63 km. Queda 11 m sobre el DEM, dentro de la tolerancia de la
red y de la del sensor (±1 mbar del ClimaVUE ≈ ±13 m a 635 mbar). Recalculado el 2026-11-09 con
`calibrate_baro.py`: 3980 m con 71 días (2026-08-30 → 11-09; +8 m sobre el DEM) y 3976 m con los
últimos 35. Se mantiene 3983 en `stations.py`: la diferencia (≤ 7 m) es menor que la tolerancia del sensor.

**Ilo, contra el nivel del mar.** No entra en el ajuste de la red, así que se contrastó con la
presión a nivel del mar de ERA5 (Open-Meteo), hora a hora, 2025-09 → 2026-09: altura
geopotencial ≈ 40 m (mediana 39.5; 41 desde 2026-01), de acuerdo con el DEM (46). Los 16 m que
se le suponían no se sostienen. En 2026-01 salta +11 m (≈ 1.3 hPa): cambio o ajuste del
barómetro. El nivel absoluto depende de ERA5: 1 hPa son unos 8 m.

**Predicción abierta sobre Charaque.** Su GPS (3627–3634) coincide con el DEM (3637) dentro de
3–10 m y discrepa de `z_baro` (3660) en 26–33 m. Dos fuentes independientes contra una, y con
una dispersión de GPS de solo 7 m. Si el GPS acierta, el barómetro de Charaque **lee 2.30 mbar
por debajo del patrón**: pedir su certificado lo confirma o lo refuta. Nótese el contraste con
Camp_Quellaveco, donde el certificado dio 0.43 mbar y ganó `z_baro`. No se toca `z_baro` con un
número inferido del GPS: como `z_baro` absorbe el sesgo, cambiarla sin corregir a la vez la
presión rompería la coherencia y dispararía `BARO_DEV`.

**Las coordenadas del KMZ son buenas.** Cinco estaciones contrastadas en campo —Vizcachas,
DME3_Cortadera, Camp_Quellaveco, Charaque y Calientes1— confirman el KMZ dentro de 3 a 34 m.
Los residuales que quedan **no son errores de coordenada**: son relleno minero que el DEM no vio
o sesgo de barómetro. La auditoría de coordenadas está cerrada salvo prueba en contra; lo que
queda es calibración.

**El DEM lee bajo donde hay obra.** En DME3 el GPS cae por encima del DEM (2907) y por debajo
de `z_baro` (2922). No es un error de coordenada: un DME es un depósito de material excedente,
un terraplén construido, y SRTM se levantó en el año 2000. Donde la estación se asienta sobre
relleno minero, el DEM no lo ve y `z_baro` es la buena. Esto explica la firma común de los
peores residuales —barómetro por encima del terreno—, y es la hipótesis principal para
Camp_Quellaveco, que comparte coordenada con «Botadero Altaranito Norte». Corolario: en esas
estaciones un DEM nunca va a cuadrar, así que el criterio es el GPS de campo más `z_baro`, no
el DEM.

### Estaciones por verificar, en orden

Residual `z_baro` − `z_dem`, como lo imprime `calibrate_baro.py`: positivo = el barómetro sitúa
la estación por encima del terreno del DEM, que es la firma del relleno minero.

Ya no se piden coordenadas, sino **certificados de calibración**, por este orden:

1. **Charaque** (+23 m): coordenada confirmada y GPS de acuerdo con el DEM. Predicción concreta
   de 2.30 mbar, ver arriba. Es el que más rinde.
2. **Calientes1** (+16 m): coordenada confirmada, sin altitud. Relleno o sesgo, sin distinguir.
3. **Apacheta** (+14 m) y **Sarallenque_MQG-15-02** (+14 m): misma firma, sin dato de campo.
4. **Chancado_primario** (−17 m): le cambiaron el barómetro el 2025-03-15, así que su `z_baro`
   mezcla dos niveles. Aquí no basta un certificado: hay que recalibrar por tramos.
5. **Titire** (−14 m) y **Cortadera** (−12 m): sin indicio adicional.

Resueltas el 2026-09-21: **DME3_Cortadera** y **Camp_Quellaveco** (coordenada confirmada en
campo y altitud cerrada por el certificado del barómetro; el DEM es el que lee 24 m bajo).

**Las altitudes de GPS de mano no sirven para esto.** En Camp_Quellaveco, fotos tomadas en la
misma estación con dos horas de diferencia dan de 3 590 a 3 640 m: 50 m de dispersión. La
estación está al pie de una colina que le tapa cielo, y con menos satélites y peor geometría el
error vertical se dispara (en un GPS de mano ya es de 1.5 a 3 veces el horizontal). De esas
fotos se aprovecha la posición horizontal, que confirmó la coordenada a 10–16 m; la altitud, no.

Sin barómetro reducible, es decir sin nada contra lo que contrastar, y tres de ellas en terreno
accidentado donde el DEM es lo menos fiable: **Sarallenque** (relieve 99 m), **PMC-4_met**
(71 m) e **Ilo**. Aquí un dato de campo vale el doble. (Mina_Norte salió de esta lista el
2026-09-21, al empezar a registrar presión.)

ASTER lee unos 7 m por debajo de SRTM en toda la red: para comparar, SRTM.

---

## 3. Presión: reducción hidrostática

Cada presión se reduce a 4 000 m con la ecuación hipsométrica (temperatura de la columna a
partir de la T de la estación suavizada 24 h y un gradiente estándar) usando `z_baro` fija.

**La gravedad no es constante** (corregido el 2026-09-21). Con `g₀` = 9.80665 la hipsométrica
devuelve altura *geopotencial*, mientras que el DEM y el GPS dan *geométrica*: son cosas
distintas. Ahora se usa la gravedad normal de Somigliana en la latitud media de la red
(−17.1° → 9.78479, un 0.22 % menos) más la corrección de aire libre (3.086·10⁻⁶ s⁻²). El sesgo
constante lo reabsorbe el anclaje, así que lo que queda es una inclinación de 7 m a lo largo de
los 2 080 m de desnivel de la red: las estaciones bajas bajan hasta 5.5 m y las altas suben
hasta 1.5 m. La latitud va fija: la franja de 16.5° a 17.8° S vale 0.0025 % (0.09 m a 3 600 m).

Mejora medible contra las tres estaciones verificadas en campo — error medio de 4.2 m a 1.2 m:

| Estación | Campo | con `g` constante | con `g` real |
|---|---|---|---|
| Vizcachas | 4390 (cartel) | 4388 | **4390** |
| DME3_Cortadera | 2910–2921 (dos GPS) | 2923 (fuera) | **2919** |
| Cortadera | 3365–3380 (GPS + Copernicus) | 3376 | **3373** |

- Con la altitud declarada las estaciones difieren 160 mbar por hora; con la barométrica, 2.3 mbar
  (IQR 0.4). **La presión no necesita grupos**: se muestra como desvío respecto a las vecinas.
- `z_baro` se calculó el 2026-09-21 con los últimos 365 días y **no debe recalcularse por
  rutina**: si se recalcula, un cambio de nivel del barómetro se absorbe y deja de verse.

**El punto ciego del método, y cómo se cierra.** La sensibilidad es de 7.8 mbar por cada 100 m,
así que un sesgo de calibración del barómetro es matemáticamente indistinguible de un cambio de
altitud: 2.35 mbar se leen como 30 m, y el ajuste los absorbe enteros dentro de `z_baro` sin que
nada lo delate. Por eso `z_baro` no puede usarse como prueba de sí misma. Lo único que lo cierra
es un certificado de calibración, que mide el sesgo directamente. El de Camp_Quellaveco (2026:
estación 662.80 mbar, patrón 663.23) dio 0.43 mbar = 5.5 m, cuatro veces menos de lo que haría
falta para dudar de su altitud. **Pedir los certificados del resto de barómetros es lo que más
rinde ahora**: convertiría `z_baro` de cantidad ajustada en cantidad medida para toda la red.
Los offsets se anotan en `stations.py` → `BARO_OFFSET` y los aplica `data.load`, de modo que la
presión reducida y `z_baro` quedan las dos en el valor verdadero.
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

- Barómetro de Apacheta casi congelado desde 2025-12-23 (ver §8).
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
- **Viento: por régimen, no por anomalías** (2026-09-23). Parecido = coseno entre los ciclos
  diarios medios del vector de procedencia (u y v por hora). No depende de la escala, así que la
  altura del sensor no manda. La correlación de anomalías de velocidad era débil (r típica
  0.15–0.35 a < 25 km) y juntaba regímenes opuestos (Altarani–Charaque–Sarallenque: −0.26). Fuera
  del cálculo, los tramos de `stations.WIND_EXCLUDED` (Sarallenque desde 2025-07-14, Mina_Norte y
  Chalsos completas, el tramo pegado de Huachunta). La estación con parecido medio < 0.60 al
  resto de su grupo va sola (Dique_pie_botadero: 0.55). Grupos 2025-09 → 2026-09: cos medio 0.92,
  0.83, 0.92, 0.90 y 0.70 (Calacaja–DME3).
- La distancia y el desnivel pesan parecido en la similitud entre pares (Spearman: velocidad
  −0.55 / −0.50, lluvia −0.67 / −0.46). Con coordenadas malas parecía que solo importaba el desnivel.

Grupos actuales (vista por grupo, T + HR, 2025-09 → 2026-09):

| Grupo | r interno | Estaciones |
|---|---|---|
| G1 | 0.90 | Altarani, Alto_Tala, Camp_Quellaveco, Charaque, Dique_pie_botadero, Tala_Legal |
| G2 | 0.75 | Calacaja, Calientes1, Chalsos, Cortadera, DME3_Cortadera |
| G3 | 0.93 | Alto_Quellaveco, Minas_Sur, Sarallenque_MQG-15-02 |
| G4 | 0.85 | Alto_Tala, Cerro_Salviani, Papujune |
| G5 | 0.91 | Apacheta, Mina_Norte (a mano), Papujune, Planta_Concentradora |
| G6 | 0.86 | Camp_Quellaveco, Chancado_primario, Dique_pie_botadero |
| G7 | 0.86 | Dique_pie_botadero, Minas_Sur, Tala-1 |
| G8 | 0.91 | Huachunta, Titire, Vizcachas |

**Estaciones con menos de 60 días quedan fuera sin aviso** (2026-09-28). `distancia()` descarta
la estación con menos de `24 · MIN_DIAS_COMUNES` horas válidas, y en T y HR no hay figura propia
para las que quedan fuera (en viento sí). Caso Mina_Norte: la base tiene T/HR/P desde 2021, pero
hasta el 2026-08-28 18:00 son registros en 0 (sin ClimaVUE) que el QC descarta como `ZERO_RECORD`;
quedan ~30 días válidos y la estación no salía en temperatura, humedad ni presión. `main.py` sí lo
avisa («estaciones con datos que no están en ningún grupo»). Decisión del usuario: no cambiar el
criterio del programa, sino añadirla a mano en `groups_draft.py` con la misma regla de `cortar()`,
usando la correlación de anomalías del tramo válido (2026-08-28 18:00 → 2026-09-28 12:00):

| Variable | Más correlacionadas | Ubicación |
|---|---|---|
| AirTC_Avg | Planta_Concentradora 0.92, Papujune 0.88, Minas_Sur 0.88 | G1 lleno → trío nuevo con Papujune y Planta_Concentradora |
| RH_Avg | Charaque 0.95, Altarani 0.94, Minas_Sur 0.94 | G1 lleno → trío nuevo con Altarani y Charaque |
| combinado | Planta_Concentradora 0.92, Minas_Sur 0.91, Altarani 0.90 | se une a G5 |

Regenerar `groups_draft.py` con `grouping.py` borra esta adición. Con 60 días ya cumplidos, la
regeneración del 2026-11-09 la incluye sola: en T entra en el grupo con Apacheta, Papujune y
Planta_Concentradora; en HR con Camp_Quellaveco, Charaque, Papujune y Planta_Concentradora; en el
combinado en un grupo de 6 (r medio 0.90) con Altarani, Camp_Quellaveco, Charaque, Papujune y
Planta_Concentradora. Ya no hace falta la adición a mano.

**Registros cortos y Calacaja** (2026-11-09). Con 73 días válidos, Mina_Norte entraba en el corte
junto a estaciones de 365 días y deformaba la partición de HR: sin ella el ARI entre ventanas de
90 d sube de 0.63 a 0.90 (en T, de 0.53 a 0.55). Quitar una estación cada vez en HR, con
Mina_Norte aún dentro, daba también Charaque (+0.24), Alto_Tala (+0.24), Planta_Concentradora
(+0.16) y Camp_Quellaveco (+0.14); era un efecto de Mina_Norte, no de ellas: con Mina_Norte ya
fuera, quitar Alto_Tala o Camp_Quellaveco cambia el ARI de HR en −0.03 y −0.01 (no estorban), y
lo único que sube algo es Cerro_Salviani (+0.05) y Apacheta (+0.04). Alto_Tala queda en su grupo
(Tala-1, Tala_Legal, Dique, Camp_Quellaveco, Charaque) en las 10 ventanas de 90 d (margen mínimo
0.02, en la estación seca, cuando todas se parecen); Camp_Quellaveco en 9 de 10: en nov→feb
pasa al lado de Chancado_primario (r 0.94 frente a 0.92). En T, sin Mina_Norte, la que más
estorba es Tala-1 (+0.08; sus escalones de nov-dic) y las que estabilizan, Tala_Legal (−0.09) y
Dique (−0.05). Desde `grouping.py` actual, las estaciones con menos de 180
días con dato (`MIN_DIAS_NUCLEO`) no entran en el corte: se asignan después al grupo de menor
distancia media y, si el segundo queda a menos de 0.05 (`MARGEN_CORTAS`), aparecen en los dos.
Mina_Norte queda así en dos grupos en T (margen 0.036), HR (0.036) y combinado (0.003): es una
estación puente, no de un solo grupo. Los grupos del combinado vuelven a ser los de la tabla
anterior, con Mina_Norte añadida. Se corrigieron las figuras repetidas del viento (Camp_Quellaveco
dos veces; Cerro_Salviani sola y dentro de un grupo).

**Calacaja no es una estación rara, está aislada** (2026-11-09). Con los 231 pares sin ella se
ajusta r = 1.07 − 0.143·ln(km) − 0.016·(Δz/100 m) en T y r = 1.12 − 0.139·ln(km) − 0.016·(Δz/100 m)
en HR. Calacaja queda dentro de lo que predice ese modelo (residuo medio +0.06 en T y −0.04 en
HR, menos de 1 sd): es la única estación bajo 3000 m salvo DME3_Cortadera (587 m más arriba, a
8 km), y sus otras vecinas están a 13–19 km y 780–1440 m más arriba. Sin desfase horario con DME3
(el máximo de r está en 0 h), con amplitud diaria y varianza normales (rango diario 7.6 °C, sd de
anomalía 1.4 frente a 1.6 de la red). Por franja del día, r con DME3 en T: 0.87 de 12 a 18 h y
0.56 de 0 a 6 h (HR 0.85 y 0.70); en T cae también en mayo (0.47) y julio (0.51). Es compatible
con drenaje de aire frío o brisa local de valle de noche, pero no lo he probado. No hay indicio
de fallo: le falta pareja. Decisión del usuario (2026-11-09): ninguna estación sola en T y HR, así
que Calacaja va en el grupo del suroeste (Calientes1, Chalsos, Cortadera, DME3_Cortadera), de
donde es el eslabón débil. Su r de anomalías con ese grupo es 0.65 en T y 0.59 en HR frente a
0.81–0.88 y 0.78–0.84 de las demás; el r medio interno del grupo pasa de 0.85 a 0.77 en T y de
0.82 a 0.73 en HR (combinado: 0.75). Por ventanas de 90 d su r con el grupo oscila entre 0.50 y
0.72 en T y entre 0.48 y 0.79 en HR. Apacheta no entra: se parece más a Papujune, Planta y
Cerro_Salviani (0.87 en T, 0.88 en HR) que al suroeste (0.75 y 0.73). Cortadera sí encaja (0.85 y
0.82). El visor muestra bajo ese grupo una leyenda con estas cifras (`NOTES` en `groups.py`). En
viento Calacaja sigue sola (sin pareja por régimen).

**El tope de 6 no fabrica la inestabilidad** (2026-11-09, sin Mina_Norte, 365 d). Se comparó con
topes de 4 a 10 y con cortes por umbral de distancia (sin tope), midiendo r de anomalías dentro
de los grupos, ARI entre ventanas de 90 d y entre 4 bloques disjuntos, y cuántos pares de
r anual ≥ 0.92 quedan juntos:

| Corte | HR: r dentro / ARI bloques / pares juntos | T: r dentro / ARI bloques / pares juntos | Mayor grupo (HR, T) |
|---|---|---|---|
| tope 6 (actual) | 0.91 / 0.76 / 0.76 | 0.88 / 0.54 / 1.00 | 6, 6 |
| tope 8 | 0.91 / 0.83 / 0.82 | 0.87 / 0.48 / 1.00 | 7, 7 |
| umbral 0.16 | 0.88 / 0.51 / 0.98 | 0.88 / 0.42 / 1.00 | 14, 6 |
| umbral 0.25 | 0.87 / 0.72 / 1.00 | 0.81 / 0.55 / 1.00 | 15, 16 |

Sin tope no es más estable (salvo con grupos de 15), y la cohesión interna baja. Sí se sostiene
una parte de la objeción: en HR, 1 de cada 4 pares con r ≥ 0.92 acaba en grupos distintos con
tope 6. Las diferencias de ARI de ~0.05 entre topes están dentro del ruido (6 pares de bloques).
El tope de 6 funciona como límite de tamaño de figura, no como criterio estadístico. Límite que
se acepta: el grupo con una estación puente pasa de 6.

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
| Dique_pie_botadero | viento | (1) desde 2024-T2, 0–0.5 % de las horas con viento de la mitad este (NNE–SSO), de día y de noche, cuando Tala-1 (0.5 km), Alto_Tala y Papujune reciben de noche el 51–83 % del NE–ENE; la dirección solo recorre 260°–278° en el día (Tala-1: 65° → 261°). (2) Nunca en calma: percentil 1 de 1.5–2.3 m/s, frente a un 3–32 % de calmas nocturnas en las vecinas. (3) El 2026-07-27 la velocidad de día baja de ~5 a ~2.3 m/s (Tala-1 sigue en 4–6), la de noche sube de ~4 a ~5.4 y su dirección pasa de ~300° a 271–274°: el ciclo invertido empieza ahí, antes el día doblaba a la noche. DEM (SRTM, anterior al botadero): cañón con horizonte de 35–42° hacia SE–S y abierto al OSO (247°, 1°) y, menos, al ENE (12°) | exposición: ClimaVUE ~2 m junto al shelter y a la ladera (dato del usuario, 2026-09-24); el sector este tapado o el flujo encauzado por el cañón y el botadero; qué cambió el 2026-07-27 está por confirmar en campo |
| Chalsos | dirección | ~270° de noche y 120–160° de día, al revés que Calientes1/Cortadera/Tala_Legal (~100° / ~270°) | veleta invertida o mal orientada |
| Huachunta | dirección | veleta pegada en ~152° (mar–may 2026); constancia direccional = 1.00 | fallo mecánico |
| Sarallenque | viento | desde 2025-07-14 dirección y velocidad cambian a la vez; de noche viene de ~250° en vez de ~78°; sector S–SO–O vacío. Reorientado el 2026-09-25 (marca N al norte; antes al sur) y shelter desplazado unos metros al E | confirmado en campo: sensor orientado al sur (180°). De día, además, la cara sur estaba tapada; con el desplazamiento ya no (ver §9) |
| Apacheta | presión | el barómetro del ClimaVUE (integrado) dejó de actualizarse el **2025-12-23 por la tarde** (en la base horaria hay 11 cambios en las 20 h de ese día y ninguno al siguiente; el `.dat` de 5 min tiene un hueco del 2025-11-01 al 12-23, así que la hora exacta, ~17:00, se apoya en solo 1.5 h de 5 min). Antes cambiaba en el 31–35 % de los registros de 5 min a cualquier temperatura (≈ 22 cambios al día en los datos horarios, como Papujune); desde 2026-01-20 cambia en ≤ 3 % (0 % con T ≤ 5 °C; casi todos los cambios caen entre 7 y 17 h) y, en horario, 0.3–3.1 cambios al día según el mes (ene–abr 1.9–3.1; mayo–nov 0.3–1.3). Los valores retenidos siguen centrados: Apacheta − Papujune ≈ +2 hPa antes y después, pero el desvío pasa de 0.15 a 0.8–1.4 hPa (la presión real varía ~1–2 hPa al día). T, HR y batería del mismo logger siguen normales. Del 2026-01-01 al 01-05 hubo cambios de nuevo (12, 11, 7, 5 al día) justo antes de un hueco de datos (01-06 → 01-11). Persistió tras la limpieza y reinicio físico del 2026-05-20 y el mantenimiento del ClimaVUE del 2026-06-03 (`intervenciones_meteorologia.csv`). Antes de 2021-05 son registros en cero (§4) | fallo del barómetro del ClimaVUE (o de su lectura por SDI-12): mide, pero devuelve casi siempre el mismo valor. El QC lo descarta por `STUCK` (≈ 672 h cada 30 días); por eso Apacheta queda fuera de `calibrate_baro.py` (< 30 días válidos). Coincide en fecha con el cambio de nivel de su HR (ene-2026, fila siguiente) y con el mes del pluviómetro Young (dic-2025, `stations.py`); qué se tocó el 2025-12-23 está por confirmar en campo |
| Camp_Quellaveco | viento | desde el 2022-10-06 (06–12 h) la velocidad nocturna cae a 0.3–0.6 veces la de sus vecinas (antes 0.8–1.0), con 25–70 % de horas en calma, y la dirección nocturna deja de seguirlas (de ~80° a 120–260°); de día sopla 1.3–2 veces más que ellas. Ese mismo día, la presión reducida baja 4.9 mbar (+7.0 → +2.2) | reubicación de la estación o de la torre a un punto más alto (~60 m) y resguardado de noche (criterios B y C de WIND_REVIEW, más `BARO_DEV`). También coinciden viento y presión el 2020-10-27; el escalón de −2.5 mbar del 2024-03-24 no tiene cambio de viento esa semana |
| Camp_Quellaveco | viento nocturno | tras la calibración del 2026-09-10, el 37 % de las horas de noche en 0.00 exacto (antes 0 %), en noches enteras (14→15, 16→17, 22→23 sep) mientras Chancado (0.7 km) sopla 1.3–2.3 m/s del NE; la dirección queda congelada toda la noche con décimas de grado (94.6–95.1°, 66.2°, 87.4°). Antes de la calibración, la dirección nocturna cambiaba 43° de una hora a otra (Chancado: 20°) y con < 0.5 m/s apuntaba a 205–245°, contra el drenaje NE–E de las vecinas; parecido con Chancado: 36° de diferencia mediana en ago–sep 2025, 54° antes y 49° después. De día, sin cambio (oeste en el 98–100 % de las horas; +6° desde el 14-sep) | después: sensor que no arranca (rozamiento, umbral o programa); antes: ruido de un sensor en su umbral, ya peor que en 2025. De noche solo valen las horas con ≥ 0.5 m/s. Criterio G de WIND_REVIEW |
| Camp_Quellaveco | viento (veleta y hélice, Young) | Con 5 min, frente a Altarani y Charaque y a las mismas fechas de 2025. Deterioro desde mediados de agosto de 2026: la desviación de la dirección dentro del registro (SD1) frente a Altarani baja de 1.3–1.5 (jun–jul) a 1.14 (semana del 08-10), y los ceros exactos con vecinas a 1–5 m/s suben de 3–6 % a 12 % (08-24), 20 % (09-07) y 35 % (09-14). Tras el cambio de base del 09-10: SD1 de 0.6–0.8, cambio de dirección entre registros consecutivos 0.3–1.0 veces el de Altarani (2025: 1.1–4.0) y dirección repetida (< 0.5°) en el 12–17 % de los registros (2–3 %). De noche, con CQ = 0.00 y Charaque a 2.7 m/s, la dirección queda congelada (desviación circular de 0–0.6° durante noches enteras) en ~89°, a < 45° de Charaque en el 92 % de los registros: cabezal alineado e inmóvil y hélice parada. La regresión contra las vecinas da intercepto de −1.9 m/s frente a −1.5 en 2025, con la misma pendiente (efecto de umbral, no de escala). 2026-09-17 (primer abatimiento): sin cambio. 2026-10-20 (segundo): con vecinas a 3–5 m/s los ceros bajan de 20 % a 5 %, pero siguen en 24–30 % con 1–3 m/s y SD1 en 0.55–0.75 (solo 14 días de datos); la dirección diurna gira de forma rígida −43° a −55° en todos los bloques de 2 h (Charaque −1° a −4°; mismo recorte de 2025 −1° a −3°) | Dato de campo (usuario): en la calibración del 09-10 la base estaba rajada y se cambió por una de otro modelo, con más resistencia al giro; el 2.º abatimiento aflojó el encaje y varió la orientación. La fricción explica el cabezal inmóvil; la hélice parada con el cabezal alineado no queda explicada del todo (por comprobar en campo: giro libre de la hélice, nivel de la base, conector). Cuál orientación es la correcta tras el 10-20 está sin decidir (medirla con brújula). Excluido en `WIND_EXCLUDED` desde 2026-08-10 hasta confirmar la reparación. No cambia los grupos de viento (ya queda aparte por la forma de su ciclo de velocidad) |
| Papujune | T | 132 h con 0.0 exacto (abr-2026) | sensor caído (descartado por `STUCK`) |
| Charaque | HR | 752 h en 101.2 % (ene–abr 2025), aceptadas por el rango | calibración |
| Apacheta / Minas_Sur | HR | cambio de nivel en ene-2026 / may-2026 | cambio de sensor (Apacheta: mismo mes que su pluviómetro) |
| Calientes1 | T, HR | jul-2025: 64 % de valores redondeados a un decimal (normal ~10 %) | cambio de programa |
| Cortadera | dirección | desde 2026-09-13 13:00 (faltan 11 y 12 h): giro rígido de −73° ± 4°, igual de día y de noche (−74° / −71° frente a Calientes1; seis vecinas coinciden) | visita de campo; se restituye sumando +73°. Fuente: `wind_vector/consensus/audit/r2` |
| Alto_Quellaveco | dirección | desde 2026-09-15 12:00 (falta 11 h): giro rígido de −88° ± 5° (−85° / −94° frente a Minas_Sur, día / noche) | visita de campo; se restituye sumando +88° |
| Cortadera | dirección nocturna | desde sep-2022 las noches en 90–135° pasan de 0–2 % a 46–71 % (53–65 % desde 2023); antes el 84 % caía en 45–90° | cambio de sitio o de orientación sin fechar con exactitud; sin confirmar |
| Altarani | dirección nocturna | ene–mar 2025: noches en 90–180° al 52 %, 0 % y 17 % (resto de meses 92–98 %); en feb-2025 la noche viene de ~288° | fallo o giro temporal no documentado; fuera del periodo del consenso |
| Planta_Concentradora | dirección | desde 2024-04-06: de día +73° respecto a Papujune y de noche −9°; coseno del ciclo diario con las vecinas −0.15 a 0.44 (antes 0.77–0.95) | cambio de orientación o de sitio; no es un giro único (signos opuestos día/noche). Cifras de la revisión externa, sin verificar por separado |
| Camp_Quellaveco | dirección nocturna | en horas con > 1 m/s la noche no tiene dirección dominante desde el 2022-10-06 (constancia 0.05–0.20, antes 0.84–0.92), repartida en los cuatro cuadrantes | sitio, no anemómetro: el punto nuevo es turbulento de noche (`audit/r2`); complementa la fila de la reubicación |
| Charaque / Sarallenque_MQG-15-02 | viento | registros congelados (dirección y velocidad fijas): Charaque 2026-01-14 14:00 → 01-15 12:00 y 2026-01-28 14:00 → 01-29 07:00; MQG 2026-02-16 14:00 → 02-17 09:00 | logger o registro; sin verificar por separado |

Calacaja no es un fallo: está ~800 m más abajo que Calientes1 y es constantemente +4.5 °C más
cálida, con el mismo ciclo diario. Sus parejas son Calientes1, Chalsos y DME3.

---

## 9. Viento (en curso)

Los criterios para revisar el viento de la red y diagnosticar un caso sospechoso están en
[`WIND_REVIEW.md`](WIND_REVIEW.md).

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


### Sarallenque: traslado del shelter en julio de 2025

Sensor: WindSonic en un mástil del Shelter 04 (remolque), a ~4 m. Reporte descriptivo (solo datos
y gráficos: mapa, rosas, series y fotos): `sarallenque_wind/reporte_viento_sarallenque.html`. Diagnóstico con los criterios E y F de
`WIND_REVIEW.md`.

**Verificado en los datos.**

- **Cambio el 2025-07-14 en dirección y velocidad a la vez.** Hasta entonces seguía su ladera,
  que sube hacia 48° (NE): de día el viento venía de ~245° y de noche de ~78°, como sus vecinas.
  Sarallenque_MQG-15-02 (2.2 km) y Altarani (2.7 km) no cambian en esas fechas.
- **Tramos después del cambio:**

  | Tramo | Estado |
  |---|---|
  | 2025-07-14 → 2025-09-14 | inestable: la dirección nocturna deriva de 138° a 293° y el borde inferior de la serie salta de 52° a 151° de semana en semana |
  | 2025-09-15 → 2025-10-05 | estable; empieza con la calibración de mediados de septiembre |
  | 2025-10-06 → ~2025-11-16 | estable, girado ~−50° respecto al anterior: borde inferior, borde superior, día y noche bajan 45–70° a la vez; MQG no se mueve |
  | desde ~2025-11-17 | estable, girado ~+30° respecto al anterior; borde inferior fijo en 111° durante 13 semanas |

- **Giro de 180° (±10°), medido en la noche** (periodos limpios 2025-05-01 → 06-30 y
  2025-11-17 → 2026-01-09). Girando 180° el histograma nocturno, la similitud con el de antes pasa
  de 0.01 a 0.98. Hora a hora, la diferencia entre 22 y 08 h va de 172° a 184°. Las vecinas giran
  de noche entre 0° y −20° entre esos mismos periodos, así que no es la estación.
- **De día, aunque se corrija el giro, no es comparable.** Tras restar 180°, el viento de día viene
  de ~299° contra ~247° antes (las vecinas se mueven ±20°). El sector S–SO–O (165–285°), que traía
  el 39 % de las horas con viento, pasa a 0 %, y el de 300° sube del 0.4 % al 52 %. La velocidad de
  día sube un 30 % respecto a MQG; la de noche apenas cambia.

**Hipótesis sobre las causas**, de más a menos probable:

1. **El shelter se trasladó en julio de 2025 y quedó orientado al revés.** La marca de norte del
   WindSonic va referida al mástil, que va sujeto al shelter, así que giró con él. El usuario
   revisó una foto anterior a julio de 2025 en la que el shelter está orientado casi en sentido
   opuesto. Explica el giro de 180° y que la noche, restándolo, coincida con la de antes.
2. **El punto nuevo está más cubierto: hay un obstáculo al S–SO–O.** El viento de ese sector ya no
   llega; rodea el obstáculo y entra por su borde, en ~290° (el borde inferior fijo de 111° sin
   corregir). Candidatos: el talud cortado que se ve detrás del shelter en la foto f2 (mirando al
   sur) y, más lejos, el tajo, que queda al O y al SO. Esto explica que el día no coincida tras
   corregir el giro. La subida de la velocidad diurna podría ser el viento acelerándose al rodear
   el obstáculo, pero no está comprobado.
3. **Reorientaciones posteriores sin registrar.** Los giros de ~−50° del 6 de octubre y de ~+30°
   hacia el 17 de noviembre de 2025 son movimientos del mástil o del sensor: sujeción floja o
   ajustes en visitas de campo.
4. **Contribuyen poco o nada:** la inclinación del shelter (afecta algo a la velocidad y poco a la
   dirección); el enmallado al este (el drenaje nocturno del NE sigue llegando); un cambio regional
   o estacional (las vecinas no lo muestran). Descartado: un fallo de veleta, porque el WindSonic
   no tiene partes móviles.

**Coordenada.** El GPS de la foto de 2026-08 cae a 11 m de la coordenada de `stations.py` (KMZ).
Con el traslado de julio de 2025, las dos corresponden al punto **nuevo**; la ubicación anterior
no se conoce.

**Tratamiento (hasta 2026-09-24; revisado abajo, tras la visita):**

| Tramo | Dirección de noche | Dirección de día | Velocidad |
|---|---|---|---|
| hasta 2025-07-13 | válida | válida | válida |
| 2025-07-14 → 2025-09-14 | no válida | no válida | no válida |
| 2025-09-15 → ~2025-11-16 | corregible por tramo cuando se mida el ángulo (~200° y ~140° según las estimaciones semanales) | no comparable | no comparable |
| desde ~2025-11-17 | válida restando 180° (confirmar con brújula) | no comparable: sector S–O tapado | no comparable de día (+30 %) |

### Sarallenque: visita del 2026-09-25

**Dato de campo (usuario, 2026-09-28).** El 2026-09-25 se reorientó el WindSonic: debía tener la
marca N hacia el norte y la tenía hacia el sur. Además, el shelter quedó desplazado unos metros al
este (~3 m y ~2 m según campo), más expuesto por la cara sur y más cubierto por la cara este. El
desplazamiento está por debajo de la precisión del GPS: la coordenada de `stations.py` no cambia.

**Verificado en los datos** (base hasta 2026-09-28 15:00; direcciones = mediana vectorial sin
calmas, ver abajo; MQG = Sarallenque_MQG-15-02 en el mismo periodo):

| Tramo | Día Sar / MQG | Noche Sar / MQG | Velocidad Sar/MQG (día / noche) |
|---|---|---|---|
| Antes del traslado (2024-07-14 → 2025-07-14) | 238° / 232° (+7°) | 74° / 95° (−21°) | 0.51 / 0.68 |
| Tras el traslado, crudo (2025-11-17 → 2026-09-25 10:00) | 133° | 263° | — |
| Tras el traslado + 180° | 313° / 239° (**+74°**) | 83° / 87° (−4°) | 0.56 / 0.72 |
| Tras la visita (desde 2026-09-25 20:00; 22 h día, 27 h noche) | 213° / 237° (−24°) | 74° / 45° (+28°) | 0.42 / 0.42 |

- **Hora del cambio.** El 2026-09-25 falta el registro de las 11:00. De 12 a 19 h la dirección
  (~160°) no encaja con ninguna de las dos orientaciones; desde las 20–21 h la noche ya viene del
  ENE. Tramo de transición: 2026-09-25 11:00 → 20:00.
- **Noche: solo el giro de 180°.** Tras la visita vuelve a 74°, igual que antes del traslado; la
  diferencia hora a hora con MQG pasa de −124° (15→25 sep) a −7° (media vectorial ponderada). El
  tramo anterior girado 180° queda a 9° del de antes del traslado y a −4° de MQG.
- **Día: el giro no basta.** Girado 180°, el día del tramo anterior viene del NO (313°), 74° fuera de
  MQG; tras la visita viene del SSO (213°), cerca de MQG. De noche el giro fue ~190° y de día ~75°:
  antes y después de la visita no se relacionan por un giro único.
- **La diferencia con MQG tras la visita no mide todavía un giro residual.** MQG marcó de noche 45°
  esos días (su habitual: 87–95°) y los signos de día y de noche son opuestos, que no es la firma de
  un giro del sensor.
- **La velocidad relativa a MQG bajó**, más de noche (0.68 → 0.42) que de día (0.51 → 0.42). Con
  ~1 día de datos no se da por cambio.
- **Método de la dirección** (usuario: mediana vectorial, para que las calmas no sesguen). En
  Sarallenque la media ponderada por velocidad, la media unitaria y la mediana difieren ≤ 5°, y
  incluir o no las calmas cambia la mediana ≤ 1° (calmas ≤ 5.6 % de las horas). En MQG de noche,
  con el viento repartido entre sectores, la diferencia entre métodos llega a 13–14°.

**Hipótesis revisadas** (sustituyen a las de arriba donde se contradicen):

1. **Orientación: confirmada.** La marca N quedó hacia el sur con el traslado de julio de 2025; de
   ahí el giro de 180° de la noche.
2. **Obstáculo: era local, pegado a la cara sur.** Unos metros de desplazamiento bastaron para que
   el viento de día vuelva a llegar del SSO, así que no era el talud ni el tajo lejanos (hipótesis 2
   de arriba), sino algo contiguo a la cara sur del shelter (el propio shelter o lo que tenía al
   lado; sin identificar). Mientras estuvo, el viento del SO lo rodeaba y llegaba del NO.
3. **Cara este más cubierta: posible efecto en la velocidad nocturna.** El drenaje nocturno llega
   del ENE, por esa cara. Encaja con la bajada de la razón nocturna con MQG a 0.42; sin confirmar.

**Tratamiento (desde 2026-09-28):**

| Tramo | Dirección de noche | Dirección de día |
|---|---|---|
| hasta 2025-07-13 | válida | válida |
| 2025-07-14 → 2025-11-16 | no válida (giros intermedios) | no válida |
| 2025-11-17 → 2026-09-25 10:00 | válida sumando 180° | no válida (cara sur tapada) |
| 2026-09-25 11:00 → 20:00 | transición, fuera | transición, fuera |
| desde 2026-09-25 20:00 | válida (revisión del 2026-11-09, abajo) | **no válida**: la dirección diurna deriva hacia el sur (revisión del 2026-11-09, abajo) |

Material: `sarallenque_wind/rosas_orientacion.py` (rosas 2×2 con botón día/noche: antes del
traslado, tras el traslado, tras el traslado + 180°, tras la visita) y
`sarallenque_wind/esquema_orientacion.py` (esquema en planta de esta interpretación; posiciones y
tamaños supuestos).

`stations.WIND_EXCLUDED` sigue excluyendo Sarallenque desde el 2025-07-14 sin fin (decisión en la revisión del 2026-11-09, abajo).

### Sarallenque: seis semanas después de la visita (revisión del 2026-11-09)

Datos horarios con el QC del visor, 1070 h desde 2026-09-25 20:00 sin huecos (calmas 3.1 %). Franjas
y método de dirección como arriba (mediana vectorial sin calmas; día 10–17 h, noche 22–06 h). La razón
de velocidad es el cociente de medias de Sarallenque y MQG en las mismas horas (no coincide con la
columna de velocidad de la tabla anterior, que usa otra medida; dentro de esta tabla es comparable).

| Tramo | Día Sar / MQG | Noche Sar / MQG | Razón de velocidad (día / noche) |
|---|---|---|---|
| Antes del traslado (2024-07-14 → 2025-07-13) | 238° / 232° (+7°) | 74° / 95° (−21°) | 0.49 / 0.54 |
| Tras la visita, todo (1070 h) | 185° / 236° (**−50°**) | 76° / 73° (+2°) | 0.32 / 0.44 |
| Tras la visita, desde 2026-10-09 | 174° / 236° (**−62°**) | 75° / 91° (−16°) | 0.31 / 0.44 |
| Mismo periodo del año anterior (2024-09-25 → 11-09, control estacional) | 251° / 225° (+26°) | 63° / 109° (−46°) | 0.48 / 0.49 |

Por semana desde la visita, la dirección de día de Sarallenque (MQG entre paréntesis): 214° (232°),
200° (240°), 190° (244°), 160° (231°), 165° (243°), 179° (226°), 166° (233°). De noche se mantiene en
71–81° toda la serie (MQG, más disperso: 36–112°, con 268° una semana).

Distribución de sectores de día (% de horas con ≥ 0.5 m/s; sin viento del N, NE ni E en ninguno de los cuatro casos):

| Caso | SE | S | SO | O |
|---|---|---|---|---|
| Sarallenque antes del traslado | 0 | 14 | 48 | 37 |
| Sarallenque tras la visita | 16 | 61 | 23 | 0 |
| MQG antes del traslado | 1 | 12 | 67 | 17 |
| MQG tras la visita | 0 | 5 | 69 | 24 |

- **La dirección nocturna quedó resuelta**: 71–81° semana tras semana, igual que antes del traslado (74°).
  La diferencia con MQG (−16°) está dentro de lo que tenía antes (−21°) y de la dispersión nocturna de MQG.
- **La dirección diurna no volvió**: viene del S (61 % de las horas) y no del SO–O (85 % antes), y el
  sector O desapareció (37 % → 0 %). No es estacional (control de 2024: 251°) ni de la red (MQG sigue en
  ~236°). La dirección no se estabilizó tras la visita: 214° la primera semana y 160–179° desde la cuarta.
- **La velocidad relativa a MQG bajó más que en la primera lectura**: de día 0.49 → 0.31, de noche
  0.54 → 0.44. De noche cuadra con la cara este más cubierta (§9 arriba); de día no hay explicación probada.
- **Hipótesis sin confirmar**: el obstáculo contiguo a la cara sur no desapareció con el desplazamiento
  de unos metros, sino que cambió de lado respecto al sensor (el sector O quedó vacío y apareció el SE), o
  el mástil o el shelter se siguen moviendo (la deriva semanal sugiere esto último). Requiere visita.

**Decisión.** `WIND_EXCLUDED` se deja como está (Sarallenque excluida desde 2025-07-14 sin fin): reabrir
el tramo posterior a la visita metería en el grupo una dirección diurna a −50° / −62° de MQG. La
herramienta solo excluye por fechas, no por franja, así que la noche válida queda fuera hasta que se
corrija el día.

### Mina_Norte: viento desde el ClimaVUE (revisión del 2026-11-09)

Mina_Norte sigue excluida entera en `WIND_EXCLUDED` (traslados del shelter sin fechar). Desde la
instalación del ClimaVUE (2026-08-28) hay 10 semanas completas de viento; dirección mediana por
semana frente a Charaque, la vecina más cercana (2 km):

| Franja | Mina_Norte | Charaque | Diferencia (rango / mediana) | Razón de velocidad con la mediana de 6 vecinas |
|---|---|---|---|---|
| Día | 243–274° | 249–264° | −6° a +19° / +4° | 0.62–0.78 |
| Noche | 77–145° | 76–117° | −18° a +41° / +13° | 0.82–1.42 |

Minas_Sur y Papujune siguen la misma forma (día 244–293° y 237–254°; noche 83–134° y 49–113°). No
hay escalones semana a semana: no se detecta un traslado o giro posterior al 2026-08-28. El 0.62–0.78
de día es compatible con un anemómetro a 4 m frente a torres a 10 m, no con un fallo. **El tramo
desde 2026-08-28 es utilizable**; el anterior sigue sin fechar. Queda por decidir `WIND_EXCLUDED` →
`[(None, "2026-08-28")]` (no aplicado) y confirmar con campo si el shelter se movió tras esa fecha.

---

## 10. Pendientes

- Viento (§9), 2026-09-24: sale de la vista por grupo. En la vista por variable: rosas día/noche por zona (Mina, Sur, Altiplano; `rose_maps.py`) y, por grupo de viento, serie horaria y ciclo diario de velocidad. Se probaron y retiraron el ciclo de dirección, la constancia diaria y el mapa hora × día: saturaban sin aportar. Los grupos de viento separan además por forma del ciclo de velocidad (`grouping.MAX_DIF_CICLO_VEL`), que saca a Camp_Quellaveco.
- Camp_Quellaveco: el anemómetro se calibró el 2026-09-10 (dato del usuario). Desde ese día aparecen horas en 0.00 exacto (antes 0 %, después 8–50 % de las horas en la mayoría de los días) y la razón día/vecinas baja de ~1.4 a ~1.05. Diagnóstico nocturno en §8 (sensor que no arranca). Preguntar qué se hizo (rodamientos, hélice u offset del programa) y qué modelo de sensor tiene la torre.
- Curar `groups_draft.py` → `groups.py`.
- Regla de QC para escalones de nivel en T y HR (caso Camp_Quellaveco), comparando con vecinas.
- Confirmar con partes de campo los casos de §8 y la coordenada de Campamento Quellaveco.
- Radiación solar: en pausa por decisión del usuario (2026-09-24); se sigue bien sin el visor.
- Lluvia y UV: exploradas (§11); falta decidir figuras y QC antes de llevarlas al visor. Para los descartes de lluvia, esperar el historial de intervenciones.
- Sarallenque (§9, revisión del 2026-11-09): (1) `WIND_EXCLUDED` se deja en `("2025-07-14", None)`: la dirección diurna tras la visita sigue −50° a −62° de MQG; (2) comparación con MQG hecha (noche resuelta, día no; la velocidad relativa bajó a 0.32 de día y 0.44 de noche); (3) pendiente de decidir: añadir en `stations.py` la corrección de +180° para la noche de 2025-11-17 → 2026-09-25 10:00 (queda a −4° de MQG), que hoy no puede aplicarse porque `WIND_EXCLUDED` no distingue franjas; (4) pedir visita: qué tapa o desvía el viento diurno (la dirección derivó de 214° a ~170° en seis semanas) y la ubicación anterior a julio de 2025.
- Mina_Norte (revisión del 2026-11-09): hecha la regeneración de grupos (§5; entra sola) y el recálculo de `z_baro` (§2; se mantiene 3983). Su viento desde 2026-08-28 es estable y coherente con Charaque, Minas_Sur y Papujune (§9): decidir si `WIND_EXCLUDED["Mina_Norte"]` pasa a `[(None, "2026-08-28")]`. Sigue sin confirmar la coordenada (782 m del KMZ) y si el shelter se movió.
- Apacheta: la presión del ClimaVUE se congeló el 2025-12-23 (§8). Pedir en campo qué se tocó ese día y revisar el barómetro o la lectura SDI-12; mientras tanto el QC la descarta y la estación no entra en el ajuste de `z_baro`.
- Camp_Quellaveco (viento, §8): excluida desde 2026-08-10. Pedir en campo la comprobación de la hélice (giro libre y tiempo de parada), del nivel de la base y del conector, y la medición de la orientación con brújula. Reabrir `WIND_EXCLUDED["Camp_Quellaveco"]` cuando se confirme la reparación, con la fecha de esa visita como fin del tramo.

---

## 11. Radiación, UV y lluvia (exploración, 2026-09-24)

Datos 2024-09 → 2026-09, sin QC. Solo estaciones con la variable en `VARIABLES_REPORTE`.

**Radiación solar (`SlrW_Avg`, 10 estaciones).** Parecido = correlación del índice de claridad
horario (cada hora de 9 a 15 h dividida por su percentil 95 en ±15 días). Las 9 de la mina y
Cortadera se parecen entre sí con r = 0.84–0.97. Vizcachas no pasa de 0.49 con ninguna, lo normal
a 58 km y siendo el único piranómetro del altiplano; su nivel está bien (1.00–1.08). Nivel (percentil 95 de mediodía por mes / mediana de la red):

| Estación | Nivel relativo | Nota |
|---|---|---|
| Cortadera | 1.27–1.36 desde 2024-T4 (0.87 antes) | factor de conversión erróneo (dato del usuario, 2026-09-24); lo corrige el usuario |
| Tala_Legal | 1.33–1.42 hasta 2025-T4; 0.91 desde 2026-T2 | mismo síntoma que Cortadera, corregido en 2026 |
| Camp_Quellaveco | 0.84–0.94 en todo el periodo | constante |
| Alto_Quellaveco | 0.84–0.91 en 2025, 0.98–1.01 desde 2026-T2 | recuperado |

**UV (`RadUV_E_Avg`, 9 estaciones).** Mina: r = 0.82–0.91 entre sí. Huachunta–Vizcachas: 0.55.
Ilo no se parece a ninguna (≤ 0.12). Nivel: Vizcachas 1.16–1.54 veces la red y subiendo;
Altarani 1.22–1.27 hasta 2025-T1 y 1.0 después (escalón); Huachunta en 0 desde 2026-T2; Ilo en
0 durante 2024-T3 y T4.

**Lluvia (`Rain_mm_Tot`, 26 estaciones).** Parecido = Jaccard de días con ≥ 1 mm y Spearman de
totales diarios, con las horas > 40 mm descartadas. Resoluciones: 0.1 mm (cubeta) en 12
estaciones, 0.017 mm (ClimaVUE) en 11, 0.034 en Calacaja y mezcla en Calientes1. Asociaciones:

- Quellaveco (Altarani, Alto_Quellaveco, Sarallenque, Sarallenque_MQG, Camp_Quellaveco, Mina_Norte,
  Minas_Sur): J = 0.59–0.82.
- Tala (Tala-1, Papujune, Charaque, Tala_Legal, Planta_Concentradora, Cerro_Salviani): J = 0.64–0.86.
- Sur (Cortadera, Apacheta, Chalsos, Calientes1, DME3_Cortadera, PMC-4_met, Calacaja): J = 0.41–0.74.
- Altiplano (Huachunta, Vizcachas, Titire): J = 0.57–0.66, Spearman 0.36–0.52: lluvia convectiva y
  dispersa.
- Ilo aparte (8 y 49 mm por año hidrológico).

Valores imposibles: horas > 40 mm en Chancado_primario (21, hasta 7 601 mm), Ilo (9, hasta
7 999), Calientes1, Cerro_Salviani, Dique_pie_botadero y Mina_Norte (1 cada una). Por año
hidrológico, sin esas horas: Dique_pie_botadero suma 13 mm en 2024-25 frente a 150–340 de sus
vecinas y 222 en 2025-26; Calientes1 pasa de 194 a 88 mm mientras sus vecinas se mantienen.
Pendiente: cruzar con el historial de intervenciones (volcados de prueba = falsos positivos).

### Intervenciones frente a los datos de lluvia (2026-09-24)

Fuentes del usuario, en `references/`: `intervenciones_meteorologia.csv` (154 visitas,
2026-01-31 → 2026-09-23) y `observaciones_precipitacion.csv` (4 casos). Correspondencia de nombres:
DPB-1 = Dique_pie_botadero, PCHAP_1 = Chancado_primario, Mina_Sur1 = Minas_Sur, PMC-4 = PMC-4_met y
EHA-TIT-1 = Titire (su resolución pasa de 0.017 a 0.1 mm el 2026-02-11, el día en que el parte
instala el Young). PMC-3 no está en la base.

**Pruebas con agua.** 250 ml = 125 volcados = 12.5 mm. De 123 visitas al pluviómetro, 17 dejan
huella en `Rain_mm_Tot` (lluvia en la estación con sus vecinas del grupo < 0.5 mm): de 0.3 a 8.6 mm,
casi siempre en una sola hora entre las 12 y las 13 h. 42 de las 51 pruebas marcadas «si» no dejan
nada: se hacen en modo mantenimiento (tabla de mantenimiento, `Rain_raw` en Camp_Quellaveco desde
2026-07-02). Reincidentes: Planta_Concentradora (6 visitas con huella, también en simples
limpiezas), Mina_Norte, Huachunta y Sarallenque. Huellas con el pluviómetro «no_consta» en el
parte: Mina_Norte 2026-02-03 (2.2 mm) y Camp_Quellaveco 2026-02-28 (2.1 mm). Huachunta 2026-06-18:
12.9 mm en la hora de las 12, justo una prueba de 250 ml, un día antes de la visita del parte
(2026-06-19): fecha del parte probablemente desplazada, como en Cerro_Salviani (2026-09-13/14).

**Lluvia aislada sin visita a ±1 día** (≥ 1 mm con las vecinas < 0.3): 12 días. En la época húmeda
pueden ser celdas convectivas reales (Titire 4, Vizcachas 2, entre ene y abr). Más sospechosos:
Sarallenque_MQG-15-02 el 2026-04-06 (4.62 mm en una hora) y el 2026-05-30 (2.82 mm a las 00 h, en
época seca).

**Observaciones del usuario, contrastadas:**
- Ilo: 3 062 y 41.3 mm el 10/08 y 3 873–7 999 mm de 13 a 17 h el 11/08, como dice la nota. Además,
  del 12 al 18/08 registra 31 mm en 62 horas de goteo casi continuo, frente a 16.9 mm en los 11
  meses anteriores; el 17/08 llueve de 06 a 10 h, antes que en la sierra (15 h). Hipótesis:
  drenaje del embudo obstruido hasta la limpieza del 19/08. Candidato a ampliar el descarte al
  periodo 2026-08-10 → 2026-08-19.
- Mina_Norte: 279.5 mm a las 16 h del 23/08 (la nota dice > 400: cantidad aproximada) y goteo
  hasta el 25/08, con 12.3 y 12.4 mm a las 07 y 08 h. Dentro del descarte 23/08 → 27/08.
- Evento del 17–18/08: real en toda la red (4–14 mm en la mayoría). Se apartan Dique_pie_botadero
  (29.3 mm: 1.8 veces Tala-1, a 0.5 km, en las mismas horas, más 7.9 mm de 22 a 23 h que Tala-1
  no tiene; agosto: 29.9 mm frente a 7–15 de sus vecinas) y Calacaja (38.3 mm, con el máximo a
  las 13–14 h, antes que el resto).
- Dique_pie_botadero, prueba del 16/08: la hora de las 12 está en NaN en `Rain_mm_Tot`; la prueba
  quedó fuera de la serie, coherente con la nota.

**Lluvia duplicada en ClimaVUE (revisado 2026-09-24, copia de la base del 2026-09-22).** Un ClimaVUE
suma de 0.017 en 0.017 mm, así que en una serie sana alrededor de la mitad de las horas con lluvia
son múltiplos impares de 0.017: 51–70 % en Chalsos, DME3_Cortadera, Sarallenque_MQG-15-02,
Cerro_Salviani, Titire, Charaque y Apacheta. Si cada incremento vale dos volcados, esa proporción
cae a cero:

| Estación | % de horas en múltiplo impar de 0.017 | Tramo |
|---|---|---|
| Calacaja | 1.9 (0 en casi todos los trimestres) | desde su primer dato (2022-12) hasta hoy |
| Ilo | 0–8 | todo el periodo con ClimaVUE (2022-T4 → 2024-T4); desde 2025-T3, pluviómetro de 0.1 mm |
| Planta_Concentradora | 0–11 | todo el periodo con ClimaVUE (2022-T4 → 2026-T1); desde 2026-02, Young de 0.1 mm |
| Dique_pie_botadero | 50–64 hasta 2025-T2; 0–10 desde 2025-T4 | nuevo desde la segunda mitad de 2025 |

En 2026 algunas series vienen redondeadas a dos decimales y el redondeo ensucia el test (Dique
2026-T3 da 31 %): allí no se interpreta.

Hipótesis: cada incremento registrado vale dos volcados del ClimaVUE (multiplicador del programa o
lectura doble del acumulado del sensor), y la lluvia de esos tramos sería la mitad de la
registrada. Encaja con lo observado en Dique: de 13 mm en 2024-25 a 222 mm en 2025-26, y en agosto
de 2026 el doble que sus vecinas. En Calacaja los totales no lo deciden: en 61 días de lluvia común
suma 229 mm frente a 201–276 del grupo Sur (razón 0.98), pero está 600 m por debajo de la siguiente
(2 332 m frente a 2 919–3 750) y su mediana horaria con lluvia es 0.17 mm frente a 0.03 en los
ClimaVUE vecinos. Lo que cierra la duda: comparar el programa CRBasic de Calacaja con el de un
ClimaVUE sano (DME3_Cortadera) y una prueba con volumen conocido cuyo resultado quede en la serie.

