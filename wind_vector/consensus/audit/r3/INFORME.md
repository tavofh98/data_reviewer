# Informe de auditoría r3: ¿Sirve el consenso de vecinas para detectar las mezclas del norte en 5 min?

**Afirmación escrutada (n.º 10):**
> *«El consenso de vecinas no sirve como sustituto de la dirección, pero sí como información de régimen para que el clasificador distinga una mezcla del norte de un viento real que da el mismo A. Ejemplo: de noche en Cortadera nunca sopla del oeste, así que un A de ~240° con régimen de drenaje tiene que ser una mezcla.»*

---

## 1. Planteamiento y protocolo de evaluación

- **Datos utilizados:** ficheros alineados `explorar_qaqc/data/aligned_<estación>.csv.gz` (registros de 5 min `m01..m12` y verdad horaria `WindDir_D1_WVT_h`) para **Cortadera**, **Papujune** y **Tala-1**, cruzados con el consenso horario por pares (`consensus_pairs.py --limpio`) calculado desde `database_duck/anglo_ambiental.db` en el periodo `2025-11-01` → `2026-11-03` con todas las exclusiones del contexto (`Cortadera` desde `2026-09-13 11:00`, `Alto_Quellaveco` desde `2026-09-15 11:00`, `Alto_Tala` `2026-08-18 05:00` → `2026-09-23 15:00`, `Sarallenque` hasta `2026-09-25 20:00`, tramos congelados de `Charaque` y `Sarallenque_MQG-15-02`, estaciones descartadas y horas con `< 0.5 m/s`).
- **Zona ambigua evaluada (Punto 1):** registros de 5 min con viento (`WS_ms_Avg > 0`) cuyo promedio aritmético `A = WindDir_Avg` cae en `[150°, 300°]`.
  - **H1 (mezcla del norte):** `D1` de 5 min a `≤ 45°` del norte.
  - **H0 (viento real fuera del norte):** `D1` de 5 min a `≥ 90°` del norte.
- **Partición de validación:** ajuste del consenso por pares y de los clasificadores en **semanas pares** (`week == 0`) y evaluación fuera de muestra en **semanas impares** (`week == 1`), además de validación cruzada entre estaciones (**LOSO**: entrenar en dos estaciones y evaluar en la tercera).

---

## 2. Punto 1: Capacidad del consenso horario para separar H1 de H0 en la zona ambigua (`A ∈ [150°, 300°]`)

### 2.1. Conteos y AUC del consenso por pares

En los registros de 5 min con `A ∈ [150°, 300°]`, la proporción de mezclas del norte (`H1: D1 ≤ 45°` frente a `H0: D1 ≥ 90°`) es minoritaria: **6.4 %** en Cortadera, **8.6 %** en Papujune y **2.9 %** en Tala-1 (semanas impares de prueba). Se evalúan tres puntuaciones derivadas del consenso horario por pares (`comb`, calibrado en semanas pares con las exclusiones de `CONTEXTO.md`):
- `-dn_cons = -|comb - 0°|`: cercanía angular del consenso al norte.
- `dcos_cons = cos(μ - comb) - cos(A - comb)`: consistencia direccional del candidato de mezcla `μ` frente a `A` respecto al consenso.
- `|A - comb|`: discrepancia angular entre el promedio aritmético de 5 min y el consenso horario.

| Estación | Muestra | `N` (`A ∈ [150°, 300°]`) | `N_H1` (`D1 ≤ 45°`) | `N_H0` (`D1 ≥ 90°`) | `N` intermedio (`45–90°`) | `% H1` (`H1/(H1+H0)`) | AUC (`-dn_cons`) | AUC (`dcos_cons`) | AUC (`\|A - cons\|`) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Cortadera** | Semanas impares (prueba) | 21 870 | 1 074 | 15 820 | 4 976 | 6.4 % | **0.898** | **0.923** | 0.895 |
| Cortadera | Todas las semanas | 45 353 | 2 072 | 32 743 | 10 538 | 6.0 % | 0.893 | 0.916 | 0.886 |
| **Papujune** | Semanas impares (prueba) | 25 533 | 1 978 | 20 959 | 2 596 | 8.6 % | **0.927** | **0.924** | 0.888 |
| Papujune | Todas las semanas | 51 943 | 3 982 | 43 170 | 4 791 | 8.4 % | 0.933 | 0.930 | 0.897 |
| **Tala-1** | Semanas impares (prueba) | 26 144 | 648 | 21 928 | 3 568 | 2.9 % | **0.911** | **0.946** | 0.946 |
| Tala-1 | Todas las semanas | 53 940 | 1 280 | 45 372 | 7 288 | 2.7 % | 0.910 | 0.946 | 0.946 |

### 2.2. Razones de verosimilitud (`LR = P(condición | H1) / P(condición | H0)`) en semanas de prueba

| Estación | Condición del consenso horario (`dn_cons = \|comb - 0°\|`) | `N` (en `H1 ∪ H0`) | `P(cond \| H1)` | `P(cond \| H0)` | `LR = P(cond\|H1)/P(cond\|H0)` | Probabilidad a posteriori `P(H1 \| cond)` |
|---|---|---:|---:|---:|---:|---:|
| **Cortadera** | Cerca del norte (`≤ 45°`) | 1 009 | 28.8 % | 4.4 % | **6.50** | 30.6 % |
| Cortadera | Mitad norte (`≤ 60°`) | 1 492 | 46.2 % | 6.3 % | **7.34** | 33.2 % |
| Cortadera | Moderado (`45° – 90°`) | 4 004 | 61.7 % | 21.1 % | **2.92** | 16.6 % |
| Cortadera | Lejos del norte (`≥ 90°`) | 11 881 | 9.5 % | 74.5 % | **0.13** | 0.9 % |
| **Papujune** | Cerca del norte (`≤ 45°`) | 2 142 | 64.9 % | 4.1 % | **15.83** | 59.9 % |
| Papujune | Mitad norte (`≤ 60°`) | 3 224 | 77.9 % | 8.0 % | **9.70** | 47.8 % |
| Papujune | Moderado (`45° – 90°`) | 1 919 | 20.9 % | 7.2 % | **2.91** | 21.5 % |
| Papujune | Lejos del norte (`≥ 90°`) | 18 876 | 14.3 % | 88.7 % | **0.16** | 1.5 % |
| **Tala-1** | Cerca del norte (`≤ 45°`) | 1 971 | 56.8 % | 7.3 % | **7.77** | 18.7 % |
| Tala-1 | Mitad norte (`≤ 60°`) | 2 698 | 86.1 % | 9.8 % | **8.82** | 20.7 % |
| Tala-1 | Moderado (`45° – 90°`) | 2 285 | 37.0 % | 9.3 % | **3.97** | 10.5 % |
| Tala-1 | Lejos del norte (`≥ 90°`) | 18 320 | 6.2 % | 83.4 % | **0.07** | 0.2 % |

**Lectura crítica del Punto 1:**
1. **Por sí solo (de forma marginal), el consenso horario sí tiene poder discriminante de régimen (AUC `0.898–0.927` con `-dn_cons` y `0.923–0.946` con `dcos_cons`).** Sobre todo actúa como **filtro negativo** cuando la red apunta lejos del norte (`dn_cons ≥ 90°`): la razón de verosimilitud cae a `LR = 0.07–0.16` y la probabilidad a posteriori de mezcla baja a `0.2 %–1.5 %` (régimen diurno de valle del O/SO).
2. **Como detector positivo es insuficiente:** incluso cuando el consenso horario apunta a `≤ 45°` del norte (`LR+ = 6.50` en Cortadera, `15.83` en Papujune y `7.77` en Tala-1), como la tasa base de `H1` en `A ∈ [150°, 300°]` es baja (`2.9 %–8.6 %`), la probabilidad a posteriori `P(H1 | dn_cons ≤ 45°)` se queda en **30.6 % en Cortadera**, **59.9 % en Papujune** y **18.7 % en Tala-1**. Es decir, en Cortadera y Tala-1 **entre el 69 % y el 81 % de los registros con `A ∈ [150°, 300°]` y consenso en el norte siguen siendo viento real (`H0`), no mezclas (`H1`)**.

---

## 3. Punto 2: Comparación con los rasgos propios del clasificador (`north_mixture.features`)

### 3.1. Separación univariada en `A ∈ [150°, 300°]` (semanas impares de prueba)

Antes de combinar rasgos, comparamos el AUC individual de los rasgos del consenso frente a cada uno de los rasgos propios de la serie de 5 min (`north_mixture.features` y rasgos físicos derivados) sobre exactamente los mismos registros ambiguos (`A ∈ [150°, 300°]`, `H1` vs `H0`, semanas impares):

| Rasgo | Cortadera | Papujune | Tala-1 | Media 3 estaciones |
|---|---:|---:|---:|---:|
| **Propio: `max(jump_prev, jump_next)`** (mayor salto de 5 min) | **0.970** | **0.944** | **0.977** | **0.964** |
| **Propio: `bigjump_6`** (fracción de saltos `> 60°` en `±30 min`) | **0.955** | **0.951** | **0.943** | **0.949** |
| **Propio: `-r_nb`** (dispersión circular de vecinos en `±15 min`) | **0.950** | **0.932** | **0.952** | **0.945** |
| **Consenso: `dcos_cons`** (`cos(μ - comb) - cos(A - comb)`) | 0.923 | 0.924 | 0.946 | 0.931 |
| **Propio: `dist_nb`** (`\|A - nb_dir\|` en `±15 min`) | 0.923 | 0.894 | 0.952 | 0.923 |
| **Propio: `jump_next`** (salto al bloque siguiente de 5 min) | 0.930 | 0.893 | 0.946 | 0.923 |
| **Propio: `jump_prev`** (salto desde el bloque previo de 5 min) | 0.929 | 0.889 | 0.940 | 0.919 |
| **Consenso: `-dn_cons`** (cercanía del consenso al norte) | 0.898 | 0.927 | 0.911 | 0.912 |
| **Consenso: `\|A - comb\|`** (distancia entre `A` y el consenso) | 0.895 | 0.888 | 0.946 | 0.909 |
| **Propio: `hod_cos`** (coseno de la hora del día) | 0.810 | 0.879 | 0.886 | 0.858 |
| **Propio: `dcos_nb`** (`cos(μ - nb_dir) - cos(A - nb_dir)`) | 0.786 | 0.859 | 0.822 | 0.823 |
| **Propio: `-ws`** (baja velocidad a 5 min) | 0.739 | 0.740 | 0.886 | 0.788 |
| **Propio: `gust`** (`WS_ms_Max / WS_ms_Avg`) | 0.845 | 0.564 | 0.871 | 0.760 |
| **Propio: `frac_north_6`** (fracción de vecinos `≤ 30°` en `±30 min`) | 0.676 | 0.717 | 0.737 | 0.710 |
| **Propio: `-nb_north`** (cercanía al norte de la media `±15 min`) | 0.657 | 0.763 | 0.695 | 0.705 |

**Hallazgo clave 1:** Un solo rasgo cinemático propio de 5 min —el salto entre registros consecutivos `max(jump_prev, jump_next)` (AUC medio **0.964**), la frecuencia de saltos `bigjump_6` (**0.949**) o la dispersión local `-r_nb` (**0.945**)— **separa mejor H1 de H0 que cualquier formulación del consenso horario de vecinas** (`0.909–0.931`).
- La razón física es directa: en la rama de mezcla (`g(μ, σ)`), la pendiente respecto a `μ` es `~180°/σ` (`6–15×` mayor que lejos del norte). Una fluctuación real de solo `3–5°` en torno al norte entre un bloque de 5 min y el siguiente provoca saltos de `40–150°` en `WindDir_Avg`, mientras que un viento real en `150–300°` evoluciona con saltos pequeños y alta resultante `r_nb`.
- Además, la información de régimen diurno/nocturno que captura el consenso ya está contenida en buena medida en la propia hora del día (`hod_cos`, AUC univariado `0.810–0.886`).

---

### 3.2. Regresión logística y Gradient Boosting con y sin consenso (validación por semanas)

Evaluamos en semanas impares (entrenando en semanas pares) el AUC sobre la zona ambigua `A ∈ [150°, 300°]` al añadir los 4 rasgos del consenso (`dn_cons`, `|A - comb|`, `dcos_cons`, `r_cons`) tanto con calibración ideal (`D1` en semanas pares) como con calibración realista sin `D1` (`R4`, horas limpias de la estación):

#### A. Regresión logística (`StandardScaler + LogisticRegression`, semanas pares → impares)

| Conjunto de rasgos | Cortadera | Papujune | Tala-1 | Media 3 est. | Δ AUC frente a sin consenso |
|---|---:|---:|---:|---:|---:|
| 1. Solo consenso (calibrado con `D1`) | 0.9079 | 0.9185 | 0.9526 | 0.9263 | — |
| 2. Solo consenso (calibrado con `R4`, sin `D1`) | 0.8792 | 0.9462 | 0.9436 | 0.9230 | — |
| 3. Propios `BASE` sin hora (`10` rasgos) | 0.9746 | 0.9756 | 0.9745 | 0.9749 | — |
| 4. Propios `BASE` sin hora + consenso (`D1`) | 0.9766 | 0.9858 | 0.9816 | 0.9813 | +0.0064 |
| **5. Propios `BASE` (`12` rasgos `north_mixture.features`)** | **0.9741** | **0.9827** | **0.9786** | **0.9785** | — |
| **6. Propios `BASE` + consenso (`D1`)** | **0.9764** | **0.9855** | **0.9815** | **0.9812** | **+0.0027** |
| **7. Propios `BASE` + consenso (`R4`, sin `D1`)** | **0.9769** | **0.9853** | **0.9812** | **0.9811** | **+0.0026** |
| **8. Propios Etapa 1 completa (`BASE` + físicos)** | **0.9884** | **0.9893** | **0.9853** | **0.9877** | — |
| **9. Propios Etapa 1 completa + consenso (`D1`)** | **0.9885** | **0.9901** | **0.9862** | **0.9883** | **+0.0006** |

#### B. HistGradientBoosting (no lineal, semanas pares → impares)

| Conjunto de rasgos | Cortadera | Papujune | Tala-1 | Media 3 est. | Δ AUC frente a sin consenso |
|---|---:|---:|---:|---:|---:|
| 1. Solo consenso (calibrado con `D1`) | 0.9574 | 0.9595 | 0.9655 | 0.9608 | — |
| **5. Propios `BASE` (`12` rasgos `north_mixture.features`)** | **0.9936** | **0.9916** | **0.9893** | **0.9915** | — |
| **6. Propios `BASE` + consenso (`D1`)** | **0.9945** | **0.9932** | **0.9906** | **0.9928** | **+0.0013** |
| **8. Propios Etapa 1 completa (`BASE` + físicos)** | **0.9947** | **0.9935** | **0.9901** | **0.9928** | — |
| **9. Propios Etapa 1 completa + consenso (`D1`)** | **0.9951** | **0.9942** | **0.9912** | **0.9935** | **+0.0007** |

**Hallazgo clave 2:**
- Con los 12 rasgos básicos de `north_mixture.features`, la regresión logística ya alcanza un AUC medio de **0.9785** (`0.9741` en Cortadera, `0.9827` en Papujune, `0.9786` en Tala-1). Añadir el consenso solo lo mueve en **+0.0027** (`0.9785 → 0.9812`).
- Nótese la comparación entre las filas 3, 4 y 5: cuando se quitan `hod_sin` y `hod_cos` de `BASE` (fila 3, AUC `0.9749`), meter el consenso sube `+0.0064` (`0.9813`), pero meter simplemente la hora del día (`hod_sin, hod_cos`, fila 5) ya recupera más de la mitad de esa ganancia (`0.9785`) sin depender de ninguna estación externa.
- Cuando se incluyen los rasgos físicos de la Etapa 1 del clasificador (`sigma_est`, `mu_ratio`, `dcos_nb`, `north_cand_3/6/12`, `bigjump_3/6/12`), el AUC propio sube a **0.9877** en regresión logística y **0.9928** en HGB; la aportación marginal del consenso se reduce a **+0.0006** en LR y **+0.0007** en HGB (menos de una milésima de AUC).

---

### 3.3. ¿Qué ocurre cuando ningún vecino temporal de 5 min cayó cerca del norte (`frac_north_6 == 0`)?

Podría pensarse que el consenso es imprescindible en las horas en que el viento oscila en torno al norte pero **ninguno** de los 12 registros de 5 min en `±30 min` cayó a `≤ 30°` del norte (`frac_north_6 == 0`). La prueba desmiente esa hipótesis:

| Estación | Subgrupo en `A ∈ [150°, 300°]` (semanas impares) | `N` | `N_H1` | `% H1` | AUC consenso solo | AUC LR `BASE` (propios) | AUC LR `BASE` + consenso | Δ AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Cortadera** | `frac_north_6 == 0` (ningún vecino `≤ 30°`) | 16 211 | 679 | 4.2 % | 0.8924 | **0.9695** | **0.9716** | +0.0021 |
| Cortadera | `frac_north_6 > 0` (algún vecino `≤ 30°`) | 683 | 395 | 57.8 % | 0.5735 | **0.8637** | **0.8865** | +0.0228 |
| **Papujune** | `frac_north_6 == 0` (ningún vecino `≤ 30°`) | 21 807 | 1 101 | 5.0 % | 0.9133 | **0.9759** | **0.9796** | +0.0037 |
| Papujune | `frac_north_6 > 0` (algún vecino `≤ 30°`) | 1 124 | 877 | 78.0 % | 0.7508 | **0.8891** | **0.9146** | +0.0255 |
| **Tala-1** | `frac_north_6 == 0` (ningún vecino `≤ 30°`) | 21 732 | 328 | 1.5 % | 0.9074 | **0.9707** | **0.9762** | +0.0055 |
| Tala-1 | `frac_north_6 > 0` (algún vecino `≤ 30°`) | 844 | 320 | 37.9 % | 0.5408 | **0.9169** | **0.9172** | +0.0003 |

Incluso cuando `frac_north_6 == 0`, los demás rasgos propios (`jump_prev`, `jump_next`, `r_nb`, `dist_nb`, `ws`, `gust`, `hod_sin/cos`) alcanzan un AUC de **0.9695–0.9759** por sí solos, porque doce bloques de 5 min que cruzan el norte sin caer en `[-30°, 30°]` tienen saltos enormes entre sí y una longitud resultante `r_nb` hundida.

---

### 3.4. Impacto en el error direccional horario final y en validación cruzada entre estaciones (LOSO)

Lo que importa operativamente es si meter el consenso en el clasificador de dos etapas reduce el error angular horario frente a `WindDir_D1_WVT_h` en una estación sin `D1` (escenario **LOSO**: entrenar en dos estaciones y evaluar en la tercera en semanas impares):

| Estación evaluada (LOSO) | Modelo de 2 etapas | AUC `A∈[150,300]` (Etapa 2) | Error horario: Todas (°) | Error horario: **Norte ≤ 45° (°)** | Error horario: Resto (°) |
|---|---|---:|---:|---:|---:|
| **Cortadera** | `V1` (sin clasificador) | — | 6.37° | 38.57° | 2.74° |
| Cortadera | LR Etapa 1+2 (solo propios) | **0.988** | 3.28° | **9.98°** | 2.53° |
| Cortadera | LR Etapa 1+2 + consenso (`D1`-cal) | 0.987 | 3.17° | 10.92° (+0.94°) | 2.30° |
| Cortadera | LR Etapa 1+2 + consenso (`R4`-cal, sin `D1`) | 0.988 | 3.23° | 10.05° (+0.06°) | 2.46° |
| Cortadera | HGB Etapa 1+2 (solo propios) | **0.982** | **2.92°** | **10.48°** | **2.06°** |
| Cortadera | HGB Etapa 1+2 + consenso (`D1`-cal) | 0.980 | 3.16° | 11.72° (+1.24°) | 2.19° |
| Cortadera | HGB Etapa 1+2 + consenso (`R4`-cal, sin `D1`) | 0.983 | 3.07° | 11.68° (+1.21°) | 2.10° |
| **Papujune** | `V1` (sin clasificador) | — | 12.94° | 34.62° | 4.96° |
| Papujune | LR Etapa 1+2 (solo propios) | 0.960 | 7.10° | 14.73° | 4.29° |
| Papujune | LR Etapa 1+2 + consenso (`D1`-cal) | 0.970 | 6.80° | 13.79° (−0.94°) | 4.23° |
| Papujune | LR Etapa 1+2 + consenso (`R4`-cal, sin `D1`) | 0.961 | 7.13° | 14.91° (+0.18°) | 4.26° |
| Papujune | HGB Etapa 1+2 (solo propios) | 0.975 | 6.15° | **10.34°** | 4.61° |
| Papujune | HGB Etapa 1+2 + consenso (`D1`-cal) | 0.978 | 6.09° | 10.43° (+0.10°) | 4.49° |
| Papujune | HGB Etapa 1+2 + consenso (`R4`-cal, sin `D1`) | 0.977 | 6.25° | 11.13° (+0.79°) | 4.45° |
| **Tala-1** | `V1` (sin clasificador) | — | 4.61° | 18.93° | 2.55° |
| Tala-1 | LR Etapa 1+2 (solo propios) | 0.982 | **3.79°** | 6.50° | **3.39°** |
| Tala-1 | LR Etapa 1+2 + consenso (`D1`-cal) | 0.983 | 4.19° | 6.48° (−0.02°) | 3.86° |
| Tala-1 | LR Etapa 1+2 + consenso (`R4`-cal, sin `D1`) | 0.982 | 4.81° | 6.50° (+0.00°) | 4.57° |
| Tala-1 | HGB Etapa 1+2 (solo propios) | **0.988** | **2.85°** | **5.56°** | **2.45°** |
| Tala-1 | HGB Etapa 1+2 + consenso (`D1`-cal) | 0.988 | 2.82° | 5.59° (+0.04°) | 2.42° |
| Tala-1 | HGB Etapa 1+2 + consenso (`R4`-cal, sin `D1`) | 0.988 | 3.42° | 5.40° (−0.16°) | 3.13° |

**Media de las 3 estaciones en validación LOSO (HGB Etapa 1+2):**
- **Solo rasgos propios:** `3.97°` en todas las horas / **`8.79°` en el sector norte**.
- **Con consenso calibrado con `D1` (oráculo espacial):** `4.02°` en todas / **`9.25°` en el sector norte** (empeora `+0.46°`).
- **Con consenso calibrado con `R4` (realista sin `D1`):** `4.24°` en todas / **`9.40°` en el sector norte** (empeora `+0.61°`).

---

## 4. Escrutinio del ejemplo concreto de la Afirmación 10 (Cortadera de noche con `A ≈ 240°`)

La Afirmación 10 sostiene:
> *«Ejemplo: de noche en Cortadera nunca sopla del oeste, así que un A de ~240° con régimen de drenaje tiene que ser una mezcla.»*

Al contrastar esta frase con los **33 470 registros de 5 min nocturnos (`22:00–06:00`)** de Cortadera (`2025-11-01` → `2026-09-13`, antes de la anomalía de veleta), la afirmación queda refutada por una **falacia de tasa base** y por la propia mecánica de `consensus_pairs.py`:

| Subconjunto en Cortadera de noche | `N` (5 min) | `H1`: Mezcla norte (`D1 ≤ 45°`) | Intermedio (`D1 ∈ 45–90°`) | `H0`: Viento real (`D1 ≥ 90°`) | Del cual `D1 ∈ 180–315°` (S–O real) |
|---|---:|---:|---:|---:|---:|
| Todos los registros nocturnos (`22–06 h`) | 33 470 | 11.5 % (3 855) | 17.6 % (5 898) | 70.9 % (23 717) | **10.1 % (3 364)** |
| Noche (`22–06 h`) con `A ∈ [150°, 300°]` | 3 972 | 16.7 % (662) | 34.4 % (1 367) | **48.9 % (1 943)** | **77.4 % (3 075)** |
| Noche (`22–06 h`) con **`A ∈ [210°, 270°]` (`~240°`)** | 1 916 | **13.6 % (260)** | 3.7 % (70) | **82.8 % (1 586)** | **85.8 % (1 643)** |
| Noche estricta (`23–05 h`) con **`A ∈ [210°, 270°]` (`~240°`)** | 1 192 | **13.2 % (157)** | 4.3 % (51) | **82.6 % (984)** | **86.1 % (1 026)** |
| Noche (`22–06 h`), `A ∈ [210°, 270°]` + **consenso en drenaje (`comb ∈ 315–135°`)** | 1 787 | **14.5 % (260)** | 3.9 % (69) | **81.6 % (1 458)** | **84.7 % (1 514)** |
| Noche (`22–06 h`), `A ∈ [210°, 270°]` + **salto propio `max_jump > 45°`** | 527 | **42.1 % (222)** | 9.9 % (52) | 48.0 % (253) | 55.6 % (293) |
| Noche (`22–06 h`), `A ∈ [210°, 270°]` + **serie propia estable (`max_jump ≤ 25°`)** | 982 | **0.7 % (7)** | 0.5 % (5) | **98.8 % (970)** | **99.3 % (975)** |

1. **Sí sopla del oeste/suroeste de noche en Cortadera (~4 % en `23–05 h` y 10.1 % en `22–06 h`):** aunque el régimen dominante nocturno en Cortadera es el abanico de drenaje N–SE (`0°–150°`, 89.2 % de la noche), existen episodios nocturnos reales de componente O/SO. Y como las mezclas del norte que caen específicamente en `A ∈ [210°, 270°]` de noche son aún más raras (`260` registros, `0.8 %` de la noche), cuando se observa `A ≈ 240°` de noche en Cortadera, **el 82.8 % de las veces es viento real del O/SO (`H0`) y solo el 13.6 % es una mezcla del norte (`H1`)**.
2. **El consenso por pares (`consensus_pairs.py`) no distingue esos episodios nocturnos:** como `consensus_pairs.py` asigna a cada `(sector de la vecina × franja nocturna)` la dirección media nocturna de Cortadera en entrenamiento (que siempre cae en el abanico de drenaje `30°–125°`), en **1 787 de los 1 916** registros nocturnos con `A ≈ 240°` el consenso sigue apuntando al drenaje (`315°–135°`), y el **81.6 %** de ellos siguen siendo viento real del oeste (`H0`). Si un clasificador aplicara la regla del ejemplo («de noche con `A ≈ 240°` y consenso en drenaje → mezcla»), **se equivocaría en 4 de cada 5 registros**, introduciendo falsas alarmas de `> 120°` de error.
3. **Lo que sí separa las 260 mezclas reales de los 1 586 vientos del oeste nocturnos es la cinemática propia de 5 min:** cuando `A ∈ [210°, 270°]` de noche es estable entre bloques consecutivos de 5 min (`max(jump_prev, jump_next) ≤ 25°`, `982` registros), el **98.8 % es viento real del oeste (`H0`)** y solo el **0.7 % (`7` registros) es mezcla (`H1`)**. En cambio, el **85.4 % (`222 / 260`)** de las mezclas reales con `A ≈ 240°` presentan saltos `max_jump > 45°`.

---

## 5. Una forma mejor de usar las vecinas: vector sinóptico crudo de la red (`test_alternatives.py`)

El consenso por pares (`consensus_pairs.py`) presenta dos defectos estructurales cuando se intenta usar como rasgo para el clasificador de mezclas de 5 min:
1. **Colapso de régimen en las horas anómalas:** al calibrar cada vecina por `(sector × franja horaria)` hacia la dirección media histórica de la estación objetivo en esa celda, asigna casi cualquier dirección nocturna de las vecinas al centro del abanico de drenaje nocturno de la estación (`~30°–125°` en Cortadera), borrando precisamente la señal de si la red está en régimen catabático normal o bajo un episodio sinóptico de oeste.
2. **Dependencia circular de `D1`:** en una estación objetivo sin `D1` (que es para lo que existe el clasificador de 5 min), no existe `D1` para calibrar las 48 celdas (`16 sectores × 3 franjas`) de cada vecina, y al calibrar con horas limpias `R4` el sesgo de selección contra el sector norte degrada la calibración.

Probamos en `wind_vector/consensus/audit/r3/test_alternatives.py` una alternativa que no necesita `D1` ni calibración por estación: **el vector sinóptico crudo de la red** (`net_dir`, dirección del promedio vectorial ponderado por velocidad de toda la red limpia, y `net_r`, coherencia espacial de la red), junto con un **prior climático propio R4** (frecuencia empírica de `A` por sector y franja horaria medida solo sobre los registros propios estables `max_jump ≤ 20°` y `r_nb ≥ 0.92`, sin vecinas):

| Estación | Configuración (Regresión Logística Etapa 1+2, sem. pares → impares) | AUC `A∈[150,300]` (E2) | Error todas (°) | **Error norte ≤ 45° (°)** | Error resto (°) |
|---|---|---:|---:|---:|---:|
| **Cortadera** | 1. Propios Etapa 1+2 (sin vecinas) | 0.9849 | 3.01° | 9.73° | 2.25° |
| Cortadera | 2. Propios + Consenso por pares (`D1`-cal) | 0.9859 | 2.88° | 9.11° | 2.18° |
| Cortadera | 3. Propios + Prior climático propio R4 (SIN vecinas) | 0.9876 | 2.97° | 9.54° | 2.22° |
| Cortadera | **4. Propios + Red sinóptica cruda (sin calibrar)** | **0.9884** | **2.77°** | **8.53°** | **2.12°** |
| **Papujune** | 1. Propios Etapa 1+2 (sin vecinas) | 0.9832 | 6.07° | 9.81° | 4.69° |
| Papujune | 2. Propios + Consenso por pares (`D1`-cal) | 0.9838 | 5.93° | 9.13° | 4.75° |
| Papujune | 3. Propios + Prior climático propio R4 (SIN vecinas) | 0.9841 | 6.01° | 9.62° | 4.68° |
| Papujune | **4. Propios + Red sinóptica cruda (sin calibrar)** | **0.9873** | **5.56°** | **8.56°** | **4.46°** |
| **Tala-1** | 1. Propios Etapa 1+2 (sin vecinas) | 0.9845 | 2.57° | 7.56° | 1.85° |
| Tala-1 | 2. Propios + Consenso por pares (`D1`-cal) | 0.9856 | 2.53° | 7.42° | 1.83° |
| Tala-1 | 3. Propios + Prior climático propio R4 (SIN vecinas) | 0.9851 | 2.57° | 7.59° | 1.84° |
| Tala-1 | **4. Propios + Red sinóptica cruda (sin calibrar)** | **0.9869** | **2.50°** | **7.35°** | **1.80°** |

El vector sinóptico crudo de la red (`net_dn = |net_dir - 0°|`, `net_dist_a = |A - net_dir|`, `net_r`) supera al consenso por pares calibrado con `D1` en las tres estaciones, reduciendo el error en el norte a **`8.53°` en Cortadera, `8.56°` en Papujune y `7.35°` en Tala-1** (media **`8.15°`** frente a `9.03°` solo con propios y `8.55°` con consenso por pares calibrado con `D1`), sin usar `D1` de la estación evaluada.

Más importante aún, en **validación entre estaciones (LOSO, entrenar en 2 estaciones y evaluar en la 3ª)** —donde el consenso por pares calibrado fracasa o no mejora porque depende de la geometría local de cada estación—, el vector sinóptico crudo de la red **sí generaliza en las tres estaciones**:

| Estación (LOSO) | Configuración (Regresión Logística Etapa 1+2) | AUC `A∈[150,300]` (E2) | Error todas (°) | **Error norte ≤ 45° (°)** | Error resto (°) |
|---|---|---:|---:|---:|---:|
| **Cortadera** | 1. LOSO Propios Etapa 1+2 (sin vecinas) | 0.9878 | 3.28° | 9.98° | 2.53° |
| Cortadera | 2. LOSO Propios + Consenso por pares (`D1`-cal) | 0.9873 | 3.17° | 10.92° (+0.94°) | 2.30° |
| Cortadera | 3. LOSO Propios + Consenso por pares (`R4`-cal) | 0.9875 | 3.23° | 10.05° (+0.07°) | 2.46° |
| Cortadera | **4. LOSO Propios + Red sinóptica cruda (sin calibrar)** | **0.9904** | **3.06°** | **8.63° (−1.35°)** | **2.44°** |
| **Papujune** | 1. LOSO Propios Etapa 1+2 (sin vecinas) | 0.9602 | 7.10° | 14.73° | 4.29° |
| Papujune | 2. LOSO Propios + Consenso por pares (`D1`-cal) | 0.9700 | 6.80° | 13.79° (−0.94°) | 4.23° |
| Papujune | 3. LOSO Propios + Consenso por pares (`R4`-cal) | 0.9615 | 7.13° | 14.91° (+0.18°) | 4.26° |
| Papujune | **4. LOSO Propios + Red sinóptica cruda (sin calibrar)** | **0.9728** | **6.51°** | **13.26° (−1.47°)** | **4.02°** |
| **Tala-1** | 1. LOSO Propios Etapa 1+2 (sin vecinas) | 0.9820 | 3.79° | 6.50° | 3.39° |
| Tala-1 | 2. LOSO Propios + Consenso por pares (`D1`-cal) | 0.9832 | 4.19° | 6.48° (−0.02°) | 3.86° |
| Tala-1 | 3. LOSO Propios + Consenso por pares (`R4`-cal) | 0.9822 | 4.81° | 6.50° (+0.00°) | 4.57° |
| Tala-1 | **4. LOSO Propios + Red sinóptica cruda (sin calibrar)** | **0.9847** | **3.67°** | **6.01° (−0.49°)** | **3.34°** |

En promedio de las tres estaciones en LOSO (Regresión Logística Etapa 1+2), el error en el sector norte pasa de **`10.40°` (solo propios)** y **`10.49°` (consenso por pares R4)** a **`9.30°` con el vector sinóptico crudo de la red (`−1.10°`)**, reduciendo además el error en el resto de sectores (`3.40° → 3.27°`).

---

## 6. Veredicto sobre la Afirmación 10 y recomendación

1. **Veredicto sobre la Afirmación 10: PARCIALMENTE CIERTA EN SU PREMISA FÍSICA, PERO REDUNDANTE EN EL CLASIFICADOR Y FALSA EN SU EJEMPLO DE CORTADERA.**
   - **Qué es cierto:** En la zona ambigua `A ∈ [150°, 300°]`, el consenso horario de vecinas sí separa marginalmente `H1` (`D1 ≤ 45°`) de `H0` (`D1 ≥ 90°`) con un **AUC de `0.898` (Cortadera), `0.927` (Papujune) y `0.911` (Tala-1)** usando `-dn_cons` (`0.923`, `0.924` y `0.946` usando `dcos_cons`), y razones de verosimilitud `LR+ = 6.50 / 15.83 / 7.77` cuando el consenso está a `≤ 45°` del norte frente a `LR- = 0.13 / 0.16 / 0.07` cuando está a `≥ 90°` del norte.
   - **Qué es falso en el ejemplo:** En Cortadera de noche (`22–06 h`) **sí sopla del oeste/suroeste el 10.1 % del tiempo** (`3 364` registros con `D1 ∈ [210°, 315°]`; ~4 % en `23–05 h`). Como las mezclas nocturnas que caen en `A ∈ [210°, 270°]` (`~240°`) son aún más raras (`0.8 %` de la noche), cuando en Cortadera de noche se observa `A ≈ 240°` —incluso con consenso en régimen de drenaje—, **el 81.6 %–82.8 % de las veces es un viento real (`H0`) y solo el 13.6 %–14.5 % es una mezcla del norte (`H1`)**. Lo que distingue al 13.6 % de mezclas reales no es el consenso horario, sino los saltos propios entre bloques de 5 min (`max(jump_prev, jump_next)`).
   - **Por qué casi no aporta al clasificador:** Un solo rasgo propio de 5 min (`max(jump_prev, jump_next)`, AUC `0.964`, o `r_nb`, AUC `0.945`) separa mejor `H1` de `H0` que todo el consenso de vecinas (`0.912–0.931`), y la hora del día (`hod_sin, hod_cos`) ya captura la mayor parte del ciclo diurno de régimen. Al añadir el consenso por pares a `north_mixture.features`, el AUC de la regresión logística apenas pasa de **`0.9785` a `0.9812` (`+0.0027`)**, y con los rasgos físicos de Etapa 1 pasa de **`0.9877` a `0.9883` (`+0.0006`)** (`0.9928 → 0.9935` en HGB).
2. **¿Vale la pena meter el consenso por pares (`consensus_pairs.py`) en el clasificador? NO.**
   - En validación cruzada entre estaciones (**LOSO**, el caso de uso real para estaciones sin `D1`), meter el consenso por pares en el clasificador de dos etapas (HGB) **empeora** el error medio con viento del norte de **`8.79°` a `9.25°`** (incluso calibrando las vecinas con `D1` verdadero) y a **`9.40°`** cuando se calibra sin `D1` usando horas limpias `R4`, además de acoplar la reconstrucción de cada estación a las caídas, exclusiones y desfases de veleta del resto de la red.
   - Si en algún momento se quisiera incorporar información de la red, debe usarse el **vector sinóptico crudo de la red sin calibración por estación** (`net_dn`, `net_dist_a`, `net_r`), que no requiere `D1` y supera al consenso por pares en las tres estaciones, pero la ganancia (`~0.2–0.8°`) sigue siendo de segundo orden frente a la cinemática propia de 5 min.

---

## 7. Scripts generados en `r3/`

- `wind_vector/consensus/audit/r3/analyze_r3.py`: cálculo del consenso horario por pares (con `D1` y con `R4`), conteos, AUC y razones de verosimilitud en `A ∈ [150°, 300°]` (Punto 1), comparativa univariada y multivariada con `north_mixture.features` y Etapa 1+2 dentro de estación y en LOSO (Punto 2), análisis de subgrupos (`frac_north_6 == 0`) y verificación del ejemplo nocturno de Cortadera.
- `wind_vector/consensus/audit/r3/test_alternatives.py`: evaluación del vector sinóptico crudo de la red, vecinas crudas y prior climático propio `R4` frente al consenso por pares.
