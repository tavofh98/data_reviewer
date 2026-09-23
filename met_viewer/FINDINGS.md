# Visor de meteorología por grupos — hallazgos y decisiones

_Actualizado: 2026-09-23 · Base: `database_duck/anglo_ambiental.db` (datos 2019-09 → 2026-09-23)_

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
- **Fuente válida: `Estaciones AAQ.kmz`** (raíz del workspace, ubicado en Google Earth). Con sus
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
red y de la del sensor (±1 mbar del ClimaVUE ≈ ±13 m a 635 mbar). Recalcular con
`calibrate_baro.py` al pasar de 30 días.

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
| Sarallenque | viento | desde 2025-07-14 dirección y velocidad cambian a la vez; de noche viene de ~250° en vez de ~78°; sector S–SO–O vacío | traslado del shelter girado 180° y a un punto con obstáculo al S–SO–O (ver §9) |
| Papujune | T | 132 h con 0.0 exacto (abr-2026) | sensor caído (descartado por `STUCK`) |
| Charaque | HR | 752 h en 101.2 % (ene–abr 2025), aceptadas por el rango | calibración |
| Apacheta / Minas_Sur | HR | cambio de nivel en ene-2026 / may-2026 | cambio de sensor (Apacheta: mismo mes que su pluviómetro) |
| Calientes1 | T, HR | jul-2025: 64 % de valores redondeados a un decimal (normal ~10 %) | cambio de programa |

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

**Tratamiento:**

| Tramo | Dirección de noche | Dirección de día | Velocidad |
|---|---|---|---|
| hasta 2025-07-13 | válida | válida | válida |
| 2025-07-14 → 2025-09-14 | no válida | no válida | no válida |
| 2025-09-15 → ~2025-11-16 | corregible por tramo cuando se mida el ángulo (~200° y ~140° según las estimaciones semanales) | no comparable | no comparable |
| desde ~2025-11-17 | válida restando 180° (confirmar con brújula) | no comparable: sector S–O tapado | no comparable de día (+30 %) |

Hasta confirmarlo en campo, Sarallenque queda fuera de cualquier agrupación de viento desde el
2025-07-14.

---

## 10. Pendientes

- Implementar la sección de viento (§9).
- Curar `groups_draft.py` → `groups.py`.
- Regla de QC para escalones de nivel en T y HR (caso Camp_Quellaveco), comparando con vecinas.
- Confirmar con partes de campo los casos de §8 y la coordenada de Campamento Quellaveco.
- Lluvia y radiación: pendientes.
- Sarallenque: medir con brújula la marca de norte del WindSonic, conseguir la fecha y la ubicación anterior del traslado de julio de 2025 y, con eso, añadir una corrección de dirección por tramos en `stations.py` (como `BARO_OFFSET`).
