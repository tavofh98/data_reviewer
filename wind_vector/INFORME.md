# Dirección del viento: error de `WindDir_Avg` y alternativas vectoriales

_Estaciones evaluadas: Cortadera, Papujune y Alto Quellaveco (CR1000X). Periodo: 2020-11 → 2026-10 (Papujune y Quellaveco), 2023-01 → 2026-10 (Cortadera). ~134 000 horas._

## 1. Conclusión

1. **`WindDir_Avg` no sirve como dirección media donde el viento viene del sector norte** y arrastra además un error moderado en el resto. Frente al Θ1 que calcula el logger, el error del promedio **mensual** que entrega el reporte es de 42–72° en promedio.
2. **Derivar la dirección de 1 h desde los 5 min no lo arregla si los 5 min son `WindDir_Avg`.** Lo reduce a la mitad (promedio mensual: 13–31°), pero el promedio de 5 min ya llega mal desde el logger.
3. **Sí se puede derivar con `WindDir_D1_WVT` y `WindDir_SD1_WVT` de 5 min**: el error del promedio mensual baja a 0.8–1.6°. Pero entonces es más simple y exacto usar directamente el `WindDir_D1_WVT` de la tabla de 60 min.
4. **El cambio de variable está justificado** (Θ1 es el estadístico que recomiendan Campbell, EPA y WMO; ver `TEORIA.md`), pero solo es posible hacia atrás en las estaciones cuyo logger guarda `WindDir_D1_WVT`.

## 2. Cómo se midió

- **Verdad:** `WindDir_D1_WVT` de la tabla de 60 min (Θ1 sobre 720 muestras de 5 s).
- **Variantes** (todas con los 12 registros de 5 min de la hora):

| | Qué es |
|---|---|
| V0 | `WindDir_Avg` horario (lo que hoy usa `anglo_reporte`) |
| V1 | vectores unitarios de `WindDir_Avg` de 5 min |
| V2 | `WindDir_Avg` de 5 min ponderado por velocidad |
| V3 | vectores unitarios de `D1` de 5 min |
| V4 | `D1` de 5 min ponderado por R, recuperada de `SD1` (Yamartino inverso) |
| V5 | `D1` de 5 min ponderado por velocidad y R: aproxima Θu (resultante) |

- **Horas evaluadas:** las que tienen los 12 registros, velocidad horaria > 0 (se excluyen calmas) y todas las variantes definidas.
- **Nivel reporte:** la media circular del periodo se calcula como lo hace `anglo_reporte` (`_stats_circular`, vectores unitarios sin ponderar, en blanco si R < 0.05), con la variante y con la verdad, en ventanas de día, semana y mes con ≥ 80 % de horas.
- **"Sector norte":** horas cuya dirección real (Θ1 horario) está a ≤ 45° del norte. Es el 9 % de las horas en Cortadera, 29 % en Papujune y 27 % en Quellaveco.

## 3. Resultados

### 3.1 Error por hora (grados, circular)

| Estación | Variante | Media | p95 | % horas > 10° |
|---|---|---|---|---|
| Cortadera | V0 | 14.05 | 98.4 | 21.1 |
| | V1 | 6.33 | 36.0 | 14.3 |
| | V3 | 1.42 | 7.3 | 3.4 |
| | V4 | 1.21 | 6.4 | 2.9 |
| | V5 (≈Θu) | 2.94 | 12.7 | 6.9 |
| Papujune | V0 | 28.14 | 138.8 | 40.3 |
| | V1 | 13.88 | 72.6 | 29.5 |
| | V3 | 2.66 | 11.9 | 6.3 |
| | V4 | 2.47 | 11.7 | 6.0 |
| | V5 (≈Θu) | 2.49 | 9.7 | 4.8 |
| Quellaveco | V0 | 19.30 | 125.0 | 27.5 |
| | V1 | 7.96 | 39.1 | 19.3 |
| | V3 | 1.31 | 6.4 | 2.8 |
| | V4 | 1.10 | 5.8 | 2.5 |
| | V5 (≈Θu) | 3.03 | 12.2 | 6.9 |

### 3.2 Error medio por hora según el sector del viento real

| Estación | Sector | V0 | V1 | V3 | V4 |
|---|---|---|---|---|---|
| Cortadera | norte (±45°) | 83.7 | 40.1 | 3.4 | 3.0 |
| | resto | 7.2 | 3.0 | 1.2 | 1.0 |
| Papujune | norte | 72.8 | 34.9 | 3.0 | 2.8 |
| | resto | 9.7 | 5.2 | 2.5 | 2.3 |
| Quellaveco | norte | 56.4 | 21.8 | 1.3 | 1.1 |
| | resto | 5.9 | 3.0 | 1.3 | 1.1 |

La zona muerta del sensor (355–360° leído como 0°) y el cruce por el norte hacen que, con viento oscilando alrededor del norte, la media aritmética caiga hacia el sur: la mediana del error en ese sector es de 87° en Cortadera con V0.

### 3.3 Error de la media del periodo (lo que llega al reporte)

Error medio en grados de la media circular del periodo frente a la hecha con Θ1 horario:

| Estación | Ventana | V0 | V1 | V2 | V4 | V5 (≈Θu) |
|---|---|---|---|---|---|---|
| Cortadera | día | 36.7 | 16.6 | 14.2 | 2.2 | 4.8 |
| | semana | 42.5 | 18.2 | 15.3 | 1.1 | 2.9 |
| | mes | 51.6 | 18.9 | 17.6 | 0.8 | 2.8 |
| Papujune | día | 53.3 | 24.3 | 18.8 | 3.1 | 2.8 |
| | semana | 61.6 | 28.6 | 22.8 | 2.0 | 1.9 |
| | mes | 72.3 | 31.2 | 23.5 | 1.6 | 1.9 |
| Quellaveco | día | 26.2 | 9.4 | 8.8 | 1.4 | 3.0 |
| | semana | 31.5 | 11.0 | 10.5 | 1.0 | 2.7 |
| | mes | 42.5 | 13.2 | 13.9 | 1.1 | 3.3 |

El error mensual con V0 supera al diario porque en un mes el viento oscila entre sectores y la media aritmética de cada hora, mal calculada, no se compensa.

### 3.4 Θ1 frente a Θu

Con V5 (≈Θu) frente a Θ1: 2.5–3.0° de diferencia media por hora y 1.9–3.3° en el promedio mensual. **La elección entre Θ1 y Θu mueve la dirección media unos pocos grados; no es lo que decide.** Lo que decide es dejar de promediar ángulos aritméticamente.

### 3.5 Caso completo: Alto Quellaveco (rosas y serie)

`output/caso_quellaveco.html` (generado con `python -m wind_vector.case_study`) muestra, para las 51 687 horas evaluadas, la rosa día/noche con la dirección real (Θ1 del logger) y con la estimada desde 5 min (V1), la serie horaria con su error, un episodio de 48 h a 5 min y la dispersión real-estimada. Solo cambia la dirección; la velocidad es la misma en ambos casos.

| Franja | Horas | Horas que caen en otro sector (16) | Diferencia total de la rosa (½Σ\|Δ\|) | Mayor diferencia en un sector | Error medio / mediana por hora | Horas con error > 90° |
|---|---|---|---|---|---|---|
| Día (10–17 h) | 16 997 | 14.3 % | 6.3 pp | 5.8 pp en 338° | 3.8° / 0.39° | 0.2 % |
| Noche (22–06 h) | 19 557 | 26.3 % | 13.3 pp | 7.1 pp en 0° | 10.7° / 0.84° | 2.5 % |

Dirección media circular del periodo por franja: de día, real 272.6° y estimada 268.7° (V0: 265.9°); de noche, real 68.1° y estimada 83.3° (V0: 112.9°).

Lectura: la estimación desde `WindDir_Avg` de 5 min **reproduce la forma general de la rosa, sobre todo de día**, pero no el valor de cada hora: el 19 % de las horas queda a más de 10° de la real, y las horas con viento del norte se desplazan hacia otros sectores (la rosa nocturna pierde 7 pp en el sector 0°). El mecanismo se ve en el episodio de 48 h: cuando el viento oscila alrededor del norte, los `WindDir_Avg` de 5 min promedian valores de ambos lados y caen cerca del sur, mientras que `D1` sigue pegado al norte. Una vez promediado en el logger, ese error no se puede deshacer con los datos guardados.

### 3.6 El sector norte: ¿se puede corregir?

Detalle y las tres estaciones en `output/RESULTADOS_NORTE.md`; gráfico en `output/norte_error_por_sector.html`. Cifras de Cortadera, verificadas con una reimplementación independiente (coinciden salvo ≤ 0.1° en la mediana circular, por desempates).

**Ingeniería inversa del programa de Cortadera** (v7.4, `Cortadera_2025-01-10_1.CR1X`, líneas 316–329). Por cada muestra de 5 s:
1. `BrHalf(..., 355, 0)`: el potenciómetro da 0–355°; el 05103 tiene una zona muerta de 5° (355–360°).
2. `Si ≥ 355 o < 0 → 0`: la zona muerta se lee como 0°.
3. `WindDir_offset = −7` (desde 2024-06-03): `dirección = lectura − 7`; si queda en [−5, 0) se fija en 355; si es < −5 se le suma 360.

El resultado coincide con la dirección real salvo dos tramos que quedan "pegados": 348–353° se lee como 353° y 355–360° como 355°. El error por muestra es de 5° como máximo, y `WindDir_Avg` no puede superar 355.0°. Huella en los datos: el máximo de `WindDir_Avg` es 355.0° en las tres estaciones. Los valores exactos de 0.0°, 353.0° y 355.0° son raros y no permiten datar el cambio (ver 3.7).

**Esas correcciones no son el origen del error grande y no sirven para invertirlo.** Un error de 5° por muestra no explica errores de 100° o más. El error entra en `Average(WindDir)`: promedia muestras de ambos lados del norte (350° y 10° dan 180°) y guarda un solo número; las muestras de 5 s no se conservan. Muchas distribuciones distintas dan la misma media, así que desde `WindDir_Avg` no hay forma exacta de recuperar Θ1.

Los datos lo confirman. De los registros de 5 min con viento cuyo `D1` está a ≤ 20° del norte (3.8 % de los registros), solo el 17 % tiene `Avg` a ≤ 10° de `D1` y el 46 % lo tiene a más de 90°. Solo el 0.6 % de los `WindDir_Avg` cae a ≤ 20° del norte. En sentido contrario, si `Avg` está cerca del norte, `D1` también lo está (97 %): el viento del norte es casi invisible en `WindDir_Avg`.

**Heurísticas por hora (mediana circular, descarte de registros ruidosos).** No ayudan. Con la dirección real a ≤ 45° del norte, el error medio es 40.1° con V1, 40.4° con la mediana circular y 41.4° quitando los registros a más de 45° de la mediana; en el conjunto de todas las horas la mediana empeora (7.7° frente a 6.3°). Cuando el viento oscila alrededor del norte, todos los registros de la hora están contaminados, no hay valores aislados que quitar.

**Excluir el sector norte.**

| Criterio | Horas retenidas | Error medio V1 | p95 | Horas > 10° | Horas > 30° |
|---|---|---|---|---|---|
| Sin filtro | 100 % | 6.33° | 36.0° | 14.3 % | 6.0 % |
| Real fuera de ±20° del norte (20–340°) | 96.6 % | 4.39° | 25.6° | 11.8 % | 4.1 % |
| Real fuera de ±45° del norte | 91.0 % | 3.00° | 17.8° | 8.8 % | 2.4 % |
| R1: `WindDir_Avg` horario en 20–340° | 99.9 % | 6.33° | 36.0° | 14.3 % | 6.0 % |
| R2: los 12 `Avg` de 5 min en 20–340° | 96.3 % | 5.83° | 32.8° | 12.8 % | 5.5 % |
| R3: R2 y ningún salto > 60° entre registros consecutivos | 77.0 % | 0.62° | 2.9° | 1.3 % | 0.2 % |
| R4: R2 y ningún registro a > 45° de la mediana de la hora | 71.7 % | 0.35° | 1.2° | 0.6 % | 0.04 % |

- Las dos primeras filas filtran por la dirección real, que en la práctica no se conoce. R1 y R2 filtran por el sector usando solo los 5 min, y casi no mejoran nada, porque el viento del norte no aparece como norte en `Avg`.
- **Lo que sí funciona es una regla de consistencia interna (R3, R4).** Cuando los 12 valores de 5 min son coherentes entre sí, la estimación es casi exacta; solo el 0.01 % de las horas aceptadas por R4 tiene la dirección real a ≤ 20° del norte. Papujune (R4: 54 % de horas aceptadas, error medio 2.6°) y Quellaveco (53 %, 1.1°) se comportan igual.
- **El coste es un sesgo de selección.** R4 acepta solo el 12.9 % de las horas con viento real a ≤ 45° del norte, y también rechaza buena parte de los sectores variables (SE–S, ~20 % de aceptación) donde el error era bajo. Una rosa hecha solo con horas aceptadas subrepresenta el norte.

**Conclusión:** el error del norte no se puede corregir con `WindDir_Avg`, pero sí se puede **detectar** y marcar. Las horas marcadas hay que excluirlas o reportarlas como no fiables, no reparar.

### 3.7 Los programas de Alto Quellaveco, Papujune y Cortadera frente a los datos

Detalle en `output/RESULTADOS_PROGRAMAS.md`.

- **Misma arquitectura en los tres.** Scan de 5 s; `PulseCount` para la velocidad y `BrHalf(..., 355, 0)` para la dirección; lo que cae en la zona muerta (≥ 355°) se pone a 0°; y en las tablas de 5 min y de 60 min se guardan tanto `Average(WindDir)` como `WindVector(WS_ms, WindDir, ..., 0, 0, 0)` sobre la misma variable ya corregida. Nada desenrolla el ángulo antes de promediar.
- **Diferencias.** El desfase de −7° está en Cortadera (desde 2024-06-03), Papujune (desde 2024-09-05) y Campamento; el programa de Alto Quellaveco (versión 2026-02-25) no lo tiene. Quellaveco guarda `Avg` y `D1` en IEEE4 y los otros en FP2.
- **Control.** Alto Quellaveco no tiene desfase y sirve de control. Error medio con el viento real a ≤ 45° del norte, antes y después de la fecha del desfase:

| Estación | V0 antes → después | V1 antes → después |
|---|---|---|
| Cortadera (desfase 2024-06-03) | 94.8° → 79.3° | 43.6° → 38.8° |
| Papujune (desfase 2024-09-05) | 72.1° → 74.3° | 35.3° → 34.2° |
| Alto Quellaveco (sin desfase; fecha 2024-06-03) | 64.9° → 46.9° | 23.8° → 19.6° |

  El desfase no empeora el error del norte, y las variaciones entre periodos son del mismo tamaño en la estación de control, que no cambió. Las diferencias entre estaciones (Quellaveco 22°, Cortadera 40°, Papujune 35° en el norte) vienen de cómo se comporta el viento en cada una, no del programa.
- **Las huellas de valores exactos no sirven para datar el cambio.** Los registros con `D1` exactamente en 0.0°, 353.0° o 355.0° son menos de 0.03 % y aparecen igual en la estación sin desfase. Lo dicho en 3.6 sobre las correcciones sigue en pie por lectura del código (error ≤ 5° por muestra), pero los datos no lo confirman con precisión.
- **Los tres loggers ya guardan `D1` en todas sus tablas.** Para esas estaciones no hay que tocar el programa: solo usar el dato.
- **Pista sobre las estaciones `WVc`.** El historial del programa de Campamento anota que el 2023-01-09 el registro de `WindDir` del Oizom pasó de promedio a vector, y su programa estandariza tablas con Calacaja. Falta ver los programas de Calacaja, Ilo y Planta_Concentradora para confirmar que su `WindDir_Avg` `WVc` sea Θ1.
- **Limitación.** Solo se dispone de la última versión de cada programa; las versiones de 2020–2024 pueden haber manejado la dirección de otro modo.

### 3.8 Corrección de las mezclas del norte con un modelo físico del promedio (`north_mixture.py`)

**Física.** Supongamos que las 60 muestras de 5 s se reparten alrededor de una dirección real μ con una dispersión σ. Entonces la media aritmética esperada se puede calcular: A = g(μ, σ) = E[(μ + σZ) mod 360].
- Lejos del norte, g(μ, σ) ≈ μ.
- Dentro de ±3σ alrededor de 0°, g cae de ~360 a ~0. Es la rama de mezcla: el valor depende de la fracción de muestras a cada lado del corte.

Por eso cada `WindDir_Avg` (A) tiene dos candidatos:
- **H0:** la dirección real es A.
- **H1:** mezcla del norte. La dirección real es el μ de la rama de mezcla que da g(μ, σ) = A. No es 0°, sino un ángulo concreto que se despeja de A.

El modelo se cumple en los datos. Con `D1` y `SD1` como dirección y dispersión reales, el g predicho correlaciona 0.96–0.98 con el A observado en los registros cercanos al norte.

**Método.** Solo usa lo que guardan las estaciones sin `D1`: `WindDir_Avg`, `WS_ms_Avg`, `WS_ms_Max` y la hora.
1. **σ estimada.** Una regresión de `SD1` con la velocidad, la racha, la hora y la variabilidad de los vecinos. El error mediano es de 2.5–3°.
2. **Etapa 1.** Un clasificador (HistGradientBoosting) estima P(H1). Usa los vecinos (±3, ±6 y ±12 registros), los saltos entre registros consecutivos y rasgos físicos: el μ despejado, su plausibilidad |μ|/σ y cuántos vecinos tienen un candidato cerca del norte.
3. **Etapa 2.** El mismo clasificador, añadiendo la P(H1) de la etapa 1 promediada en la ventana. Una mezcla suele estar rodeada de otras mezclas, que la etapa 1 por sí sola no ve como "cerca del norte".
4. **Composición.** Cada registro entra en la hora como un vector blando, P(H1)·u(μ) + (1 − P(H1))·u(A). Los registros dudosos pesan menos, y no hay umbral que ajustar.

Todo **se entrena con dos estaciones y se mide en la tercera**. La etapa 2 se entrena con probabilidades de la etapa 1 calculadas fuera de muestra. El oráculo elige siempre bien entre A y μ, con la σ real (techo).

Error medio por hora (grados) frente al Θ1 del logger; entre paréntesis, % de horas con error > 30°:

| Estación | Horas | V1 | Modelo | Oráculo |
|---|---|---|---|---|
| Cortadera | todas | 6.3 (6.0) | **3.1** (1.9) | 1.9 (0.9) |
| Cortadera | norte (real ≤ 45°) | 40.1 (43.2) | **7.7** (4.0) | 4.8 (2.1) |
| Cortadera | resto | 3.0 (2.4) | **2.6** (1.6) | 1.7 (0.8) |
| Papujune | todas | 13.9 (13.8) | **6.1** (4.0) | 3.7 (1.6) |
| Papujune | norte | 34.9 (37.7) | **10.4** (8.1) | 4.4 (1.5) |
| Papujune | resto | 5.2 (4.0) | **4.2** (2.3) | 3.5 (1.6) |
| Quellaveco | todas | 8.0 (6.9) | **3.5** (1.6) | 1.9 (0.6) |
| Quellaveco | norte | 21.8 (21.4) | **4.6** (0.9) | 2.3 (0.5) |
| Quellaveco | resto | 3.0 (1.7) | 3.1 (1.8) | 1.7 (0.6) |

**Qué se aprendió por el camino** (pruebas en el scratchpad, no reproducidas en el script):
- **El cuello de botella es detectar las mezclas, no el ángulo que se pone en su lugar.** Con decisión dura entre A y 0°, el techo ya era de 5.8/5.1/3.1° con viento del norte. Despejar μ lo baja a 4.8/4.4/2.3°. La primera versión del clasificador, con umbral 0.5 y sin rasgos físicos, dejaba pasar 6–54 mezclas por cada falsa alarma en las horas del norte con más error.
- **Hay un límite físico.** Con σ ≈ 20°, viento del norte a 350° produce A ≈ 240°, igual que un viento real del oeste. Las falsas alarmas caen en vientos reales a unos 90° del norte. Un modelo de estados (HMM sobre la dirección real, con emisión g(θ, σ̂)) choca con lo mismo: si mejora el norte, empeora el resto. No supera al clasificador.
- **Se descartaron:** corregir sin etiquetas el cambio de proporción de mezclas entre estaciones (EM de Saerens), porque mejora Papujune pero empeora Cortadera; la decisión dura con umbral, porque baja el error con norte pero sube el del resto; quitar la hora del día, porque no cambia el balance; y predecir directamente el vector de `D1` de cada registro con una regresión, porque queda a ±0.4° de los vectores blandos, mejor en Papujune y peor en Cortadera y Quellaveco.

**Límites.**
- Solo se validó entre estas tres estaciones CR1000X de la misma zona. Papujune, con más viento del norte que las otras dos, es la que peor resulta. En una estación con otro clima, el error puede ser mayor.
- El método necesita los `WindDir_Avg` de 5 min. No se comprobó que las estaciones del tercer grupo de la sección 4 los tengan con todo su histórico.

## 4. Qué implica para la base y `anglo_reporte`

**Recomendación:** incorporar `WindDir_D1_WVT` (y `WS_ms_S_WVT`, `WindDir_SD1_WVT`) a `database_duck` desde las tablas de 60 min y hacer que `anglo_reporte` tome `WindDir_D1_WVT` como dirección en las estaciones donde exista. La velocidad no cambia: en Cortadera 5 min, `WS_ms_S_WVT` coincide con `WS_ms_Avg` en el 99.98 % de los registros (no se midió en las demás).

Cambios concretos:
- `database_duck/matrices.py` descarta hoy las columnas `*_WVT`; hay que añadirlas a las estaciones que las traen.
- `anglo_reporte`: `VARIABLES_REPORTE` y `AGREGACION` pasan de `WindDir_Avg` a `WindDir_D1_WVT` solo en esas estaciones; la lógica circular de `_stats_circular` ya es correcta para un Θ1 horario.

**Cobertura de la recomendación** (inventario de `datafiles/data_1h`):

| Situación | Estaciones | Qué se puede hacer |
|---|---|---|
| Tienen `WindDir_D1_WVT` horario | Alto_Quellaveco, Camp_Quellaveco (CR1000X), Cortadera (CR1000X), Papujune, Altarani, Tala-1, Tala_Legal, Vizcachas, Huachunta (2 loggers), Minas_Sur (CR300, desde 2026-04) | Usar `D1` con todo su histórico. |
| `WindDir_Avg` ya es vectorial (etiqueta `WVc`) | Calacaja, Ilo, Planta_Concentradora, Camp_Quellaveco (Oizom) | Sin cambio; falta confirmar en el programa que sea Θ1 y no Θu. |
| Solo `WindDir_Avg` aritmético | Apacheta, Calientes1, Chalsos, Charaque, Cerro_Salviani, DME3_Cortadera, Sarallenque, Sarallenque_MQG-15-02, Mina_Norte, Alto_Tala, Titire, PCHAP, Oeste1, DPB1 | El histórico se corrige solo en parte, con la reconstrucción de 3.8 si hay 5 min. Hay que añadir `WindVector` al programa del logger para tener Θ1 de ahora en adelante. |

**Limitación que se acepta:** en el tercer grupo la dirección seguirá siendo poco fiable en el pasado, sobre todo con viento del sector norte. El histórico solo se puede corregir de forma aproximada con la reconstrucción de la sección 3.8, que necesita los registros de 5 min. Mientras tanto convendría marcar en el reporte esa dirección como aritmética, porque hoy se mezclan en el mismo informe estaciones con dirección vectorial y aritmética.

## 5. Límites del estudio

- **Solo tres estaciones CR1000X con 5 min y 1 h vectoriales** (más Huachunta, no evaluada aquí). Las demás no tienen verdad vectorial.
- **La verdad es el Θ1 del logger.** Los resultados dicen cuánto se aleja cada variante de él, no de la dirección "real" del viento, que no se conoce.
- **La implementación está verificada por una reimplementación independiente** desde los `.dat` originales (Cortadera y Quellaveco; Papujune no se contrastó): las cifras coinciden. Esa reimplementación siguió la misma especificación, por lo que no valida decisiones de método como el umbral de 45°.
- **Papujune:** el error de V3/V4 sube de 1.3–1.6° (2021–2022) a 3.2–3.5° (2024–2025) y en una exploración previa (no cuantificada aquí) los desacuerdos grandes entre `WindDir_Avg` y `D1` crecieron desde 2023 y se concentraban en registros de velocidad 0. Puede ser un problema del sensor; está fuera del alcance.
- **Quellaveco 5 min:** el fichero de abril de 2026 trae 52 registros horarios mezclados dentro de la tabla de 5 min (se descartan con la regla de "último gana"). Conviene revisarlo en origen.
- **No verificado:** las prescripciones de ASTM D5741, ISO y VDI 3786-2, y el valor que devuelve el logger en una calma total.

## 6. Reproducir

Desde `explorar_qaqc/`:

```
uv run python -m wind_vector.loader          # alinea 5 min con 60 min
uv run python -m wind_vector.build_load_report
uv run python -m wind_vector.analyze         # escribe output/RESULTADOS.md
uv run python -m wind_vector.north_mixture   # sección 3.8 (tablas por consola)
```

Ficheros: `TEORIA.md` (fundamento), `output/CARGA.md` (carga y consistencia), `output/RESULTADOS.md` (todas las tablas).
