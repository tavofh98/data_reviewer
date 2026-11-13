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
| Mina_Norte | GPS 326497 E, 8110200 N, 4004–4015 m (elipsoidal) | altitud **aceptada**: menos N ≈ 40 da 3964–3975, igual que SRTM (3969 en ese punto, 3972 en el KMZ) y 8–19 m bajo `z_baro` = 3983. Coordenada **confirmada** (2026-11-12): el dato de campo 326492–326500 E, 8110203 N coincide con el GPS en 4–6 m; el error estaba en el KMZ (782 m). `stations.py` actualizado a 326496, 8110203, a 53–59 m de Oeste 1 |

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
  del cálculo, los tramos de `stations.WIND_EXCLUDED` (Sarallenque desde 2025-07-14, Chalsos
  completa, Mina_Norte hasta 2025-11-14, el tramo pegado de Huachunta). La estación con parecido medio < 0.60 al
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

**Mina_Norte entra al agrupamiento de viento** (2026-11-12, 2025-11-13 → 2026-11-13, tope 6). Con la
dirección corregida (§6, §9) y `WIND_EXCLUDED["Mina_Norte"]` reducido a `(None, "2025-11-14")` (tramo A
y anteriores, en otro sitio), el viento pasa de 5 a 6 grupos. El antiguo grupo de Charaque (cos 0.96)
se parte en dos, ambos con cos medio 0.97:
- Charaque, Cortadera, Papujune, MQG-15-02 (dif. de ciclo de velocidad máx 0.08);
- Alto_Tala, Mina_Norte, Tala-1 (máx 0.14).

Los demás grupos de viento, T, HR y combinado no cambian (comparado con el curado del 2026-11-09).
Se probó un tope de 7 y se descartó: sin partir, el altiplano (Huachunta, Titire, Vizcachas) queda
dentro de una rama mayor y los umbrales lo dejan sin grupo. Además, Planta_Concentradora pasa a un
grupo de 6 con un par en 0.58. Pasa con y sin Mina_Norte.

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
- **Origen de los datos (2026-11-12):** el visor lee la vista `met_corrected` de
  `corrections/corrections.db`, no `meteorologia` directamente. La base cruda no se toca: la ingesta la
  reconstruye desde los `.dat` y el servidor es su único escritor. La capa de correcciones tiene tres
  piezas:
  - `corrections/registry.py`: una intervención por decisión (estación, variable, intervalo
    `(start, end]` en final de hora, tipo, parámetro, motivo y referencia a este documento);
  - `met_adjustments`: solo las celdas modificadas, con `raw_value`, `corrected_value`, `method`, `flag`
    y `correction_id`;
  - `met_corrected`: las columnas de `meteorologia` con las celdas ajustadas sustituidas, más
    `adjustment_tags`.

  `uv run python -m corrections.build_corrections` la regenera desde cero. Hay que correrlo si cambia el
  registro o si entran datos nuevos de un periodo corregido. Comprobado al construirla: la vista tiene las
  mismas filas que la tabla cruda (1 093 738), 0 celdas distintas fuera de los ajustes, y todos los
  `raw_value` coinciden con el crudo.

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
| Chalsos | dirección | ~270° de noche y 120–160° de día, al revés que Calientes1/Cortadera/Tala_Legal (~100° / ~270°) | **No es fallo: es el régimen del sitio** (revisión del 2026-11-12, §9). En los episodios de viento fuerte coincide con sus vecinas (+2° de día, +7° de noche con Cortadera), y está en una divisoria, en la cabecera de una quebrada que drena al ESE y luego al S (corregido el 2026-11-13, §9). Su programa es idéntico al de MQG-15-02 (`PMC3-Tripode_01 v4.2`), con la dirección tal cual la da el ClimaVUE. Se descartó la hipótesis de espejo, registrada antes ese mismo día |
| Huachunta | dirección | veleta pegada en ~152° (mar–may 2026); constancia direccional = 1.00 | fallo mecánico |
| Sarallenque | viento | desde 2025-07-14 dirección y velocidad cambian a la vez; de noche viene de ~250° en vez de ~78°; sector S–SO–O vacío. Reorientado el 2026-09-25 (marca N al norte; antes al sur) y shelter desplazado unos metros al E | confirmado en campo: sensor orientado al sur (180°). Revisado el 2026-11-12 (§9): de 2025-09-15 a 2026-09-25 la dirección es un **espejo** (real = K − lectura), no un giro; con él cuadran día y noche sin necesidad de un obstáculo en la cara sur |
| Apacheta | presión | el barómetro del ClimaVUE (integrado) dejó de actualizarse el **2025-12-23 por la tarde** (en la base horaria hay 11 cambios en las 20 h de ese día y ninguno al siguiente; el `.dat` de 5 min tiene un hueco del 2025-11-01 al 12-23, así que la hora exacta, ~17:00, se apoya en solo 1.5 h de 5 min). Antes cambiaba en el 31–35 % de los registros de 5 min a cualquier temperatura (≈ 22 cambios al día en los datos horarios, como Papujune); desde 2026-01-20 cambia en ≤ 3 % (0 % con T ≤ 5 °C; casi todos los cambios caen entre 7 y 17 h) y, en horario, 0.3–3.1 cambios al día según el mes (ene–abr 1.9–3.1; mayo–nov 0.3–1.3). Los valores retenidos siguen centrados: Apacheta − Papujune ≈ +2 hPa antes y después, pero el desvío pasa de 0.15 a 0.8–1.4 hPa (la presión real varía ~1–2 hPa al día). T, HR y batería del mismo logger siguen normales. Del 2026-01-01 al 01-05 hubo cambios de nuevo (12, 11, 7, 5 al día) justo antes de un hueco de datos (01-06 → 01-11). Persistió tras la limpieza y reinicio físico del 2026-05-20 y el mantenimiento del ClimaVUE del 2026-06-03 (`intervenciones_meteorologia.csv`). Antes de 2021-05 son registros en cero (§4) | fallo del barómetro del ClimaVUE (o de su lectura por SDI-12): mide, pero devuelve casi siempre el mismo valor. El QC lo descarta por `STUCK` (≈ 672 h cada 30 días); por eso Apacheta queda fuera de `calibrate_baro.py` (< 30 días válidos). Coincide en fecha con el cambio de nivel de su HR (ene-2026, fila siguiente) y con el mes del pluviómetro Young (dic-2025, `stations.py`); qué se tocó el 2025-12-23 está por confirmar en campo |
| Camp_Quellaveco | viento | desde el 2022-10-06 (06–12 h) la velocidad nocturna cae a 0.3–0.6 veces la de sus vecinas (antes 0.8–1.0), con 25–70 % de horas en calma, y la dirección nocturna deja de seguirlas (de ~80° a 120–260°); de día sopla 1.3–2 veces más que ellas. Ese mismo día, la presión reducida baja 4.9 mbar (+7.0 → +2.2) | reubicación de la estación o de la torre a un punto más alto (~60 m) y resguardado de noche (criterios B y C de WIND_REVIEW, más `BARO_DEV`). También coinciden viento y presión el 2020-10-27; el escalón de −2.5 mbar del 2024-03-24 no tiene cambio de viento esa semana |
| Camp_Quellaveco | viento nocturno | tras la calibración del 2026-09-10, el 37 % de las horas de noche en 0.00 exacto (antes 0 %), en noches enteras (14→15, 16→17, 22→23 sep) mientras Chancado (0.7 km) sopla 1.3–2.3 m/s del NE; la dirección queda congelada toda la noche con décimas de grado (94.6–95.1°, 66.2°, 87.4°). Antes de la calibración, la dirección nocturna cambiaba 43° de una hora a otra (Chancado: 20°) y con < 0.5 m/s apuntaba a 205–245°, contra el drenaje NE–E de las vecinas; parecido con Chancado: 36° de diferencia mediana en ago–sep 2025, 54° antes y 49° después. De día, sin cambio (oeste en el 98–100 % de las horas; +6° desde el 14-sep) | después: sensor que no arranca (rozamiento, umbral o programa); antes: ruido de un sensor en su umbral, ya peor que en 2025. De noche solo valen las horas con ≥ 0.5 m/s. Criterio G de WIND_REVIEW |
| Camp_Quellaveco | viento (veleta y hélice, Young) | Con 5 min, frente a Altarani y Charaque y a las mismas fechas de 2025. Deterioro desde mediados de agosto de 2026: la desviación de la dirección dentro del registro (SD1) frente a Altarani baja de 1.3–1.5 (jun–jul) a 1.14 (semana del 08-10), y los ceros exactos con vecinas a 1–5 m/s suben de 3–6 % a 12 % (08-24), 20 % (09-07) y 35 % (09-14). Tras el cambio de base del 09-10: SD1 de 0.6–0.8, cambio de dirección entre registros consecutivos 0.3–1.0 veces el de Altarani (2025: 1.1–4.0) y dirección repetida (< 0.5°) en el 12–17 % de los registros (2–3 %). De noche, con CQ = 0.00 y Charaque a 2.7 m/s, la dirección queda congelada (desviación circular de 0–0.6° durante noches enteras) en ~89°, a < 45° de Charaque en el 92 % de los registros: cabezal alineado e inmóvil y hélice parada. La regresión contra las vecinas da intercepto de −1.9 m/s frente a −1.5 en 2025, con la misma pendiente (efecto de umbral, no de escala). 2026-09-17 (primer abatimiento): sin cambio. 2026-10-20 (segundo): con vecinas a 3–5 m/s los ceros bajan de 20 % a 5 %, pero siguen en 24–30 % con 1–3 m/s y SD1 en 0.55–0.75 (solo 14 días de datos); la dirección diurna gira de forma rígida −43° a −55° en todos los bloques de 2 h (Charaque −1° a −4°; mismo recorte de 2025 −1° a −3°) | Dato de campo (usuario): en la calibración del 09-10 la base estaba rajada y se cambió por una de otro modelo, con más resistencia al giro; el 2.º abatimiento aflojó el encaje y varió la orientación. La fricción explica el cabezal inmóvil; la hélice parada con el cabezal alineado no queda explicada del todo (por comprobar en campo: giro libre de la hélice, nivel de la base, conector). Cuál orientación es la correcta tras el 10-20 está sin decidir (medirla con brújula). Excluido en `WIND_EXCLUDED` desde 2026-08-10 hasta confirmar la reparación. No cambia los grupos de viento (ya queda aparte por la forma de su ciclo de velocidad) |
| Papujune | T | 132 h con 0.0 exacto (abr-2026) | sensor caído (descartado por `STUCK`) |
| Charaque | HR | 752 h en 101.2 % (ene–abr 2025), aceptadas por el rango | calibración |
| Apacheta / Minas_Sur | HR | cambio de nivel en ene-2026 / may-2026 | cambio de sensor (Apacheta: mismo mes que su pluviómetro) |
| Calientes1 | T, HR | jul-2025: 64 % de valores redondeados a un decimal (normal ~10 %) | cambio de programa |
| Calientes1 | dirección | **Particularidad, no fallo** (revisión del 2026-11-12, decisión del usuario). De día viene del O (~272–290° desde 2025), donde las vecinas del sur vienen del SO; de noche coincide con ellas (−16° a +18° con Apacheta, DME3 y Tala_Legal en los periodos estables). Tala_Legal (6 km) tiene el mismo régimen (día 291–295°, noche 104–124°). La dirección diurna de la zona va del S al ONO según el valle (DME3 ~185°, Apacheta ~225°, Cerro_Salviani ~235°, Cortadera ~255°, Calientes1 ~280°, Tala_Legal ~292°). En la red sale como la más limpia: 100 % de transiciones en el mismo sentido que sus vecinas y ajuste como giro de 0.94. Aparte, saltos de orientación de 20–30° con día y noche moviéndose juntos frente a Cortadera, Apacheta y DME3: −20° en 2021-T4 → 2022-T1, **+25–30° de 2023-T4 a 2024-T4**, −20° en 2025-T1 y una deriva lenta de −20° de 2025-T3 a 2026-T3 (también frente a Tala_Legal) | el O diurno es del sitio: el valle encauza el flujo diurno. Los saltos, giros pequeños del sensor o de su sujeción; preguntar por mantenimiento hacia 2023-10 y 2025-01. No afectan a su grupo de viento (G1, cos 0.92); solo importan para un uso cuantitativo de la dirección |
| Cortadera | dirección | desde 2026-09-13 13:00 (faltan 11 y 12 h): giro rígido de −73° ± 4°, igual de día y de noche (−74° / −71° frente a Calientes1; seis vecinas coinciden) | visita de campo; se restituye sumando +73°. Fuente: `wind_vector/consensus/audit/r2` |
| Alto_Quellaveco | dirección | desde 2026-09-15 12:00 (falta 11 h): giro rígido de −88° ± 5° (−85° / −94° frente a Minas_Sur, día / noche) | visita de campo; se restituye sumando +88° |
| Alto_Tala | dirección | desde 2026-09-24 (transición el 24 y el 25; estable desde el 26): giro rígido de unos −65°, igual de día y de noche (Tala-1 −64° / −65°, Tala_Legal −71° / −58°, Calientes1 −77° / −72°; mediana diaria de la diferencia, ambas ≥ 1 m/s). Detectado el 2026-11-12 | calibración en campo (hipótesis del usuario). Cuál orientación es la buena está sin decidir: frente a Tala-1 la nueva queda más cerca (antes +38° / +64°, después −26° / −2°), frente a Tala_Legal y Calientes1 la anterior (+6° / +19° y +27° / +25°) |
| Cortadera | dirección nocturna | desde sep-2022 las noches en 90–135° pasan de 0–2 % a 46–71 % (53–65 % desde 2023); antes el 84 % caía en 45–90°. Fechado el 2026-11-13 con D1 por quincenas: el cambio es en la **segunda quincena de 2022-09** y afecta también al día (resultante diurna 224–236° → 249–263°; nocturna 57–75° → 84–102°), estable desde entonces. Coincide con el fin de los escalones de presión de Cortadera (§4). En la misma quincena Papujune gira en sentido contrario (día 235–259° en ene–ago 2022 → 207–239° desde la segunda quincena de sep) y el 2022-10-06 se reubica Camp_Quellaveco | cambio de sitio (la presión lo apoya) o de orientación; tres estaciones en tres semanas sugieren una campaña de campo. Pedir partes de sep–oct 2022 de Cortadera y Papujune |
| Altarani | dirección nocturna | ene–mar 2025: noches en 90–180° al 52 %, 0 % y 17 % (resto de meses 92–98 %); en feb-2025 la noche viene de ~288° | fallo o giro temporal no documentado; fuera del periodo del consenso |
| Planta_Concentradora | dirección | desde 2024-04-06: de día +73° respecto a Papujune y de noche −9°; coseno del ciclo diario con las vecinas −0.15 a 0.44 (antes 0.77–0.95) | cambio de orientación o de sitio; no es un giro único (signos opuestos día/noche). Cifras de la revisión externa, sin verificar por separado. Cribado del 2026-11-12 (2025-11 → 2026-11): transiciones del ciclo diario al revés que sus cinco vecinas y mejor ajuste como espejo con 4 de 5. Esa firma no basta (ver Chalsos, §9): con viento fuerte de Papujune (5–6 m/s, 56–80 h) se alinea con ella en el 76–80 % de las horas, lo que apunta a un régimen de sitio (¿traslado en 2024-04?) más que a un espejo. Sin cerrar |
| Camp_Quellaveco | dirección nocturna | en horas con > 1 m/s la noche no tiene dirección dominante desde el 2022-10-06 (constancia 0.05–0.20, antes 0.84–0.92), repartida en los cuatro cuadrantes | sitio, no anemómetro: el punto nuevo es turbulento de noche (`audit/r2`); complementa la fila de la reubicación |
| Charaque / Sarallenque_MQG-15-02 | viento | registros congelados (dirección y velocidad fijas): Charaque 2026-01-14 14:00 → 01-15 12:00 y 2026-01-28 14:00 → 01-29 07:00; MQG 2026-02-16 14:00 → 02-17 09:00 | logger o registro; sin verificar por separado |

**Giros de torres en septiembre de 2026.** Cuatro torres con veleta cambian de orientación en dos
semanas: Camp_Quellaveco (2026-09-10, base cambiada; giro diurno de −43° a −55° tras el abatimiento
del 10-20), Cortadera (09-13, −73°), Alto_Quellaveco (09-15, −88°) y Alto_Tala (09-24, unos −65°). En las
tres últimas el giro es rígido, igual de día y de noche, y del mismo signo en todas. Apunta a una campaña
de calibración con un error de alineación repetido (referencia o declinación mal aplicada); hipótesis del
usuario: calibraciones. Por confirmar con los partes. Cortadera, Alto_Quellaveco y Alto_Tala están hoy
dentro de los grupos de viento sin exclusión ni corrección.

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

### Sarallenque: espejo, no giro (revisión del 2026-11-12)

Contexto espacial como con Mina_Norte. Dirección horaria = media de vectores unitarios de los
registros de 5 min (`references/AAQ_Est_Sarallenque_Table3.dat`, 2021-07 → hoy). Vecinas a 2.0–3.8
km: MQG-15-02, Minas_Sur, Mina_Norte (corregida), Oeste 1, Chancado_primario, Alto_Quellaveco,
Altarani y Charaque. Tramos como arriba: S0 antes del traslado (2024-07-14 → 2025-07-14), S2
(2025-09-15 → 10-06), S3 (10-06 → 11-16), S4 (2025-11-17 → 2026-09-25 10:00) y S5 tras la visita.

**Un giro no cuadra día y noche a la vez.** Frente a las mismas vecinas, S4 pide de día unos +120° y de
noche unos −120° (≡ +240°). Un giro desplaza todas las direcciones por igual; restar en unas y sumar en
otras, con media de ~180°, es la firma de un **espejo**: real = K − lectura. La lectura del 2026-09
(«giro de 180° de noche, día no comparable») era esa misma firma.

**Pruebas:**
1. **El sentido del recorrido se invierte, en el mismo sitio.** Ciclo diario medio de la mañana (6 → 9 h):
   S0 77° → 95° → 151° → 225° y S5 86° → 122° → 203° → 210° rolan en sentido horario por el sur, como
   MQG. S4 bruto rola al revés: 262° → 262° → 214° → 143°. En la tarde, igual. Un giro conserva el
   sentido; solo un espejo lo invierte. S4 y S5 son el mismo punto (shelter desplazado ~3 m).
2. **Contraste por sectores de 30° de cada vecina, S4 frente a S5:**

   | | Día | Noche | Día − noche |
   |---|---|---|---|
   | Giro necesario θ (7 vecinas) | +44° a +52° | +113° a +174° | ~120° |
   | Constante del espejo K | 315–323° | 341–353° | ~28° |

3. **Constancia de la relación hora a hora:** el espejo ajusta mejor que el giro en S2, S3 y S4 (con
   Charaque, 0.91 / 0.82 / 0.88 frente a 0.87 / 0.75 / 0.75). En S0 gana el giro de 0°.
4. **Con real = 341° − lectura, el ciclo de S4 reproduce el de S5:**

   | Hora | 0 | 7 | 8 | 9 | 12 | 18 | 19 | 20 | 22 |
   |---|---|---|---|---|---|---|---|---|---|
   | S4 corregido | 82° | 79° | 127° | 198° | 210° | 181° | 136° | 109° | 89° |
   | S5 (bien orientado) | 79° | 122° | 203° | 210° | 184° | 196° | 164° | 88° | 78° |
   | MQG en S4 | 92° | 107° | 206° | 232° | 240° | 235° | 185° | 143° | 104° |

   Misma forma (noche del ENE, salto por el SE–S, regreso por el S–SE). La transición de la mañana va
   una hora más tarde en S4 y la meseta diurna queda ~25° más al oeste que en S5.
5. **La prueba del sentido de giro hora a hora no discrimina:** ni las vecinas entre sí correlacionan
   sus cambios de dirección a 30 min (MQG–Charaque +0.01 a +0.07). Se descartó.
6. **Viento fuerte (MQG ≥ 7 m/s, Charaque ≥ 4).** En S5, ya bien orientada, los westerlies fuertes
   (vecinas a 250–290°) se leen del S (170–185°): el sitio nuevo desvía el viento del O hacia el S. En S4,
   esos episodios corregidos con el espejo dan 154–210°, como S5; con un giro de 180° darían 311–7°.
   El espejo resiste la prueba que tumbó la hipótesis en Chalsos, porque aquí la referencia es el mismo
   sitio.

**Límite del método.** La inversión del sentido de las transiciones prueba un espejo solo si se compara
el mismo sitio (S4 frente a S5). Entre sitios distintos, una estación en la vertiente opuesta tiene el
régimen al revés y también recorre la transición al revés (caso de Chalsos, abajo).

**K se fija con la noche.** El drenaje nocturno llega del ENE en el sitio viejo y en el nuevo: frente a
S5, K = 341–353°; frente a S0, 335–343°. El día no sirve de referencia: S0 es otro sitio (K ≈ 12°) y el
día de S5 deriva (214° → 165°; K ≈ 316°), a ambos lados del valor nocturno. K semanal de noche en S4:
321–357°, sin saltos. K por tramo: S2 ≈ 357°, S3 ≈ 294°, S4 ≈ 341° (± 10°). S1 (2025-07-14 → 09-15) no
es corregible: dos semanas de transición y, del 18/08 al 14/09, una noche con K ≈ 0° y un día que no
encaja.

**Lo que cambia de lo anotado antes:**
- El día «no comparable» de S4 era el espejo. Corregido viene de ~207°, a −31° de MQG, entre el sitio
  viejo (+7°) y S5 (−56°). La hipótesis de un obstáculo pegado a la cara sur pierde su principal apoyo.
- Las «reorientaciones» de −50° (S3) y +30° (S4) son cambios de K: el mástil se movió entre tramos.
- La diferencia día−noche de ~28° frente a S5 no se resuelve. Puede ser el sitio en S5 (día que deriva).

**Mecanismo, sin confirmar.** «Marca N hacia el sur» da por sí solo un giro de 180°, no un espejo. La
foto del 2026-08-18 (en S4) muestra el WindSonic derecho en lo alto de su mástil, así que no estaba
invertido. Queda el cálculo de la dirección: con la componente N–S de signo cambiado la salida es
180° − x, y con la marca N en φ resulta K = φ + 180°. K = 341° da φ ≈ 161° (SSE), coherente con lo visto
en campo. Pero antes del traslado no había espejo y tras la visita tampoco; si en la visita solo se
hubiera girado el sensor, el espejo seguiría (K ≈ 180°). Algo más que la orientación cambió en el
traslado y se deshizo en la visita (programa, configuración o la unidad). Preguntar a campo qué se hizo
el 25/09 y pedir el programa del CR1000X anterior a la visita.

**Propuesta, sin aplicar:** espejo en `corrections.db` (tipo nuevo `mirror`, por registro de 5 min y
media vectorial) con K = 357° (S2), 294° (S3) y 341° (S4); fuera S1, la semana 2025-11-10 → 11-17 y la
visita. `WIND_EXCLUDED` sigue sin cambios.

### Mina_Norte: viento desde el ClimaVUE (revisión del 2026-11-09)

Mina_Norte estaba excluida entera en `WIND_EXCLUDED` (traslados del shelter sin fechar). Desde la
instalación del ClimaVUE (2026-08-28) hay 10 semanas completas de viento; dirección mediana por
semana frente a Charaque, la vecina más cercana (2 km):

| Franja | Mina_Norte | Charaque | Diferencia (rango / mediana) | Razón de velocidad con la mediana de 6 vecinas |
|---|---|---|---|---|
| Día | 243–274° | 249–264° | −6° a +19° / +4° | 0.62–0.78 |
| Noche | 77–145° | 76–117° | −18° a +41° / +13° | 0.82–1.42 |

Minas_Sur y Papujune siguen la misma forma (día 244–293° y 237–254°; noche 83–134° y 49–113°). No
hay escalones semana a semana: no se detecta un traslado o giro posterior al 2026-08-28. El 0.62–0.78
de día es compatible con un anemómetro a 4 m frente a torres a 10 m, no con un fallo. **El tramo
desde 2026-08-28 es utilizable**; el anterior quedó fechado el 2026-11-12 con Oeste 1 (ver abajo). Decidido el 2026-11-12:
`WIND_EXCLUDED` → `[(None, "2025-11-14")]`, con el tramo B corregido (§6, §9). Falta confirmar con campo si el shelter se movió tras el 2026-08-28.

### Mina_Norte frente a Oeste 1: tramos y orientación (2026-11-12, preliminar)

**Datos.** Oeste 1 (Oizom Polludrone en CR800, `references/AAQ_Est_OESTE_1_Table1_Oizom.dat`, horario,
2024-04 → hoy) está a 53–59 m de la coordenada corregida de Mina_Norte (§2). Solo su viento es
utilizable: T y HR son constantes de relleno (20 °C, 40 %) y BP = 0. Su velocidad nunca baja de
0.18 m/s y su dirección no sale de 15–326°: sin calmas y con el sector N deformado. En 2025 la base
guarda T, HR y BP de Mina_Norte como 0: ese año solo hay viento y lluvia. Mapa de rosas por tramo
con Charaque y MQG-15-02: `mina_norte_wind/mina_norte_roses.html` (`build_roses.py`; el mapa B+ lee la
serie corregida de `met_corrected`).

**Tramos de Mina_Norte** (día 10–17 h; horas con ambas ≥ 1 m/s):

| Tramo | Periodo | Sitio y sensor | Dirección − Oeste 1 (mediana / IQR) | Velocidad / Oeste 1 | Velocidad / Charaque |
|---|---|---|---|---|---|
| A | 2025-01-01 → 2025-11-14 | punto del KMZ (327257, 8110014), WindSonic; sitio más expuesto (dato del usuario) | +6° / 37° | 1.42 | 0.92 |
| B | 2025-11-26 → 2026-08-26 | junto a Oeste 1, WindSonic | **−51° / 16°** | 0.86 | 0.53 |
| C | 2026-08-28 → hoy | junto a Oeste 1, ClimaVUE | −1° / 15° | 1.12 | 0.61 |

La transición A → B es en dos pasos: dirección el 16/11/2025 (hueco de registro el 15/11, 11–16 h) y
velocidad hacia el 25/11 (hueco el 25/11, 12–13 h). Encaja con el daño de paneles por rocas de
noviembre de 2025 y un traslado posterior (dato del usuario; sin parte de campo: el registro de
intervenciones empieza en 2026-02). En 2024 hubo otro tramo girado (2024-10-13 → 2024-12-21, −90° a
−140°), sin analizar.

**Quién está girada.** Diferencia de dirección de día por pares en A / B / C: los tres pares con Mina_Norte
saltan unos −50° de A a B (MN−O1 −56°, MN−Charaque −50°, MN−MQG −48°) y vuelven en C; los tres pares sin
ella cambian ≤ 7° (O1−Charaque −10°/−15°/+5°, O1−MQG +7°/+10°/+20°, Charaque−MQG +16°/+23°/+17°). Un giro
por estación ajustado por mínimos cuadrados cuadra todos los pares con residuo de 2–3.5°. **La girada es
Mina_Norte.** Las velocidades lo confirman: O1/Charaque se mantiene en 0.63–0.64 en A y B.

**Lectura meteorológica.**
- De día manda la capa límite convectiva (mezcla profunda, viento del valle y del oeste): coherente
  a escala de kilómetros, así que es la franja que sirve para la orientación. Entre dos sensores a
  55 m solo cabe un desfase instrumental.
- El desfase es de error de orientación, no de flujo desviado por un obstáculo:
  - es casi igual en los sectores con viento (180–315°: −48° a −55°);
  - es estable mes a mes (−44° a −57°), aunque Oeste 1−Charaque cambia de −23° (nov–abr) a ~0° (may–ago)
    con el cambio de régimen estacional;
  - un obstáculo daría un desvío que depende del sector.
- Depende algo de la velocidad (−43° con Oeste 1 a 1–2 m/s, −51° a 2–3, −53° a 3–4, −57° a 4–6). Con
  viento flojo pesan más las circulaciones locales y la estela del shelter. La estimación robusta es la de
  las horas bien ventiladas.
- 51–53° no es un error típico de cableado (90°, 180°) ni la declinación magnética (unos −5°): es la marca N
  del WindSonic mal alineada al reinstalarlo, coherente con un montaje tras el daño.
- De noche manda el drenaje katabático: capa somera, de metros a decenas de metros, que sigue el
  microrrelieve. Un shelter y paneles de 2–3 m junto a un sensor a 4 m quedan dentro de esa capa. La
  velocidad nocturna de B correlaciona bien con la de Oeste 1 mes a mes (r 0.77–0.98), salvo en febrero
  de 2026 (−0.06). Ese mes daba el r = 0.07 del tramo entero, así que no hay estela general. La gran dispersión de la dirección nocturna (IQR 123°), en cambio, era sobre todo
  un artefacto: el 0/360 del sensor girado cae en el NE real, y la media aritmética mezclaba registros a
  ambos lados. Con la reconstrucción vectorial baja a 36° (ver abajo).
- La velocidad de día en B es un 13 % menor que en C respecto a Charaque (0.53 frente a 0.61; C es más
  corto y estacional). Es compatible con una obstrucción parcial. No es corregible sin conocer la causa.

**Corrección del tramo B: +53° a todas las horas, aplicada (2026-11-12).** El giro es del sensor y no
depende de la hora del día. El valor sale del contraste por sectores B − C contra Oeste 1 (−53.6°, ver
abajo), que sustituye a los +51° de la primera estimación; la incertidumbre es de ±5°. La calidad
diferente de la noche se marca, no se resuelve dejando la noche sin girar. Sin datos de campo sobre la
orientación, no hay forma de confirmarla mejor.

**Aplicación en `corrections.db`** (§6; intervenciones de `corrections/registry.py`):

| Intervención | Horas `(start, end]` | Qué hace | Horas |
|---|---|---|---|
| `MN-2025-11-transition` | 2025-11-14 → 2025-11-26 | dirección vacía: traslado, giro en dos pasos | 280 |
| `MN-B-rotation` | 2025-11-26 → 2026-08-26 | +53°: 5 min + vector desde 2026-01-11; antes y en huecos, media horaria girada | 3865 + 1463 `north_risk` (5 min); 1126 + 4 `north_risk` (horaria) |
| `MN-2026-08-sensor-swap` | 2026-08-26 → 2026-08-28 | dirección vacía: cable cortado y WindSonic retirado | 32 |

- **5 min + vector:** cada registro se gira y la hora es la dirección media de vectores unitarios (Θ1)
  de los registros con velocidad > 0, con ≥ 9 de 12 registros por hora. Los 5 min reproducen la base
  horaria (diferencia mediana 0.02°, hora etiquetada al final del intervalo).
- **Media horaria girada** (antes de 2026-01-11 y huecos de los 5 min): de noche conserva el artefacto de
  la media aritmética.
- **Marca `north_risk`:** algún registro de la hora, en el marco del sensor sin girar, a menos de 30° de
  0/360. Ahí la media aritmética del logger pudo mezclar los dos lados del corte (350° y 10° dan 180°), y
  girar no lo arregla. Es una detección parcial y amplia: marca el 43 % de las horas nocturnas, muchas
  buenas, y no ve una mezcla que cae lejos del norte del sensor (cerca de 180° del sensor, unos 233°
  reales). El clasificador de mezclas de `wind_vector/north_mixture.py` las separaría mejor.
- En las ventanas excluidas la velocidad se conserva: es verosímil y el problema es solo de orientación.

Diferencia con Oeste 1 en las horas con 5 min (ambas ≥ 1 m/s), desde `corrections.db`
(`mina_norte_wind/validate_segment_b.py`); como referencia, el tramo C con ClimaVUE:

| Serie | Día: mediana / IQR / % < 30° | Noche: mediana / IQR / % < 30° |
|---|---|---|
| B, cruda | −51° / 17° / 6 % | −63° / 121° / 15 % |
| B, cruda girada +53 (media aritmética) | +2° / 17° / 95 % | −16° / 91° / 34 % |
| B, corregida (5 min + vector) | +2° / 17° / 95 % | −29° / 36° / 40 % |
| B, corregida, sin `north_risk` | +2° / 17° / 95 % | −25° / 27° / 44 % |
| C, ClimaVUE, cruda | 0° / 15° / 99 % | −6° / 35° / 66 % |

Día y noche por tramo frente a Oeste 1, leyendo `met_corrected` (todas las horas, ambas ≥ 1 m/s):

| Tramo | Día: mediana / IQR / % < 30° | Noche: mediana / IQR / % < 30° |
|---|---|---|
| A | +6° / 37° / 75 % | −34° / 89° / 31 % |
| B corregido | +2° / 17° / 95 % | −28° / 38° / 38 % |
| B corregido, sin `north_risk` | +2° / 16° / 96 % | −25° / 40° / 41 % (705 de 1243 h) |
| C | −1° / 15° / 99 % | −7° / 47° / 56 % |

- **De día**, girar resuelve y el vector no añade nada, porque de día no se cruza el norte del sensor.
- **De noche**, el vector deja la dispersión de B al nivel de C. Queda un desfase nocturno residual de
  unos −18° a −20° respecto a C, que no desaparece al quitar las horas `north_risk` (−25°). Una parte
  pueden ser mezclas que la marca no detecta; el resto es compatible con desvío del drenaje por el
  shelter o los paneles, o con diferencias estacionales (C solo cubre sep–nov). No está resuelto.
- **Velocidad de B:** de día ~13 % baja frente a C respecto a Charaque. De noche es coherente salvo en
  febrero de 2026. Sin corregir.

**Contraste sin tomar a Oeste 1 como patrón** (`mina_norte_wind/climavue_transition.py`). La referencia es
la relación de Mina_Norte con cada vecina en C; el giro que la reproduce en B es este:

| Contraste | Oeste 1 | Charaque | MQG |
|---|---|---|---|
| Agosto (B) frente a 28/08–22/09 (C), día | 53° | 58° | 60° |
| Ídem, noche | 55° | 66° | 45° |
| Barrido en todo B con 5 min, día (θ que anula el desvío) | ~51° | ~63° | ~60° |
| Ídem, noche | ~74° | > 80° | ~74° |

- **De día, el giro está entre 51° y 60°** según la referencia y el periodo. En el barrido, θ = 59° deja
  las tres vecinas a ≤ 8°.
- **De noche hace falta 20–40° más que de día, y lo dicen las tres vecinas.** Mes a mes, el desfase de
  día frente a Oeste 1 es −44° a −56°. El de noche (5 min + vector) es −84° a −90° en ene–abr, −71° a −79°
  en may–jul y −61° en agosto. En C la diferencia entre día y noche es de solo −10° a +6°.
- **Un giro de compromiso no lo resuelve:** θ = 73° minimiza el error máximo (23°), pero deja el día a
  +19° de Oeste 1.
- **Contraste por sectores, B frente a C contra Oeste 1** (5 min + vector; ambas ≥ 1.5 m/s; sectores de
  30° de Oeste 1). Cancela el sesgo propio de Oeste 1 en cada dirección y es el más limpio, porque
  Charaque y MQG cambian ~25° con la estación respecto a Oeste 1:

  | Sectores de Oeste 1 | B − C |
  |---|---|
  | 210–300° | −48° a −53° |
  | 120–150° | −53° a −58° |
  | 180° (pocas horas) | −66° |
  | 0–90° | −72° a −103° |

  En los sectores con `north_risk` < 50 %, la media ponderada es **−53.6°**.
- **El exceso está solo en 0–90°**, donde cae el 0/360 del sensor girado (`north_risk` del 60–69 % de
  las horas). Es el artefacto de la media aritmética dentro de cada registro de 5 min (`north_risk`, antes
  llamada `riesgo_norte`), que la media vectorial horaria no puede deshacer. No es un efecto de flujo nocturno: la noche «pedía más giro»
  porque sus vientos del E–NE caen en ese sector. Corrige lo anotado antes en esta sección.
- **No es canalización del sitio B:**
  - la rosa no se estrecha: desviación circular de día de 34° en Mina_Norte frente a 31° en Oeste 1, y
    de 20° frente a 23° en C;
  - el desfase es constante en 180° de sectores limpios.

  Es lo contrario del tramo A, donde sí hay firma de canalización: rosa más estrecha que la de Oeste 1
  (11° frente a 19° de día) y desfase que cambia con la dirección.
- **Evolución:** el giro aparece la semana del 17/11/2025 (−29°, transición), es completo desde la del
  24/11 (−55°) y se mantiene entre −39° y −60° semana a semana hasta agosto. Hay una deriva lenta de unos
  −10° (−45° en ene–abr, −55° a −60° en jun–jul) que no se separa del cambio estacional de sectores.
  Desaparece de golpe con el ClimaVUE (semana del 31/08: +2°). No hay agravamiento brusco ni
  recuperación.
- **Fotos de campo** (usuario, 2026-11-12: anemómetro orientado bien con un margen de 20–30°): no cuadran
  con 53°. Pendiente saber la fecha de las fotos y la referencia usada (brújula, el shelter, el terreno).
- **Agosto de 2026 no sirve como «justo antes» limpio.** El IQR horario frente a Oeste 1 sube a 25° de día
  y a 97° de noche (13–17° y 25–50° en may–jul): el WindSonic ya se degradaba antes del cable cortado del
  27/08. La velocidad, en cambio, es congruente a ambos lados (razón con Oeste 1 de 0.96–1.01 en B frente a
  1.05–1.14 en C de día, y 0.97 frente a 0.92–0.95 de noche; r nocturno 0.98 y 0.97).
- **Tramo A:** es otro sitio, 785 m al este y más expuesto. Es válido como dato, pero no homogéneo con
  B y C: una serie climatológica de Mina_Norte debe tratarlo como emplazamiento distinto.

**Encaje en los grupos de viento ya establecidos (verificación, 2026-11-12; `groups.py` sin cambios).**
Se usaron los criterios de `grouping.py`: coseno entre ciclos diarios del vector de procedencia y
diferencia de forma del ciclo de velocidad. El periodo es el de `groups.py` (2025-11-10 → 2026-11-10) y
las vecinas se calculan en la misma ventana que Mina_Norte:

| Ventana | Mina_Norte | Mejor grupo (cos medio / dif. ciclo vel.) | Segundo | Más parecidas |
|---|---|---|---|---|
| Año (B + C) | corregida | **G2** 0.95 / 0.15 | G1 0.80 | Tala-1 0.97, Alto_Tala 0.96, Cortadera 0.94, MQG 0.94 |
| Año (B + C) | cruda | G3 0.88 / 0.22 | G2 0.77 | Chancado_primario 0.95, Apacheta 0.93 |
| Tramo B | corregida | **G2** 0.91 / 0.15 | G1 0.71 | Tala-1 0.94, Alto_Tala 0.94, MQG 0.91 |
| Tramo B | cruda | G3 0.79 / 0.22 | G5 0.53 | Chancado_primario 0.88, Apacheta 0.80 |
| Tramo C (ClimaVUE, sin ajuste) | — | **G2** 0.91 / 0.18 | G1 0.87 | Charaque 0.98, Minas_Sur 0.97, Alto_Tala 0.96 |

G2 está formado por Alto_Tala, Charaque, Cortadera, Papujune, Sarallenque_MQG-15-02 y Tala-1.
- **Corregida, Mina_Norte entra en G2** y cumple los dos umbrales (cos ≥ 0.60, diferencia ≤ 0.25).
- **El tramo C, que no lleva corrección, apunta al mismo grupo.** Es una confirmación independiente del
  giro.
- **Cruda, el giro la llevaba a G3** (Apacheta, Chancado_primario: régimen ajeno a 2–8 km).
- **Al regenerar con tope 6, G2 se parte en dos** (§5): Mina_Norte queda con Alto_Tala y Tala-1, ambos
  grupos con cos 0.97.

**Para cerrar en campo:** fecha del traslado tras el daño de noviembre de 2025; orientación del WindSonic
en B (si se alineó la marca N); posición del sensor respecto al shelter y a los paneles en B y en C.

### Chalsos: régimen del sitio, no espejo (revisión del 2026-11-12; corregida el 2026-11-13)

Se probó la hipótesis de espejo con las pruebas de Sarallenque y se descartó el mismo día. La primera
revisión usó la base horaria; la del 2026-11-13 (más abajo) rehace el análisis con direcciones
vectoriales y sustituye la lectura del terreno (punto 3) y la de las transiciones.

**Lo que parecía un espejo.** Ciclo diario al revés que sus vecinas: ~258° de noche y 112–150° de día,
frente a ~98° y ~255° de Cortadera. Transiciones en sentido contrario (0 % en el mismo sentido) y mejor
ajuste como espejo (constancia del ciclo 0.85–0.94 frente a 0.33–0.56 como giro), con K = 4–15° frente a
Cortadera en todos los trimestres. **Corrección del 2026-11-13:** esas cifras salen de `WindDir_Avg`, que es
un promedio aritmético de ángulos; las transiciones «al revés» y el paso de las dos por el S eran en parte
un artefacto de ese promedio (ver abajo).

**Por qué no lo es:**
1. **Programa.** El del logger de Chalsos (`PMC3-Tripode_01 v4.2.CR300`, en `references/`) es idéntico al
   de MQG-15-02, que funciona bien: solo difiere un byte posterior a `EndProg`. La dirección es la del
   ClimaVUE por SDI-12 (`R7!`, `CVData(6)`), sin transformar. Charaque hace lo mismo (`WindDir=CV_WindDir`).
2. **Viento fuerte.** Un espejo invierte a cualquier velocidad. En las 269 h con Cortadera ≥ 6 m/s (sobre
   todo westerlies de jun–nov, de 10 a 16 h), Chalsos coincide con sus vecinas: Chalsos − Cortadera = +2°
   de día (62 % a menos de 45°) y +7° de noche (79 %). Con K = 10°, un viento de 284° se leería como 86°.
   Ejemplos: 2024-07-10 Cortadera 284°, Chalsos 283°, Calientes1 296°, Apacheta 288°; 2025-04-22: 299°,
   296°, 283°, 283°. Control: Sarallenque S4, espejo conocido, no se alinea nunca con viento fuerte (4–13 %).
3. **Terreno.** ~~Sube hacia el S–SO–O y baja a una quebrada al E–ESE; drenaje nocturno desde el OSO y
   ascenso diurno desde el ESE.~~ Sustituido el 2026-11-13: esa lectura (anillos de 16 direcciones) no
   cuadraba con el relieve; la nueva está abajo.

#### Revisión del 2026-11-13: direcciones vectoriales, divisoria y embalse

**Dirección vectorial.** `WindDir_Avg` sale de `Average(1,WindDir,…)` en los dos loggers (línea 115 del
programa de Chalsos, línea 140 del de Cortadera): si en la hora el viento cruza el N, el valor cae hacia
180° (`wind_vector/INFORME.md`). Medido en Cortadera, que guarda también `WindDir_D1_WVT` (2024-03 →
2026-09, ≥ 0.5 m/s): el aritmético se aleja > 45° del vectorial en el 16–28 % de las horas de 18–22 h, ~10 %
de noche y < 1 % a mediodía; la noche aritmética queda +10–15° desviada (99° frente a 83–90°). Chalsos se
reconstruyó desde su Table3 de 5 min (`references/AAQ_Est_Chalsos_CR310_Table3.dat`, 2024-03-06 → hoy) con
`wind_vector/north_mixture.py` en la configuración de la validación externa (σ y etapas 1 y 2 entrenadas
con cortadera, papujune y quellaveco): 22 813 h, 3.9 % de registros de 5 min corregidos, 7.1 % de horas
con más de 30° de cambio frente a la media simple de los 5 min. En Chalsos el aritmético horario se aleja
> 45° del reconstruido en el 22–36 % de las horas de 7–9 h. La reconstrucción está en `wind_vector/rescue.py`
y entra en `met_corrected` como `CH-vector-rescue` (22 809 h; 3 521 con marca `north_mixture`). Solo cubre lo
que hay en el Table3: las horas posteriores llegan con el `WindDir_Avg` del logger. Con solo el dato horario,
un modelo entrenado con la historia reconstruida de Chalsos baja el error de la media mensual de 21° a 11°,
pero no sirve hora a hora (`wind_vector/INFORME.md` §3.9).

**Regímenes** (2024-03-06 → 2026-09-13, 21 225 h comunes; resultante ponderada por velocidad y sector
modal; el periodo acaba antes del giro de Cortadera del 2026-09-13):

| | Noche (0–6 h) | Día (11–16 h) | Transición de la mañana | Transición de la tarde |
|---|---|---|---|---|
| Cortadera (D1) | 89°, constancia 0.82; modal E 49 % | 258°, 0.97; modal OSO 59 % | sin dirección definida (8 h: constancia 0.04) | O → **N** → E (18–21 h: 276°, 302°, 19°, 63°) |
| Chalsos (reconstruida) | 268°, 0.75; modal O–ONO 32 % | 113°, 0.55; modal ESE 40 % | O → **N** → E (7–9 h: 296°, 46°, 94°) | E → **S** → O (18–21 h: 121°, 148°, 236°, 259°) |

Por la tarde las dos giran en sentido horario; un espejo invertiría el sentido. Con direcciones vectoriales,
la prueba del viento fuerte se mantiene: con Cortadera a 6–8 m/s, Chalsos coincide (< 45°) en el 50 % de
las horas frente al 26 % del espejo; con ≥ 8 m/s, en 9 de 10 (n = 10). Por debajo de 6 m/s gana el espejo
(53–76 %), porque los regímenes estables son opuestos en el eje E–O. Las 282 h fuertes: 82 % de 11 a 15 h,
82 % con Cortadera de 230–300°, 60 % de agosto a noviembre.

**Térmico, no mecánico.** De 11 a 15 h, con la velocidad de Cortadera fija, la fracción de horas de Chalsos
del ESE (80–170°) sube con la radiación global de Cortadera (0–4 m/s: 67 → 87 %; 4–6 m/s: 49 → 80 %), y su
velocidad mediana también (2.1 → 3.0 y 2.4 → 3.4 m/s); con la radiación fija, más westerly reduce el ESE.
Un remolino de sotavento crecería con el westerly. El componente diurno del ONO–NO (8–19 % de las horas)
aparece con westerly fuerte y poca radiación (Cortadera 5–7 m/s y < 600 W/m²: 55 %; ≥ 900 W/m²: 17 %;
Cortadera 3–5 m/s y ≥ 900 W/m²: 6 %) y en junio y agosto (30 %): es el flujo regional que cruza la
divisoria cuando el viento de valle se debilita.

**Terreno** (SRTM 30 m; cortes por la resultante de cada régimen, mediana de siete cortes a ±15°; drenaje
D8 en rejilla de 120 m). La pendiente de los primeros 30–720 m sube hacia el SSO (~210°, 9–20 %), pero
ningún régimen la sigue. Chalsos está en una **divisoria**: el agua que cae en la estación va al ESE y luego
al S, a una quebrada que baja 489 m en 3.6 km; a 300 m al O–NO va a la otra cuenca, la del embalse.
- Día (de 113°): llega subiendo desde la quebrada (−56 m a 240 m, −146 m a 1 km, banda −187 a −117) y tras la
  estación baja un poco (−48 m a 1 km). Es el viento de valle de la quebrada, que cruza la divisoria; no va
  hacia terreno más alto. El arranque (8–9 h) coincide con el calentamiento de las laderas que miran al E
  (dato del usuario), pero el régimen dura hasta las 18 h (65–86 % de las horas de 10 a 18 h).
- Noche (de 268°): llega desde terreno más alto a 1–1.5 km al O (+35 y +124 m) y baja hacia el E, a la
  cabecera de la quebrada (−61 m a 1 km; banda −128 a −6). Hipótesis: sigue el relieve kilométrico, no el
  del lomo; ajusta peor (tramos casi llanos en la banda) y un tercio de las noches viene del ONO–NO, hacia
  donde el terreno baja.
- Cortadera está en un alto local (más bajo en todas las direcciones hasta 1 km) y sigue la pendiente
  regional (sube a 50°, 60 m/km): de noche llega desde terreno +196 m más alto a 2.5 km; de día va hacia
  terreno +255 m más alto a 2.5 km.

**Embalse** (comentario, no determinante). Situado con una captura de Google Earth del usuario (unos 1 km²;
la imagen más antigua es de agosto de 2022, ya con agua, más pequeño): brazo NE a 0.9 km de Cortadera
(rumbo 231°, el valle baja 190 m), brazo SE a 2.6 km de Chalsos (307°, baja 176 m). Cortadera: de día el
viento sale del lado del embalse y de noche va hacia él, como un viento de valle con o sin agua. Chalsos,
al revés: de día va hacia el embalse y de noche viene de su lado, y la brisa de tierra (del SE de noche) solo
aparece en el 3.8 % de las noches. No hay antes y después medible: Chalsos empieza en 2024-03, y Cortadera
cambia de régimen en la segunda quincena de 2022-09 por otra causa (§8). Del 2023 al 2026, mientras el
embalse crece, el régimen de Cortadera no cambia (día 256–264°, noche 87–92°, velocidad diurna 1.59–1.64
veces la de Papujune).

**Conclusión.** El sensor mide bien. Chalsos tiene el régimen de su divisoria, dominado por la quebrada del
SE, opuesto al de sus vecinas. `WIND_EXCLUDED["Chalsos"]` («dirección invertida, sin confirmar») ya no tiene
motivo como fallo; pero si se quita, Chalsos seguirá sola en el agrupamiento por régimen, porque su ciclo no
se parece al de ninguna. Para un uso de la dirección, mejor la serie reconstruida que `WindDir_Avg`.
**Decisión (usuario, 2026-11-13):** Chalsos sigue por su cuenta, fuera del agrupamiento de viento;
`WIND_EXCLUDED` se mantiene con el motivo actualizado (régimen del sitio, no fallo).

---

## 10. Pendientes

- Viento (§9), 2026-09-24: sale de la vista por grupo. En la vista por variable: rosas día/noche por zona (Mina, Sur, Altiplano; `rose_maps.py`) y, por grupo de viento, serie horaria y ciclo diario de velocidad. Se probaron y retiraron el ciclo de dirección, la constancia diaria y el mapa hora × día: saturaban sin aportar. Los grupos de viento separan además por forma del ciclo de velocidad (`grouping.MAX_DIF_CICLO_VEL`), que saca a Camp_Quellaveco.
- Camp_Quellaveco: el anemómetro se calibró el 2026-09-10 (dato del usuario). Desde ese día aparecen horas en 0.00 exacto (antes 0 %, después 8–50 % de las horas en la mayoría de los días) y la razón día/vecinas baja de ~1.4 a ~1.05. Diagnóstico nocturno en §8 (sensor que no arranca). Preguntar qué se hizo (rodamientos, hélice u offset del programa) y qué modelo de sensor tiene la torre.
- Curar `groups_draft.py` → `groups.py`.
- Regla de QC para escalones de nivel en T y HR (caso Camp_Quellaveco), comparando con vecinas.
- Confirmar con partes de campo los casos de §8 y la coordenada de Campamento Quellaveco.
- Radiación solar: en pausa por decisión del usuario (2026-09-24); se sigue bien sin el visor.
- Lluvia y UV: exploradas (§11); falta decidir figuras y QC antes de llevarlas al visor. Para los descartes de lluvia, esperar el historial de intervenciones.
- Sarallenque (§9, revisión del 2026-11-09): (1) `WIND_EXCLUDED` se deja en `("2025-07-14", None)`: la dirección diurna tras la visita sigue −50° a −62° de MQG; (2) comparación con MQG hecha (noche resuelta, día no; la velocidad relativa bajó a 0.32 de día y 0.44 de noche); (3) sustituido el 2026-11-12: no es un giro de +180° de noche sino un espejo día y noche (§9, «espejo, no giro»), con K = 357° / 294° / 341° en S2 / S3 / S4; pendiente de aplicar en `corrections.db` (tipo `mirror`); (4) preguntar a campo qué se hizo el 2026-09-25 (¿solo giro, o programa, configuración o unidad?) y pedir el programa del CR1000X anterior; (5) pedir visita: qué tapa o desvía el viento diurno (la dirección derivó de 214° a ~170° en seis semanas) y la ubicación anterior a julio de 2025.
- Mina_Norte (revisión del 2026-11-09): hecha la regeneración de grupos (§5; entra sola) y el recálculo de `z_baro` (§2; se mantiene 3983). Su viento desde 2026-08-28 es estable y coherente con Charaque, Minas_Sur y Papujune (§9). Coordenada confirmada el 2026-11-12 (§2). Con Oeste 1 (§9, 2026-11-12) quedan tramos A/B/C fechados. La corrección del tramo B (+53°, día y noche, 5 min + vector desde 2026-01-11) y las dos ventanas sin dirección están aplicadas en `corrections.db`, y el visor las lee (§6). Ya está en el agrupamiento de viento, con Alto_Tala y Tala-1 (§5; `groups.py` regenerado el 2026-11-12). Falta entender el residuo nocturno de −20° y la velocidad nocturna de B. Sin datos de campo sobre la orientación ni la fecha del traslado (usuario, 2026-11-12).
- Chalsos (§9, 2026-11-12, corregido el 2026-11-13): no es fallo, es el régimen de su divisoria (descartado el espejo: programa idéntico al de MQG, coincide con Cortadera con viento fuerte, por la tarde gira en el mismo sentido, el ESE diurno depende de la radiación). Cerrado el 2026-11-13: sigue en `WIND_EXCLUDED` por decisión del usuario (va sola) y su dirección reconstruida desde 5 min está en `corrections.db`. Abierto: `CH-vector-rescue` tiene el fin abierto, pero solo hay reconstrucción hasta 2026-11-13 11:00; con un Table3 nuevo hay que rehacer `wind_vector.rescue` y `build_corrections`.
- Cortadera y Papujune (§8): cambio de dirección en la segunda quincena de 2022-09; pedir partes de campo.
- Planta_Concentradora (§8): transiciones al revés, pero con viento fuerte se alinea con Papujune; más probable un cambio de sitio hacia 2024-04-06 que un espejo. Revisar con la prueba de viento fuerte por tramos y el terreno.
- Torres giradas en septiembre de 2026 (§8): Cortadera (−73°), Alto_Quellaveco (−88°) y Alto_Tala (≈ −65°), probablemente calibraciones. Confirmar con los partes, decidir qué orientación es la buena (en Alto_Tala las vecinas no coinciden) y corregir o excluir: hoy entran en los grupos de viento.
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

