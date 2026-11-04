# Informe de auditoría r2: estaciones con más error nocturno y giros de sensor

_Periodo auditado: `2025-11-01` a `2026-11-03` (contraste histórico `2020–2026`). Script de verificación: [`audit_r2.py`](audit_r2.py)._

---

## Afirmación 6 — Altarani: drenaje nocturno (90–180°) y bimodalidad cuando Tala-1 gira al oeste (104 h)

> **Afirmación escrutada:** _«Altarani: de noche el 96 % de las horas viene de 90–180° por su propia ladera, no por un fallo. Cuando de noche Tala-1 marca 230–290° (104 h), Altarani se reparte entre SE (43 %) y NO (51 %), y ningún desfase único lo predice. ¿Es el sitio o el sensor? Busca evidencia en contra: su propio pasado (2021–2025), SD1, velocidad, saltos, otras vecinas.»_

### Veredicto: **PARCIAL**
- **Se sostiene** que en el periodo `2025-11-01` a `2026-11-03` el dominio nocturno del sector `90–180°` en Altarani (**`95.2 %`** en `22–06 h` con `WS > 1.0 m/s`; **`96.1 %`** en `23–06 h`) **es físico (del sitio, encauzamiento catabático de su valle) y no un fallo del sensor**:
  - Coincide con la topografía del valle de Altarani (el terreno sube hacia `140°` SE y se abre al NO `320°`; dirección nocturna observada `137.9°`, diurna `304.7°`).
  - La veleta muestra turbulencia natural (`WindDir_SD1_WVT` mediana de `12.8°`, IQR `10.2°–17.2°`, **`0.00 %` de horas con `SD1 < 3°`** y cambio horario mediano `|D1(t) - D1(t-1)| = 5.3°`), descartando veleta pegada.
  - Su propio pasado (`2020–2024` y `2026`) confirma entre **`91.2 %` y `96.0 %`** de horas nocturnas (`WS > 1.0 m/s`) en `90–180°`.
- **Evidencia en contra hallada en su pasado (`2025-01` a `2025-03`):** al revisar el histórico `2021–2025` mes a mes aparece **un fallo/giro temporal del sensor no documentado entre enero y marzo de 2025** (fuera de la ventana `2025-11 → 2026-11` del consenso): en febrero de 2025 el porcentaje nocturno en `90–180°` cayó a **`0.0 %`** (`63.3 %` en NO y `36.7 %` en SO, media nocturna `287.6°`, `SD1 = 7.3°`), recuperando su régimen histórico en abril de 2025 (`93.8 %` en `90–180°`). Además, entre septiembre y octubre de 2025 la media nocturna rotó ligeramente `~+13°` (de `~125°` a `~138°`), manteniéndose dentro del cuadrante SE (`90–180°`).
- **Se sostiene literalmente, pero se refuta como límite de predictibilidad de la red**, lo relativo a las **`104 h`** en que Tala-1 marca `230–290°` de noche (`22–06 h`, `WS_Altarani > 1.0 m/s` y `WS_Tala1 > 1.0 m/s`):
  - En esas `104 h` exactas, Altarani se reparte en **`43.3 %` SE (`45 h` en `90–180°`)**, **`51.0 %` NO (`53 h` en `270–360°`)** y `5.8 %` otros (`6 h`). Es matemáticamente cierto que **un desfase constante único desde Tala-1** no puede acertar una distribución bimodal separada `~180°`.
  - **Se refuta** que no existan variables en la red que predigan ese reparto: Tala-1 está en otra cuenca, pero **las vecinas de la propia cuenca de Altarani (`Alto_Quellaveco`, `Sarallenque_MQG-15-02`), `Charaque` y `Papujune`, junto con la hora de la noche**, sí discriminan cuándo el flujo del oeste penetra hasta Altarani (`NO`, con **`73.9 %–81.8 %` de precisión**) y cuándo Altarani queda desacoplada en drenaje (`SE`).

### Cifras que lo sustentan

1. **Reproducción exacta de las cifras del análisis (`2025-11-01` → `2026-11-03`):**
   - Noche `22–06 h` con `WS >= 0.5 m/s` (`N = 3 235 h`): **`91.9 %`** en `90–180°`, `5.3 %` en `270–360°`, media `138.2°` (`R = 0.853`, `SD1` mediana `13.0°`).
   - Noche `22–06 h` con `WS > 1.0 m/s` (`N = 3 029 h`): **`95.2 %`** en `90–180°`, `3.1 %` en `270–360°`, media `137.9°` (`R = 0.907`, `SD1` mediana `12.8°`).
   - Noche `23–06 h` con `WS > 1.0 m/s` (`N = 2 712 h`): **`96.1 %`** en `90–180°`.
   - Subconjunto nocturno (`22–06 h`) con `WS_Altarani > 1.0 m/s`, `WS_Tala1 > 1.0 m/s` y `D1_Tala1 ∈ [230°, 290°]`: **`N = 104 h`**, con **`45 h` (`43.3 %`) en SE (`90–180°`)**, **`53 h` (`51.0 %`) en NO (`270–360°`)** y `6 h` (`5.8 %`) en otros sectores. (Si se relaja `WS_Tala1 >= 0.5 m/s`, son `N = 163 h`: `52.8 %` SE y `39.3 %` NO).

2. **Serie histórica anual (`2020–2026`) y anomalía de enero–marzo de 2025:**

   | Año / Tramo | Noche `N` (`WS ≥ 0.5`) | `% 90–180°` (`WS ≥ 0.5`) | `% 90–180°` (`WS > 1.0`) | Dir. media Noche (`R`) | `WS` media Noche | `SD1` med. Noche | Dir. media Día (`% 250–350°`) |
   |---|---:|---:|---:|---|---:|---:|---|
   | `2020` | `456` | `93.9 %` | `96.0 %` | `141.2°` (`0.88`) | `2.81 m/s` | `13.0°` | `305.1°` (`97.8 %`) |
   | `2021` | `3 186` | `91.5 %` | `94.2 %` | `128.0°` (`0.87`) | `2.87 m/s` | `13.8°` | `296.4°` (`97.5 %`) |
   | `2022` | `3 126` | `88.6 %` | `92.1 %` | `115.4°` (`0.84`) | `3.12 m/s` | `13.2°` | `284.5°` (`96.7 %`) |
   | `2023` | `3 160` | `88.3 %` | `91.2 %` | `116.7°` (`0.84`) | `3.11 m/s` | `13.4°` | `284.9°` (`95.1 %`) |
   | `2024` | `3 193` | `91.7 %` | `94.4 %` | `125.7°` (`0.86`) | `3.01 m/s` | `13.8°` | `295.1°` (`96.9 %`) |
   | `2025` (año completo) | `3 185` | `78.1 %` | `82.4 %` | `137.1°` (`0.60`) | `2.99 m/s` | `12.0°` | `301.6°` (`98.8 %`) |
   | — _detalle `2025-02` (`WS > 1`)_ | `169` | — | **`0.0 %`** | **`287.6°` (`0.89`)** | `1.99 m/s` | **`7.3°`** | _anomalía de sensor ene–mar 2025_ |
   | — _detalle `2025-04 → 12` (`WS > 1`)_ | `2 402` | — | **`96.3 %`** | `131.5°` (`0.94`) | `3.42 m/s` | `12.2°` | _régimen normal restaurado_ |
   | `2026` (hasta `03-nov`) | `2 701` | `91.5 %` | `94.9 %` | `137.2°` (`0.85`) | `3.06 m/s` | `13.5°` | `304.7°` (`96.6 %`) |

3. **Qué predice si Altarani va a `NO` (`53 h`) o se queda en `SE` (`45 h`) durante las `104 h` en que Tala-1 marca `230–290°`:**
   - **Condicionamiento por otras vecinas (si la vecina también registra flujo del oeste-noroeste `240–360°`):**

     | Vecina condicionante en `240–360°` | Cuando la vecina SÍ está en `240–360°` (`n`) | Cuando la vecina NO está en `240–360°` (`n`) | Exactitud de separación `NO` vs `SE` (sobre `98 h` bimodales) |
     |---|---|---|---|
     | **`Charaque`** | **`80.0 % NO`** (`32 NO`, `7 SE`, `1 Otro`) | **`59.4 % SE`** (`38 SE`, `21 NO`, `5 Otro`) | **`71.4 %`** (`70 / 98`) |
     | **`Alto_Quellaveco`** (misma cuenca, arriba) | **`81.8 % NO`** (`18 NO`, `4 SE`, `0 Otro`) | **`50.0 % SE`** (`41 SE`, `35 NO`, `6 Otro`) | **`60.2 %`** (`59 / 98`; precisión `NO = 81.8 %`) |
     | **`Papujune`** | **`76.5 % NO`** (`26 NO`, `7 SE`, `1 Otro`) | **`54.3 % SE`** (`38 SE`, `27 NO`, `5 Otro`) | **`65.3 %`** (`64 / 98`) |
     | **`Sarallenque_MQG-15-02`** (misma cuenca, 2.6 km) | **`73.9 % NO`** (`17 NO`, `6 SE`, `0 Otro`) | **`48.1 % SE`** (`39 SE`, `36 NO`, `6 Otro`) | **`57.1 %`** (`56 / 98`; precisión `NO = 73.9 %`) |

   - **Condicionamiento por la hora de la noche y por velocidad/turbulencia:**
     - **Inicio de la noche (`22–23 h`, `n = 45 h`):** domina el **`NO` con `62.2 %` (`28 h`)** frente a `28.9 %` SE (`13 h`), porque el flujo diurno valle arriba persiste al anochecer antes de establecerse la inversión térmica.
     - **Madrugada (`00–06 h`, `n = 59 h`):** se invierte el dominio hacia el **`SE` con `54.2 %` (`32 h`)** frente a `42.4 %` NO (`25 h`).
     - **Intensidad del viento en la red y turbulencia local:** cuando el flujo del oeste logra penetrar hasta Altarani (`NO`), `Tala-1` sopla más fuerte (`1.99` vs `1.46 m/s`), `Charaque` sopla más fuerte (`1.78` vs `1.35 m/s`), `Sarallenque_MQG` alcanza `3.33` vs `2.68 m/s`, y la turbulencia `SD1` en Altarani es mucho menor (`mediana 20.1°` en `NO` frente a `30.5°` cuando queda en `SE`).

### Explicación
Altarani está encajonada en el fondo del valle del río Asana/Sarallenque (`3 210 m`), cuya pendiente drena de forma casi ininterrumpida desde el sureste (`138°`) durante la noche. No hay ningún fallo de sensor en el periodo del consenso (`nov 2025 – nov 2026`). Cuando `Tala-1` (en la cuenca vecina y más expuesta) gira al oeste de noche (`104 h`), ese dato aislado es ambiguo porque a veces es una brisa local que no rompe la piscina de aire frío del fondo de Altarani (`SE`) y otras veces un flujo de escala mayor o de primera hora de la noche (`22–23 h`) que barre ambas cuencas (`NO`). Sin embargo, al comprobar si `Charaque`, `Alto_Quellaveco` o `Papujune` también están en el sector oeste (`240–360°`), el `76.5–81.8 %` de esos casos corresponden a `NO` en Altarani: lo que falla es predecir mediante un desfase estático por vecina, no la información física de la red.

---

## Afirmación 7 — Cortadera: abanico nocturno (0°–135°) y predicción de la posición dentro del abanico

> **Afirmación escrutada:** _«Cortadera: de noche su viento se abre en abanico de 0° a 135°; las vecinas indican "noche de drenaje" pero no la posición dentro del abanico, y la calibración apunta al centro (~100°): de ahí 50–60° de error con norte. ¿Hay alguna variable (velocidad, hora, SD1, otra vecina) que sí indique la posición en el abanico?»_

### Veredicto: **PARCIAL**
- **Se sostiene** la descripción física del abanico nocturno y el mecanismo por el cual la calibración univariante por sectores (`consensus_diagnosis.py --limpio`) colapsa hacia el centro-este del abanico (`85.9°` de media, mediana `91.3°`, IQR `87.3°–93.9°`), generando **`54.0°` de error medio** cuando Cortadera entra de noche en el sector norte (`|D1| ≤ 45°`).
- **Se refuta** que ninguna variable ni vecina indique la posición dentro del abanico:
  1. Entre las variables locales de Cortadera, la dispersión intrahoraria **`WindDir_SD1_WVT`** tiene una correlación fuerte con el ángulo dentro del abanico (`Pearson r = -0.455`, `Spearman ρ = -0.563`), y la persistencia horaria `D1(t-1)` alcanza `r = +0.649` (`MAE_norte = 29.0°`).
  2. Entre las vecinas individuales, **`Minas_Sur`** correlaciona con la posición dentro del abanico (`r = +0.52` con `sin(dir)` y `r = -0.48` con `cos(dir)`), bajando por sí sola el error nocturno en norte a **`40.8°`** (frente a `55.7°–66.7°` del resto de vecinas).
  3. Combinando de forma no lineal los vectores y velocidades de las vecinas (`HistGradientBoostingRegressor` entrenado en semanas pares y evaluado en semanas impares), **las propias vecinas explican el `60.3 %` de la varianza (`R² = 0.603`) dentro del abanico nocturno**, reduciendo el error global del abanico de `16.9°` a **`11.2°`** y el error en horas del norte de **`54.0°` a `29.8°`** (y hasta **`R² = 0.693`, `MAE_abanico = 9.4°`, `MAE_norte = 26.8°`** al añadir `SD1`, `WS`, hora de la noche y día del año).

### Cifras que lo sustentan

1. **Estructura real del abanico nocturno (`22–06 h`, `WS > 1.0 m/s`, antes del giro del `2026-09-13 11:00`, `N = 2 416 h`):**
   El `90.5 %` (`2 187 h`) cae entre `0°` y `135°` (`91.2 %` entre `345°` y `135°`), con dirección circular media de `89.6°` (`R = 0.750`), pero con una fuerte asimetría física hacia el E–SE:

   | Sector en Cortadera (noche) | % de horas (`n`) | `WS_ms_Avg` media | `WindDir_SD1_WVT` media | `|WindDir_Avg - D1|` medio | Régimen físico |
   |---|---:|---:|---:|---:|---|
   | `315–360°` (NO–N) | `2.0 %` (`48`) | `3.08 m/s` | `39.1°` | `99.2°` | Cruce por `0°/360°`, muy turbulento |
   | `0–45°` (N–NE) | `7.9 %` (`190`) | `2.79 m/s` | `27.2°` | `55.3°` | Borde norte del abanico, alta `SD1` |
   | `45–90°` (NE–E) | `18.0 %` (`435`) | `2.27 m/s` | `24.5°` | `9.4°` | Transición interna del abanico (mínimo de `WS`) |
   | `90–135°` (E–SE) | `64.7 %` (`1 562`) | `2.83 m/s` | `11.4°` | `0.9°` | Modo principal de drenaje, flujo laminar |
   | `135–225°` (S) | `0.4 %` (`9`) | `2.42 m/s` | `54.6°` | `10.6°` | Residual |
   | `225–315°` (O) | `7.1 %` (`172`) | `1.64 m/s` | `32.4°` | `16.8°` | Cola del régimen diurno del oeste |

   El histórico `2020–2026` confirma que este reparto es propio del emplazamiento actual de Cortadera desde septiembre de 2022 (`2023–2026`: `89.4–90.3 %` de las noches en `0–135°`, `55.7–65.3 %` en `90–135°`, `6.2–10.9 %` en norte `≤ 45°`, dirección media `85.3–90.4°`). Antes de la reubicación de septiembre de 2022 (`2020–2021`), el `83.6–83.7 %` caía en `45–90°` (media `66.6–72.0°`).

2. **Por qué la calibración actual da `54.0°` de error con norte:**
   En las semanas impares de prueba (`N = 1 216 h` nocturnas), cada vecina pasa casi toda la noche en su propio sector de drenaje y su desfase calibrado apunta a la media circular de Cortadera (`~86–95°`). Al promediar todas las vecinas con pesos fijos `1/e²`, el consenso predice una dirección nocturna casi constante: media `85.9°`, mediana `91.3°`, IQR `87.3°–93.9°` (error global nocturno `22.8°`). En las `138` horas nocturnas de prueba en que Cortadera está en el sector norte (`|D1| ≤ 45°`, media real `18.4°`), el consenso predice `71.7°` de media, arrojando un error medio de **`54.0°`**.

3. **Variables que sí predicen la posición dentro del abanico (`[-30°, 150°]`, `N = 2 213 h`):**
   - **Correlaciones univariantes con el ángulo dentro del abanico (`y_fan`):**
     - `WindDir_SD1_WVT` propia: **`Pearson r = -0.455`**, **`Spearman ρ = -0.563`** (a menor ángulo —más cerca del norte—, mucha mayor turbulencia intrahoraria).
     - `WS_ms_Avg` propia: `Pearson r = +0.105`, `Spearman ρ = +0.302` (relación no monótona: mínimo en `45–90°` con `2.27 m/s`).
     - Hora de la noche (`0..8` desde las `22 h`): `Pearson r = +0.202`, `Spearman ρ = +0.183` (el norte es más frecuente entre `22` y `00 h` y decae en la madrugada).
     - Mes del año: `Pearson r = +0.109`, `Spearman ρ = +0.152` (mayor proporción de norte entre mayo y agosto).
   - **Vecinas individuales y modelo multivariante (entrenamiento en semanas pares, evaluación en semanas impares sobre el abanico nocturno):**

     | Predictor / Modelo (evaluado en semanas impares) | `R²` test (abanico) | `MAE` abanico (`°`) | `MAE` norte `≤ 45°` (`°`) | Correlación `(sin, cos, ws)` con ángulo en abanico |
     |---|---:|---:|---:|---|
     | Constante en la mediana (`99.5°`) | `-0.158` | `16.9°` | `64.5°` | — |
     | Consenso por pares actual (`consensus_diagnosis.py`) | — | `18.5°` | `54.0°` | — |
     | Vecina individual: `Calientes1` (calibración 22.5°) | — | `18.5°` | `62.7°` | `(+0.34, +0.10, +0.19)` |
     | Vecina individual: `Tala-1` (calibración 22.5°) | — | `17.6°` | `59.4°` | `(+0.30, +0.04, +0.24)` |
     | Vecina individual: `Alto_Tala` (calibración 22.5°) | — | `15.7°` | `58.1°` | `(+0.21, +0.33, +0.22)` |
     | Vecina individual: `Apacheta` (calibración 22.5°) | — | `18.7°` | `55.7°` | `(+0.40, -0.01, -0.17)` |
     | Vecina individual: **`Minas_Sur`** (calibración 22.5°) | — | **`16.0°`** | **`40.8°`** | **`(+0.52, -0.48, -0.21)`** |
     | Persistencia temporal `D1(t - 1)` | — | `14.3°` | `29.0°` | `r = +0.649` |
     | **HGBR: solo vecinas (`u, w, ws` de 10 vecinas)** | **`+0.603`** | **`11.2°`** | **`29.8°`** | — |
     | **HGBR: vecinas + `hora` + `WS` y `SD1` propias** | **`+0.671`** | **`9.9°`** | **`28.2°`** | — |
     | **HGBR: vecinas + `hora` + `WS`/`SD1` + `DOY`** | **`+0.693`** | **`9.4°`** | **`26.8°`** | — |

### Explicación
El problema en Cortadera de noche no es una ausencia total de señal en la red, sino una limitación del estimador aditivo por pares: como la distribución nocturna de Cortadera está muy sesgada hacia `90–135°` (`64.7 %` de las horas), cualquier media ponderada de desfases univariantes por sector de `22.5°` encoge la predicción hacia `~90°`. Cuando se utilizan conjuntamente la dirección y la velocidad de las vecinas (`Minas_Sur`, `Apacheta`, `Calientes1`, `Alto_Tala`, `Tala-1`) junto con la firma de turbulencia (`SD1`) y la hora nocturna, sí se distingue si Cortadera está en el borde norte (`0–45°`) o en el drenaje laminar del sureste (`90–135°`), reduciendo el error nocturno con norte a la mitad (`54.0° → 26.8°–29.8°`).

---

## Afirmación 8 — Camp_Quellaveco: ¿su error nocturno se debe al 54 % de calmas y al fallo del 2026-09-10?

> **Afirmación escrutada:** _«Camp_Quellaveco: su error nocturno es del sensor (reubicación de 2022 a un sitio resguardado, 54 % de calmas nocturnas, anemómetro que no arranca tras la calibración del 2026-09-10), no del método.»_

### Veredicto: **PARCIAL (refutada la atribución a las calmas y a la calibración del 2026-09-10)**
- **Se sostiene** que desde la reubicación del `2022-10-06` la estación quedó en un emplazamiento resguardado de noche (con `54.3 %` de calmas `< 0.5 m/s` en `2025–2026`) y que tras la calibración del `2026-09-10` el anemómetro presenta un fallo de arranque (`25.5 %` de las horas nocturnas en `0.00 m/s` exacto entre el `10-sep` y el `03-nov`, frente a `1.6 %` antes).
- **Se refuta** que el `54 %` de calmas nocturnas o el anemómetro que no arranca tras el `2026-09-10` expliquen el error nocturno (`30.8°`) o el error en norte (`41.1°–41.2°`) reportados para el consenso:
  1. **El protocolo de evaluación (`consensus_diagnosis.py` y `consensus_pairs.py`) filtra de entrada `WS_ms_Avg > 1.0 m/s` en la estación evaluada.** Por consiguiente, **el `100 %` de las horas en calma (`< 0.5 m/s`), el `100 %` de las horas con el anemómetro parado en `0.00 m/s` tras el `2026-09-10` y el `100 %` de las horas de umbral (`0.5–1.0 m/s`) ya están fuera del cálculo del error**. En las `289` horas nocturnas de prueba evaluadas, el anemómetro está girando siempre a más de `1.0 m/s`.
  2. **Excluir todo el tramo posterior al `2026-09-10` deja el error prácticamente intacto:** antes del `2026-09-10` el error nocturno del consenso ya era de **`29.4°`** (`N = 267 h` de prueba con `WS > 1.0 m/s`, frente a `30.8°` en todo el año) y el error en el sector norte era de **`41.5°`** (`N = 107 h`, frente a `41.2°` sobre `N = 108 h` en todo el año). Después del `2026-09-10` solo hubo **1 hora** del sector norte con `WS > 1.0 m/s` en semanas impares.

### Cifras que lo sustentan

1. **Partición de las horas nocturnas (`22–06 h`) en Camp_Quellaveco y efecto del corte `WS > 1.0 m/s`:**

   | Periodo | Noche total (`N`) | `WS == 0.00` | `WS < 0.5 m/s` (calma) | `0.5 ≤ WS ≤ 1.0 m/s` | `WS > 1.0 m/s` (evaluadas) | Error consenso Noche (`WS > 1`, test) | Error consenso Transición (`WS > 1`, test) | Error consenso Norte `≤ 45°` (`WS > 1`, test) |
   |---|---:|---:|---:|---:|---:|---:|---:|---:|
   | **Todo el año** (`2025-11-01` → `2026-11-03`) | `3 295` | `5.2 %` (`170`) | `54.3 %` (`1 790`) | `28.8 %` (`948`) | **`16.9 %` (`557`)** | **`30.8°`** (`N = 289`) | **`23.6°`** (`N = 740`) | **`41.2°`** (`N = 108`) |
   | **Antes de calibración** (`< 2026-09-10`) | `2 800` | `1.6 %` (`45`) | `49.7 %` (`1 391`) | `31.4 %` (`880`) | **`18.9 %` (`529`)** | **`29.4°`** (`N = 267`) | **`24.0°`** (`N = 631`) | **`41.5°`** (`N = 107`) |
   | **Tras calibración** (`≥ 2026-09-10`) | `495` | `25.5 %` (`126`) | `80.4 %` (`398`) | `13.9 %` (`69`) | **`5.7 %` (`28`)** | **`48.0°`** (`N = 22`) | **`21.7°`** (`N = 109`) | **`15.3°`** (`N = 1`) |

2. **Dónde se produce realmente el error del sector norte (`N = 108 h` de prueba con `WS > 1.0 m/s`):**
   - **Transición (`07–09 h` y `18–21 h`):** concentra el **`61.1 %` (`66 / 108 h`)** de los casos del norte, con un error medio del consenso de **`41.3°`**, velocidad media baja (`1.42 m/s`) y alta dispersión intrahoraria (`SD1 = 44.4°`).
   - **Noche (`22–06 h`):** representa el **`25.0 %` (`27 / 108 h`)**, con error medio de **`31.0°`** (`WS = 1.53 m/s`, `SD1 = 40.5°`).
   - **Día (`10–17 h`):** representa el **`13.9 %` (`15 / 108 h`)**, con error medio de **`59.4°`** (`WS = 1.97 m/s`, `SD1 = 63.2°`).

3. **Evidencia histórica (`2020–2026`) en horas nocturnas activas (`WS > 1.0 m/s`):**
   Incluso restringiendo el análisis a las noches en que el viento supera `1.0 m/s` (donde el anemómetro no está detenido por rozamiento), la reubicación del `2022-10-06` cambió radicalmente el régimen físico del punto:

   | Tramo histórico (noche `22–06 h`) | % noches con `WS < 0.5` | % noches con `WS > 1.0` (`n`) | Dirección media (`WS > 1.0`) | Constancia `R` (`WS > 1.0`) | `SD1` media (`WS > 1.0`) |
   |---|---:|---:|---:|---:|---:|
   | `2020` (pre-reubicación) | `22.9 %` | `61.6 %` (`1 820`) | `86.1°` (E) | **`0.92`** | `15.1°` |
   | `2021` (pre-reubicación) | `5.8 %` | `75.8 %` (`2 490`) | `82.5°` (E) | **`0.87`** | `19.7°` |
   | `2022` hasta `2022-10-05` | `3.3 %` | `79.2 %` (`1 977`) | `79.6°` (E) | **`0.84`** | `21.8°` |
   | `2022` desde `2022-10-06` | `36.0 %` | `19.4 %` (`152`) | `283.1°` | **`0.20`** | `35.3°` |
   | `2023` (post-reubicación) | `42.7 %` | `26.3 %` (`864`) | `175.9°` | **`0.05`** | `33.3°` |
   | `2024` (post-reubicación) | `55.5 %` | `18.7 %` (`616`) | `4.9°` | **`0.18`** | `30.8°` |
   | `2025` (post-reubicación) | `40.0 %` | `22.3 %` (`729`) | `300.2°` | **`0.16`** | `30.1°` |
   | `2026` (post-reubicación) | `54.7 %` | `18.0 %` (`495`) | `303.3°` | **`0.16`** | `30.8°` |

### Explicación
El análisis original mezcla dos fenómenos distintos: por un lado, el fallo mecánico/de umbral del anemómetro en viento débil (`< 0.5 m/s`, agravado el `2026-09-10` con horas en `0.00 m/s`); por otro, el error del consenso evaluado exclusivamente en horas con **`WS > 1.0 m/s`**. En esas horas con `WS > 1.0 m/s` el anemómetro sí se mueve, pero desde la reubicación de octubre de 2022 la estación está dentro de una zona abrigada donde el flujo nocturno y de transición que supera `1 m/s` es turbulento (`SD1 ~ 31–44°`), carece de dirección dominante (`R = 0.05–0.20`, repartido en los cuatro cuadrantes: `17.8 %` NE, `17.6 %` SE, `28.5 %` SO, `36.1 %` NO) y está físicamente desacoplado del drenaje laminar NE–E de `Chancado_primario` y `Tala-1`. Por tanto, en las horas evaluadas (`WS > 1.0 m/s`) el error no proviene del fallo del `2026-09-10` ni de las calmas, sino del **desacople topográfico local del nuevo sitio** en noche y transición.

---
## Afirmación 9 — Giros del sensor en Cortadera (2026-09-13) y Alto_Quellaveco (2026-09-15)

> **Afirmación escrutada:** _«Cortadera (desde 2026-09-13) y Alto_Quellaveco (desde 2026-09-15) giraron el sensor: de día ~280° → ~200° y ~326° → ~220°. ¿Podría ser estacional o un fallo de la vecina de referencia? Compara con el mismo periodo de años anteriores y con varias vecinas; estima el ángulo del giro y si es igual de día y de noche. Para el punto 9, deja el ángulo estimado y la fecha y hora de inicio que mejor encajan.»_

### Veredicto: **SE SOSTIENE**
Ambos cambios son **giros físicos del sensor producidos durante intervenciones de campo a mediodía** (con desconexión horaria en la base), **no son estacionales**, **no se deben a fallos de la vecina de referencia** y **tienen el mismo ángulo de giro de día y de noche** una vez descontada la deriva estacional común con las vecinas de control.

### Resumen ejecutivo: fecha/hora de inicio y ángulo de giro estimado

| Estación | Hueco de intervención en la base (`NULL`) | Fecha y hora de inicio para exclusión | Inicio del tramo girado estable | Ángulo de giro estimado (`Después - Antes`) | Corrección para restituir la serie | ¿Igual de día y de noche? |
|---|---|---|---|---|---|---|
| **Cortadera** | `2026-09-13 11:00` y `12:00` (2 h sin registro) | **`2026-09-13 11:00`** | **`2026-09-13 13:00`** (`14:00` sin la hora de reconexión) | **`-73° ± 4°`** (antihorario) | **`+73°` (mód. 360°)** | **Sí:** relativo a `Calientes1` es **`-74.6°` de día**, **`-71.4°` de noche** y **`-73.1°` en 24 h** (`-69.0°` a `-83.1°` en los 12 bloques de 2 h) |
| **Alto_Quellaveco** | `2026-09-15 11:00` (1 h sin registro) | **`2026-09-15 11:00`** | **`2026-09-15 12:00`** (`13:00` sin la hora de reconexión) | **`-88° ± 5°`** (antihorario, `~1/4` de vuelta) | **`+88°` (mód. 360°)** | **Sí:** por correlación de histogramas es **`-86°` de día** y **`-88°` de noche**; relativo a `Minas_Sur` es **`-84.6°` de día**, **`-94.3°` de noche** y **`-88.2°` en 24 h** (relativo a `Papujune`: **`-92.1°` día**, **`-86.1°` noche**, **`-88.9°` 24 h**) |

### Cifras que lo sustentan

1. **Firma horaria exacta del inicio del giro (huecos de visita de campo a mediodía):**
   - **Cortadera (`2026-09-13`):**
     - `09:00`: `344.3°` (`WS = 4.65 m/s`, `Δ[Cortadera - Calientes1] = +65.9°`).
     - `10:00`: `320.9°` (`WS = 5.78 m/s`, `Δ[Cortadera - Calientes1] = +56.0°`).
     - **`11:00` y `12:00`: `NULL`** en `Cortadera` (mientras `Calientes1` registra `265.5°` y `266.3°`).
     - **`13:00`:** reaparece con `228.3°` (`WS = 7.48 m/s`, `SD1 = 36.9°`, `Δ = -36.8°`).
     - **`14:00` a `18:00`:** ya estabilizada en `198.2°–210.8°` (`WS = 3.99–7.14 m/s`, `SD1 = 14.7–18.2°`, `Δ[Cortadera - Calientes1] = -56.2°` a `-70.2°`).
     - **`22:00` a `03:00` (primera noche):** marca `335.1°–354.4°` mientras `Calientes1` marca `96.5°–104.6°` (`Δ = -108.3°` a `-127.8°`, frente a `-47.6°` a `-70.2°` la noche anterior).
   - **Alto_Quellaveco (`2026-09-15`):**
     - `09:00`: `335.5°` (`WS = 2.96 m/s`, `Δ[Alto_Quellaveco - Minas_Sur] = +35.3°`).
     - `10:00`: `339.5°` (`WS = 2.54 m/s`, `Δ[Alto_Quellaveco - Minas_Sur] = +46.1°`).
     - **`11:00`: `NULL`** en `Alto_Quellaveco` (mientras `Minas_Sur` registra `308.5°`).
     - **`12:00`:** reaparece con `227.2°` (`WS = 4.43 m/s`, `SD1 = 59.3°`, `Δ = -69.3°`).
     - **`13:00` a `18:00`:** estabilizada en `182.1°–209.9°` (`WS = 3.29–5.54 m/s`, `SD1 = 11.0–29.9°`, `Δ[Alto_Quellaveco - Minas_Sur] = -70.6°` a `-96.3°`).
     - **`22:00` a `06:00` (primera noche):** la diferencia con `Minas_Sur` pasa a `-35.3°` a `-91.8°` (la noche anterior era `-22.4°` a `+4.6°`).

2. **Descarte de efecto estacional — comparación multianual del mismo periodo del año (`15 Sep – 03 Nov`, `DOY 258–307`, `2020–2026`, `WS ≥ 0.5 m/s`):**

   | Año (`15 Sep – 03 Nov`) | `Cortadera` Día (`R`) | `Cortadera` Noche (`R`) | `Calientes1` Día / Noche | `Alto_Quellaveco` Día (`R`) | `Alto_Quellaveco` Noche (`R`) | `Minas_Sur` Día / Noche |
   |---|---|---|---|---|---|---|
   | `2020` | `224.0°` (`0.98`) | `65.2°` (`0.88`) | `305.1°` / `123.9°` | `279.3°` (`0.76`) | `87.6°` (`0.45`) | — |
   | `2021` | `230.7°` (`0.98`) | `75.1°` (`0.89`) | `318.6°` / `140.5°` | `262.2°` (`0.81`) | `94.6°` (`0.55`) | `288.0°` / `136.6°` |
   | `2022` | `252.5°` (`0.99`) | `86.5°` (`0.91`) | `285.2°` / `108.4°` | `281.6°` (`0.89`) | `33.3°` (`0.55`) | `280.3°` / `126.8°` |
   | `2023` | `260.8°` (`0.93`) | `95.4°` (`0.77`) | `307.5°` / `137.8°` | `269.5°` (`0.75`) | `98.4°` (`0.41`) | `272.9°` / `209.9°` |
   | `2024` | `254.3°` (`0.99`) | `87.7°` (`0.87`) | `302.7°` / `145.7°` | `210.4°`* (`0.81`) | `42.3°`* (`0.57`) | `254.2°` / `111.5°` |
   | `2025` | `255.1°` (`0.98`) | `91.4°` (`0.91`) | `287.2°` / `126.5°` | `296.2°` (`0.81`) | `98.6°` (`0.55`) | — |
   | **`2026` (post-giro)** | **`202.5°` (`0.97`)** | **`30.2°` (`0.73`)** | **`273.6°` / `109.2°`** | **`224.9°` (`0.85`)** | **`335.9°` (`0.55`)** | **`298.0°` / `64.9°`** |

   _(*En `2024`, `Alto_Quellaveco` atravesaba otro giro previo ya documentado en `WIND_REVIEW.md` §3.B entre `2024-05` y `2025-02`; en todos los años sanos su dirección diurna en sep–oct es `262°–296°` y la nocturna `88°–99°`, jamás `336°` NO.)_

3. **Descarte de fallo en la vecina de referencia — contraste contra 6 vecinas independientes (`Antes` desde `2026-07-15` vs `Después` hasta `2026-11-03`):**

   - **Cortadera (`2026-07-15 → 2026-09-13 10:00` vs `2026-09-13 12:00 → 2026-11-03`):**
     - Propia estación: Día `277.0° → 202.8°` (**`Δ_unit = -74.2°`**, `Δ_vec = -75.0°`, giro de histograma `-61°`, coseno `0.01 → 0.78`); Noche `91.9° → 29.3°` (**`Δ_unit = -62.6°`**, `Δ_vec = -61.7°`, giro de histograma `-54°`, coseno `0.14 → 0.87`).
     - Frente a 6 vecinas (cambio en la diferencia circular hora a hora `Δ[Cortadera - vecina]`):

       | Vecina de control | Cambio propio de la vecina (Día / Noche) | `Δ(Cortadera - vecina)` Día | `Δ(Cortadera - vecina)` Noche | `Δ(Cortadera - vecina)` 24 h |
       |---|---|---:|---:|---:|
       | **`Calientes1`** | `273°→273° (+1°)` / `96°→108° (+12°)` | **`-74.6°`** | **`-71.4°`** | **`-73.1°`** |
       | **`Tala_Legal`** | `298°→293° (-5°)` / `107°→109° (+2°)` | **`-69.0°`** | **`-62.3°`** | **`-66.1°`** |
       | **`Cerro_Salviani`** | `226°→223° (-2°)` / `200°→202° (+1°)` | **`-72.4°`** | **`-81.2°`** | **`-67.4°`** |
       | **`DME3_Cortadera`** | `204°→201° (-3°)` / `94°→118° (+24°)` | **`-70.0°`** | **`-85.0°`** | **`-60.0°`** |
       | **`Apacheta`** | `241°→229° (-12°)` / `131°→132° (+2°)` | **`-62.1°`** | **`-55.9°`** | **`-56.5°`** |
       | **`Calacaja`** | `183°→195° (+12°)` / `14°→27° (+13°)` | **`-84.6°`** | **`-74.7°`** | **`-76.1°`** |
       | **Mediana 6 vecinas** | — | **`-71.2°`** | **`-73.1°`** | **`-66.8°`** |

   - **Alto_Quellaveco (`2026-07-15 → 2026-09-15 10:00` vs `2026-09-15 13:00 → 2026-11-03`):**
     - Propia estación: Día `319.3° → 224.8°` (**`Δ_unit = -94.6°`**, `Δ_vec = -96.6°`, **giro de histograma `-86°`**, coseno `0.06 → 0.95`); Noche `64.6° → 334.3°` (**`Δ_unit = -90.3°`**, `Δ_vec = -86.6°`, **giro de histograma `-88°`**, coseno `0.46 → 0.94`); 24 h: **`-100.2°`** (**giro de histograma `-86°`**, coseno `0.45 → 0.96`).
     - Frente a 6 vecinas (cambio en la diferencia circular hora a hora `Δ[Alto_Quellaveco - vecina]`):

       | Vecina de control | Cambio propio de la vecina (Día / Noche) | `Δ(Alto_Quellaveco - vecina)` Día | `Δ(Alto_Quellaveco - vecina)` Noche | `Δ(Alto_Quellaveco - vecina)` 24 h |
       |---|---|---:|---:|---:|
       | **`Minas_Sur`** | `305°→298° (-7°)` / `61°→62° (+1°)` | **`-84.6°`** | **`-94.3°`** | **`-88.2°`** |
       | **`Papujune`** | `251°→248° (-3°)` / `40°→41° (+1°)` | **`-92.1°`** | **`-86.1°`** | **`-88.9°`** |
       | **`Sarallenque_MQG-15-02`** | `252°→241° (-11°)` / `69°→78° (+9°)` | **`-83.6°`** | **`-88.9°`** | **`-84.9°`** |
       | **`Tala-1`** | `263°→252° (-11°)` / `51°→45° (-6°)` | **`-83.6°`** | **`-85.8°`** | **`-82.7°`** |
       | **`Altarani`** | `307°→293° (-13°)` / `138°→130° (-9°)` | **`-79.9°`** | **`-84.6°`** | **`-76.0°`** |
       | **`Cerro_Salviani`** | `226°→223° (-2°)` / `201°→200° (-1°)` | **`-92.5°`** | `-61.0°` | **`-88.6°`** |
       | **Mediana 6 vecinas** | — | **`-84.1°`** | **`-86.0°`** | **`-86.6°`** |

4. **Comprobación bloque a bloque (cada 2 horas, `00–23 h`) de que el giro es igual de día y de noche:**

   | Bloque horario | `Cortadera`: `Antes → Después` (`Δ_abs`) | `Δ_rel(Cortadera - Calientes1)` | `Alto_Quellaveco`: `Antes → Después` (`Δ_abs`) | `Δ_rel(Alto_Quellaveco - Minas_Sur)` |
   |---|---:|---:|---:|---:|
   | `00–01 h` | `93.1° → 27.8°` (`-65.3°`) | **`-70.8°`** | `69.7° → 324.9°` (`-104.8°`) | **`-99.9°`** |
   | `02–03 h` | `94.1° → 31.7°` (`-62.4°`) | **`-72.0°`** | `60.8° → 333.1°` (`-87.7°`) | **`-90.9°`** |
   | `04–05 h` | `93.1° → 36.6°` (`-56.5°`) | **`-69.1°`** | `58.3° → 334.1°` (`-84.2°`) | **`-92.6°`** |
   | `06–07 h` | `93.5° → 35.1°` (`-58.3°`) | **`-71.3°`** | `62.3° → 323.0°` (`-99.3°`) | **`-91.8°`** |
   | `08–09 h` | `19.3° → 212.0°` (`-167.3°`) | **`-75.3°`** | `0.9° → 234.6°` (`-126.3°`) | **`-96.6°`** |
   | `10–11 h` | `281.0° → 204.4°` (`-76.6°`) | **`-76.5°`** | `321.5° → 231.0°` (`-90.5°`) | **`-86.3°`** |
   | `12–13 h` | `272.5° → 200.6°` (`-71.9°`) | **`-72.5°`** | `322.4° → 227.2°` (`-95.2°`) | **`-88.5°`** |
   | `14–15 h` | `271.9° → 200.9°` (`-71.0°`) | **`-70.3°`** | `319.3° → 227.2°` (`-92.2°`) | **`-83.8°`** |
   | `16–17 h` | `282.3° → 205.3°` (`-77.1°`) | **`-79.3°`** | `313.6° → 220.1°` (`-93.6°`) | **`-79.4°`** |
   | `18–19 h` | `328.3° → 223.6°` (`-104.7°`) | **`-83.1°`** | `336.4° → 225.6°` (`-110.8°`) | **`-72.0°`** |
   | `20–21 h` | `57.8° → 309.2°` (`-108.6°`) | **`-69.0°`** | `55.0° → 317.9°` (`-97.1°`) | **`-87.1°`** |
   | `22–23 h` | `85.9° → 12.5°` (`-73.4°`) | **`-75.0°`** | `74.9° → 338.3°` (`-96.6°`) | **`-92.3°`** |
   | **Media / Mediana 12 bloques** | — | **`-73.7°` / `-72.3°`** (`σ = 4.1°`) | — | **`-88.4°` / `-89.7°`** (`σ = 7.5°`) |

### Explicación
En ambas estaciones la evidencia cumple todos los criterios de un **giro rígido de orientación del sensor (criterios E y F de `WIND_REVIEW.md`)** sin cambio de exposición ni de velocidad:
1. En **Cortadera**, la desconexión del **`2026-09-13` entre las `11:00` y las `12:00`** marca el instante exacto de la visita. La diferencia bruta entre día (`-74.2°`) y noche (`-62.6°`) se debe únicamente a que en la transición estacional de julio-agosto a septiembre-octubre el flujo nocturno regional en el sector Sur rotó `+12°` (visible en `Calientes1`: `96° → 108°` de noche y `+1°` de día). Al referenciar Cortadera a `Calientes1`, el salto es un giro rígido puro de **`-73° ± 4°`** en los 12 bloques de 2 horas del día (incluidas las transiciones `08–09 h` y `20–21 h`, donde el salto bruto aparentaba `-167°` y `-109°` por el adelanto estacional del ciclo solar, pero `Δ_rel` da `-75.3°` y `-69.0°`).
2. En **Alto_Quellaveco**, la desconexión del **`2026-09-15` a las `11:00`** marca el inicio del giro. Tanto la correlación circular de histogramas (`-86°` de día, `-88°` de noche, `-86°` en 24 h, subiendo la similitud coseno de `0.06–0.46` a `0.94–0.96`) como la diferencia hora a hora frente a `Minas_Sur` (`-88.2°` en 24 h), `Papujune` (`-88.9°`), `Sarallenque_MQG` (`-84.9°`) y `Tala-1` (`-82.7°`) coinciden en un giro antihorario de **`-88° ± 5°`** (prácticamente un cuarto de vuelta, `-90°`), idéntico de día y de noche.
