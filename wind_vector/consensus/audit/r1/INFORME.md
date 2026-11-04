# Informe de Auditoría r1: El Método del Consenso Espacial

**Alcance**: Escrutinio cuantitativo de las afirmaciones 1 a 5 sobre el método de consenso espacial (`consensus_idw.py`, `consensus_calibrated.py`, `consensus_pairs.py`), corrección de la ponderación de vecinas mediante validación interna sobre semanas pares y propuesta de método mejorado comparable sobre las mismas semanas impares de prueba (`2025-11-01` a `2026-11-03`).
**Script de verificación**: `explorar_qaqc/wind_vector/consensus/audit/r1/r1_audit.py`.

---
## Afirmación 1: Error de `WindDir_Avg` fuera del sector norte y límite frente al consenso

> **Afirmación**: _«Fuera del sector norte, `WindDir_Avg` y D1 de la misma estación casi coinciden (error 7–17°) porque salen de las mismas muestras; por eso ningún consenso de vecinas puede superar al dato propio fuera del norte.»_

### Veredicto: **Parcial**

La causa física es correcta y, en el promedio global de todas las horas fuera del norte (`|D1| > 45°`), ningún consenso espacial puro supera al dato propio. Sin embargo, la afirmación presenta **dos errores importantes**:
1. **Las cifras `7–17°` están mal atribuidas**: corresponden al error medio en **todas las horas** (incluyendo el sector norte), no al error fuera del norte. Fuera del norte (`|D1| > 45°`), el error medio real es **`3.7°–5.7°`** en 7 de las 8 estaciones (**`12.1°`** en `Minas_Sur`), con **medianas de `0.0°–0.3°`** (`3.2°` en `Minas_Sur`).
2. **El fallo de `WindDir_Avg` no termina en `|D1| = 45°`**: entre el **3.3 % y el 13.2 % de las horas fuera del norte** (139 a 436 h por estación, concentradas en `45° < |D1| <= 90°` con alta turbulencia direccional `SD1_WVT ~ 50°–65°`) sufren **cruces parciales por 0°/360°** durante la hora. En ese subconjunto de horas fuera del norte, `WindDir_Avg` tiene un error medio de **`49.0°–58.0°`** y el consenso por pares lo supera en **las 8 estaciones** (`27.8°–51.6°`).

### Cifras que lo sustentan

#### Tabla 1A — Desglose del error de `WindDir_Avg` frente a `D1` (`ws > 1 m/s`, red `--limpio`)

| Estación | Horas totales | % horas Norte (`\|D1\|≤45°`) | Error todas las h (°) | Error Norte `\|D1\|≤45°` (°) | Error fuera `\|D1\|>45°` media / mediana (°) | Error `45°<\|D1\|≤90°` (°) | Error `\|D1\|>90°` (°) | Horas fuera con error >30° | `SD1` medio si err>30° vs ≤30° (°) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Altarani | 8162 | 6.0 % | 7.5 | 64.7 | **3.8 / 0.1** | 4.8 | 3.0 | 319 (4.2 %) | 61.8 vs 16.5 |
| Alto_Quellaveco | 6591 | 35.6 % | 16.9 | 40.1 | **4.1 / 0.3** | 7.1 | 2.4 | 139 (3.3 %) | 50.1 vs 22.8 |
| Camp_Quellaveco | 4961 | 4.2 % | 9.5 | 96.7 | **5.7 / 0.0** | 7.7 | 3.1 | 341 (7.2 %) | 50.8 vs 13.6 |
| Cortadera | 6716 | 8.5 % | 10.0 | 76.3 | **3.9 / 0.1** | 10.8 | 1.5 | 292 (4.7 %) | 56.0 vs 16.5 |
| Minas_Sur | 4242 | 30.3 % | 32.6 | 79.8 | **12.1 / 3.2** | 13.7 | 7.4 | 390 (13.2 %) | 64.5 vs 25.7 |
| Papujune | 6263 | 25.3 % | 17.2 | 57.0 | **3.7 / 0.2** | 12.1 | 1.5 | 169 (3.6 %) | 50.9 vs 22.4 |
| Tala-1 | 7989 | 11.6 % | 9.8 | 48.4 | **4.7 / 0.0** | 7.1 | 2.9 | 436 (6.2 %) | 62.9 vs 14.6 |
| Tala_Legal | 7465 | 4.7 % | 7.0 | 70.0 | **3.9 / 0.1** | 4.3 | 3.3 | 321 (4.5 %) | 61.7 vs 15.3 |

#### Tabla 1B — Comparación en semanas de prueba (`te`) fuera del norte (`|D1| > 45°`)

| Estación | Horas prueba `\|D1\|>45°` | `WindDir_Avg` fuera (°) | Consenso pares fuera (°) | Horas prueba fuera con err(`A`)>30° | En err(`A`)>30°: `Avg` vs `Pares` (°) | Regla híbrida ciega en todas las h (`Avg` → `Híbrido`) |
|---|---:|---:|---:|---:|---:|---:|
| Altarani | 3788 | **3.79** | 13.48 | 163 | 57.3 vs **47.3** | 7.8 → **7.7** |
| Alto_Quellaveco | 2149 | **3.80** | 38.64 | 68 | 55.5 vs **48.4** | 16.0 → **12.7** |
| Camp_Quellaveco | 2360 | **6.06** | 13.73 | 186 | 56.0 vs **37.0** | 10.0 → 11.0 |
| Cortadera | 3005 | **3.49** | 17.09 | 122 | 57.1 vs **51.6** | 9.8 → 10.5 |
| Minas_Sur | 1464 | **11.29** | 23.15 | 171 | 52.1 vs **27.8** | 33.7 → **24.8** |
| Papujune | 2336 | **3.86** | 21.41 | 94 | 49.0 vs **39.8** | 17.4 → **12.1** |
| Tala-1 | 3505 | **4.36** | 13.02 | 198 | 55.9 vs **48.8** | 9.7 → **8.6** |
| Tala_Legal | 3533 | **4.05** | 12.87 | 170 | 58.0 vs **42.0** | 7.1 → 7.2 |

### Explicación
- Cuando el viento es estacionario lejos del norte (`|D1| > 90°`), la media aritmética de los 720 ángulos de 5 s y la media vectorial ponderada por velocidad difieren solo en ~`0.1°` de mediana (`1.5°–3.3°` de media), muy por debajo de la dispersión espacial entre estaciones (`13°–38°`).
- El motivo por el que `Minas_Sur` presenta `32.6°` en todas las horas (y `Alto_Quellaveco` `16.9°`, `Papujune` `17.2°`) es ante todo su **alta frecuencia de viento del norte** (`30.3 %`, `35.6 %` y `25.3 %` del tiempo, frente a `4 %–12 %` en las demás), sumada en `Minas_Sur` a un `13.2 %` de horas con `|D1| > 45°` que oscilan cruzando el norte (`SD1 = 64.5°`).
- Si no se dispone de `SD1_WVT` ni de datos de 5 min para detectar qué horas fuera del norte tuvieron cruces parciales por 0°, una regla ciega basada solo en la discrepancia entre `WindDir_Avg` y el consenso mete suficientes falsos positivos fuera del norte como para subir el error en `|D1| > 45°` en `1.4°–3.4°` (aunque mejora el error global de toda la serie en las estaciones con frecuente viento del norte).

---

## Afirmación 2: Causa del fallo del consenso IDW crudo (25–58°)

> **Afirmación**: _«El consenso IDW crudo (vectores u, v ponderados por velocidad y 1/d²) falla 25–58° por los flujos locales (drenaje, laderas, tajo), no por un defecto del método.»_

### Veredicto: **Parcial**

Es cierto que los flujos topográficos locales imponen un **suelo físico irreductible de `22.7°–51.0°`** en un promedio espacial sin calibrar. Pero es **falso** que el método `consensus_idw.py` no tenga defectos propios: en el **sector norte**, entre **`13°` y `50°` del error del IDW crudo** provienen de un **defecto metodológico grave** (alimentar el promedio vectorial con el `WindDir_Avg` corrupto de las vecinas que no tienen `D1`), agravado por no aplicar `--limpio`, ponderar por la velocidad cruda de sensores a distinta altura y usar distancia 2D sin penalizar el desnivel vertical.

### Cifras que lo sustentan

#### Tabla 2 — Desglose metodológico vs físico del IDW sin calibrar (semanas impares de prueba `te`, formato `todas / norte` en grados)

| Estación | 1. `IDW_bruto` (`consensus_idw.py`) | 2. `IDW_limpio_ws` (`--limpio`, `ws/d²`) | 3. `IDW_limpio_unit` (`--limpio`, `1/d²`) | 4. `IDW_unit_soloD1` (sin vecinas `Avg`) | 5. `IDW_3D_soloD1` (`d_xy² + (8·dz)²`) | Desfase circular medio Día / Noche vs IDW |
|---|---:|---:|---:|---:|---:|---:|
| Altarani | 58.3 / 50.0 | 51.8 / 44.3 | 51.8 / 44.0 | 51.1 / **38.0** | **51.0** / 38.5 | +29° / +56° |
| Alto_Quellaveco | 39.0 / 48.4 | 38.8 / 46.8 | 39.5 / 46.3 | 39.8 / **39.7** | 39.2 / **38.8** | +18° / +6° |
| Camp_Quellaveco | 47.3 / 84.5 | 45.7 / 87.1 | 49.6 / 92.6 | 30.3 / 56.9 | **22.7 / 56.6** | +39° / +20° |
| Cortadera | 32.8 / 72.3 | 28.0 / 79.2 | 31.7 / 88.7 | 24.8 / **39.1** | **24.2** / 41.4 | +12° / −1° |
| Minas_Sur | 36.6 / 42.1 | 36.6 / 48.7 | 37.1 / 50.5 | 36.7 / 47.0 | **35.3 / 41.2** | −2° / −38° |
| Papujune | 33.5 / 35.7 | 36.8 / 67.1 | 39.6 / 77.9 | 41.4 / 54.9 | 38.3 / 48.9 | −18° / −32° |
| Tala-1 | 24.4 / 74.5 | 24.4 / 78.8 | 25.8 / 81.6 | 33.4 / 77.1 | 28.6 / **66.8** | −4° / −27° |
| Tala_Legal | 40.9 / 84.4 | 44.4 / 83.2 | 44.9 / 83.9 | 48.5 / 70.7 | 45.8 / **67.3** | +40° / +36° |

### Explicación
1. **Defecto 1 — Contaminación del IDW con `WindDir_Avg` de vecinas sin `D1`**: `consensus_idw.py` hace `df["dir"] = df.D1.fillna(df.A)`. Cuando el flujo regional viene del norte, las vecinas sin `D1` (como `Chancado_primario` a 0.65 km de `Camp_Quellaveco`, `Apacheta` y `Calientes1` cerca de `Cortadera`, o `Alto_Tala` a 0.69–2.0 km de `Tala_Legal`, `Tala-1` y `Papujune`) sufren el fallo de cruce por 0°/360° y devuelven direcciones falsas hacia el sur/este/oeste (~180°). Al quitar del IDW unitario las vecinas sin `D1` (columna 4), el error en el norte cae de golpe **`49.6°` en `Cortadera` (`88.7° → 39.1°`)**, **`35.7°` en `Camp_Quellaveco` (`92.6° → 56.9°`)** y **`23.0°` en `Papujune` (`77.9° → 54.9°`)**, y el error total en `Camp_Quellaveco` baja de `49.6°` a `30.3°`. *(Nota: `consensus_idw.py` probó una columna «8 con D1», pero sin `--limpio` y ponderando por velocidad cruda, lo que camufló esta mejora con los giros de septiembre de `Cortadera` y `Alto_Quellaveco`).*
2. **Defecto 2 — No aplicar `--limpio` e ignorar la distancia vertical (`dz`)**: `consensus_idw.py` dejó dentro estaciones rotadas/congeladas (`Planta_Concentradora`, `Chalsos`, `Mina_Norte`, `Sarallenque` antiguo y los tramos rotados de septiembre). Además, con `1/d_xy²` puro, una estación en la cresta o borde de tajo domina a otra en fondo de quebrada con distinto régimen térmico; al penalizar el desnivel vertical (`1 km` vertical = `8 km` horizontal, columna 5), `Camp_Quellaveco` baja hasta **`22.7°`** en todas las horas.
3. **Lo que sí es físico (flujos locales)**: Aun corrigiendo todos los defectos del IDW crudo (columna 5), el error global no baja de **`22.7°–51.0°`**. La última columna demuestra por qué: cada estación tiene un desfase topográfico sistemático respecto al flujo medio de la red que además depende del régimen diurno/nocturno (p. ej. `Altarani` está rotada `+29°` de día y `+56°` de noche por el drenaje SE de su ladera; `Minas_Sur` pasa de `-2°` de día a `-38°` de noche; `Tala_Legal` mantiene `+40°/+36°` por la canalización de su quebrada).

---
## Afirmación 3: Calibración por pares (`sector 22.5° × franja`) y mejora en el sector norte

> **Afirmación**: _«Calibrar cada vecina por separado (desfase circular por sector de 22.5° × franja día/noche/transición) y combinarlas por su acierto mejora el sector norte en 6 de 8 estaciones (p. ej. Papujune 34° → 22°).»_

### Veredicto: **Parcial (aritméticamente cierta con oráculo `D1`, pero metodológicamente inválida para estaciones que solo tienen `WindDir_Avg`)**

Las cifras reportadas se reproducen con exactitud: frente al consenso IDW calibrado (`consensus_calibrated.py --limpio`), el consenso por pares (`consensus_pairs.py --limpio`) mejora el error de prueba en el sector norte en **6 de las 8 estaciones** (todas excepto `Camp_Quellaveco`, que sube de `37.8°` a `41.2°`, y `Minas_Sur`, de `30.3°` a `31.1°`; en `Papujune` baja de `34.1°` a `22.1°`), y frente al `WindDir_Avg` propio mejora en **8 de 8**.

Sin embargo, el método tiene una **falla estructural de diseño (fuga de información del oráculo `D1`)**:
- El objetivo declarado del consenso (`CONSENSO.md` §Pregunta) es reconstruir la dirección vectorial horaria **en estaciones donde solo existe `WindDir_Avg`**.
- Pero `consensus_pairs.py` entrena la tabla de 48 desfases (`16 sectores × 3 franjas`) de cada estación objetivo usando como verdad su propio **`WindDir_D1_WVT` (`truth = P["d1"][t]`)**.
- Si la estación objetivo **solo tiene `WindDir_Avg`** y entrenamos los desfases contra `WindDir_Avg` —tanto usando todas las horas como filtrando solo «horas limpias» fuera del norte (`|WindDir_Avg| > 45°`, como propone `CONSENSO.md` en §Pendiente)—, **el método colapsa en el sector norte (`59.9°–105.6°` de error)**, rindiendo peor que el propio `WindDir_Avg` sin corregir.

### Cifras que lo sustentan

#### Tabla 3 — Comparación en semanas de prueba (`te`, formato `todas / norte` en grados)

| Estación | `WindDir_Avg` propio | Climatología horaria pura (0 vecinas, con `D1`) | `Calib_IDW` (`consensus_calibrated.py`, con `D1`) | `Pares` con oráculo `D1` (`consensus_pairs.py`) | `Pares` entrenado con `WindDir_Avg` (todas) | `Pares` entrenado con `WindDir_Avg` limpio (`\|A\|>45°`) |
|---|---:|---:|---:|---:|---:|---:|
| Altarani | 7.8 / 66.7 | 22.1 / 60.4 | 18.3 / 53.8 | 15.8 / **50.5** | 20.9 / 82.6 | 21.1 / 83.4 |
| Alto_Quellaveco | 16.0 / 39.3 | 50.5 / 51.9 | 33.7 / 33.7 | 36.9 / **33.5** | 46.2 / 73.8 | 50.7 / 88.5 |
| Camp_Quellaveco | 10.0 / 95.4 | 24.0 / 81.4 | 12.8 / **37.8** | 14.9 / 41.2 | 20.2 / 96.0 | 20.2 / 96.0 |
| Cortadera | 9.8 / 72.5 | 28.8 / 65.5 | 19.2 / 53.3 | 19.8 / **46.1** | 25.0 / 102.8 | 25.6 / 105.6 |
| Minas_Sur | 33.7 / 81.2 | 31.3 / 43.7 | 22.4 / **30.3** | 25.7 / 31.1 | 48.3 / 98.9 | 49.2 / 101.2 |
| Papujune | 17.4 / 57.1 | 29.9 / 32.1 | 26.4 / 34.1 | 21.6 / **22.1** | 33.5 / 76.9 | 37.3 / 89.7 |
| Tala-1 | 9.7 / 50.2 | 22.4 / 34.7 | 14.5 / 32.6 | 14.1 / **22.4** | 19.1 / 59.9 | 20.7 / 66.6 |
| Tala_Legal | 7.1 / 71.1 | 20.2 / 37.4 | 15.0 / 34.9 | 13.6 / **28.6** | 16.1 / 70.0 | 16.2 / 70.3 |

### Explicación
1. **Por qué fracasa calibrar con «horas limpias» en estaciones sin `D1`**: La tabla de calibración indexa el desfase por el **sector de la vecina (`sector_vecina × franja`)**. Cuando en la estación objetivo sopla viento del norte, la vecina se encuentra en sus sectores asociados al flujo norte. Si entrenamos con todas las horas de `WindDir_Avg`, esas celdas aprenden el ángulo aritmético corrupto (~180°). Y si filtramos del entrenamiento las horas con `|WindDir_Avg| ≤ 45°` (o con alta dispersión), vaciamos de muestras verdaderas del norte esas celdas y solo dejamos en ellas horas en que la estación objetivo ya apuntaba fuera del norte (`> 45°`), por lo que la tabla aprende un sesgo que jamás predice norte (`66.6°–105.6°`). Para usar este método en una estación sin `D1`, primero hay que reconstruir sus horas del norte en entrenamiento mediante las series de 5 min (`protocol.py`) antes de ajustar la tabla espacial.
2. **Cuánto aporta realmente la red frente a la simple hora del día**: En un sistema térmico de montaña, la mera climatología horaria de la estación objetivo sin mirar ninguna vecina (columna 3) ya alcanza `32.1°` en el norte de `Papujune` y `34.7°` en `Tala-1`. El consenso por pares aporta una reducción adicional real de `10°–40°` sobre la climatología horaria porque captura si el régimen sinóptico/mesoescalar del día está adelantado, retrasado o perturbado.

---

## Afirmación 4: La mejor vecina no es la más cercana (caso Cortadera y red general)

> **Afirmación**: _«La mejor vecina no es la más cercana (Cortadera se predice mejor desde Alto_Tala, Tala-1 y Papujune).»_

### Veredicto: **Parcial**

La tesis general **se sostiene en la mayoría de la red** (en 5 de las 8 estaciones la vecina limpia más cercana no es la #1 ni en todas las horas ni en el norte, y en `Altarani`, `Cortadera` y `Papujune` la más cercana cae hasta los puestos **#9 y #10**). Sin embargo, hay **tres matices críticos** que el análisis original pasó por alto:
1. **Cuando dos estaciones cercanas comparten piso altitudinal y ambas tienen `D1` (`Alto_Quellaveco` ↔ `Minas_Sur`, a `0.86 km` y `dz = 20 m`), la más cercana SÍ es la #1 absoluta** tanto en todas las horas (`22.9°` y `18.5°`) como en el sector norte (`15.2°` y `22.2°`).
2. **En `Cortadera`, el trío `Alto_Tala, Tala-1, Papujune` salía de ordenar el error de entrenamiento (`cal_tr`)**: en semanas de prueba (`cal_te`, todas las horas), **`Calientes1` (`6.07 km`, `20.8°`) supera a `Tala-1` (`21.2°`) y a `Papujune` (`22.0°`)** como segunda mejor vecina tras `Alto_Tala` (`9.11 km`, `19.3°`). En cambio, **en el sector norte de `Cortadera`**, ni `Alto_Tala` (`64.3°`) ni `Tala-1` (`63.2°`) funcionan: las mejores en prueba son **`Minas_Sur` (`40.4°`)**, **`Papujune` (`50.7°`)** y **`Alto_Quellaveco` (`52.0°`)** a 7–11 km.
3. **El ranking de `CONSENSO.md` incluía un artefacto estadístico (`Sarallenque`)**: `consensus_pairs.py` reportó a `Sarallenque` en el Top 3 de `Altarani` y `Papujune` porque ordenó por error de entrenamiento (`e_tr`) y `Sarallenque` solo tenía datos desde el `2026-09-25 21:00` (~8–11 % de cobertura anual, sobreajustando las 48 celdas con ~7 h por celda).

### Cifras que lo sustentan

#### Tabla 4A — Vecina limpia más cercana (`n_te ≥ 500 h`) frente a las mejores vecinas reales en semanas de prueba (`te`)

| Estación | Vecina limpia más cercana (`km`, `dz`, `D1`) | Error en prueba de la más cercana: `Total / Norte` (Puesto de 16) | Top 3 en prueba — **Todas las horas** (`cal_te`) | Top 3 en prueba — **Sector Norte** (`cal_n_te`) |
|---|---|---|---|---|
| Altarani | `Minas_Sur` (1.40 km, dz=375 m, D1=Sí) | 21.6° / 55.6° (**#9 / #8**) | `Tala-1` (7.8 km: **16.8°**), `Alto_Tala` (8.7 km: **18.1°**), `Charaque` (6.4 km: **18.5°**) | `Sarallenque_MQG` (4.0 km: **46.8°**), `Alto_Tala` (8.7 km: **47.7°**), `Cortadera` (12.1 km: **49.4°**) |
| Alto_Quellaveco | `Minas_Sur` (0.86 km, dz=20 m, D1=Sí) | 22.9° / 15.2° (**#1 / #1**) | `Minas_Sur` (0.9 km: **22.9°**), `Papujune` (5.9 km: **28.4°**), `Sarallenque_MQG` (4.6 km: **34.6°**) | `Minas_Sur` (0.9 km: **15.2°**), `Papujune` (5.9 km: **23.8°**), `Sarallenque_MQG` (4.6 km: **39.2°**) |
| Camp_Quellaveco | `Chancado_primario` (0.65 km, dz=130 m, D1=No) | 15.1° / 36.7° (**#2 / #1**) | `Tala-1` (3.7 km: **14.6°**), `Chancado_primario` (0.7 km: **15.1°**), `Charaque` (2.8 km: **17.9°**) | `Chancado_primario` (0.7 km: **36.7°**), `Altarani` (4.1 km: **41.1°**), `Charaque` (2.8 km: **46.9°**) |
| Cortadera | `Apacheta` (3.99 km, dz=351 m, D1=No) | 25.8° / 55.5° (**#10 / #4**) | `Alto_Tala` (9.1 km: **19.3°**), `Calientes1` (6.1 km: **20.8°**), `Tala-1` (9.4 km: **21.2°**) | `Minas_Sur` (10.8 km: **40.4°**), `Papujune` (7.3 km: **50.7°**), `Alto_Quellaveco` (9.9 km: **52.0°**) |
| Minas_Sur | `Alto_Quellaveco` (0.86 km, dz=20 m, D1=Sí) | 18.5° / 22.2° (**#1 / #1**) | `Alto_Quellaveco` (0.9 km: **18.5°**), `Papujune` (6.7 km: **26.3°**), `Cortadera` (10.8 km: **26.4°**) | `Alto_Quellaveco` (0.9 km: **22.2°**), `Cortadera` (10.8 km: **33.0°**), `Camp_Quellaveco` (3.0 km: **34.2°**) |
| Papujune | `Alto_Tala` (2.00 km, dz=323 m, D1=No) | 27.3° / 31.6° (**#9 / #7**) | `Alto_Quellaveco` (5.9 km: **17.2°**), `Minas_Sur` (6.7 km: **22.7°**), `Cortadera` (7.3 km: **24.0°**) | `Alto_Quellaveco` (5.9 km: **20.6°**), `Minas_Sur` (6.7 km: **21.3°**), `Tala-1` (2.1 km: **27.5°**) |
| Tala-1 | `Alto_Tala` (1.03 km, dz=114 m, D1=No) | 14.4° / 34.1° (**#1 / #6**) | `Alto_Tala` (1.0 km: **14.4°**), `Altarani` (7.8 km: **16.2°**), `Papujune` (2.1 km: **16.2°**) | `Tala_Legal` (1.6 km: **28.4°**), `Charaque` (2.4 km: **32.1°**), `Minas_Sur` (6.6 km: **32.5°**) |
| Tala_Legal | `Alto_Tala` (0.69 km, dz=148 m, D1=No) | 13.9° / 33.3° (**#2 / #2**) | `Tala-1` (1.6 km: **13.5°**), `Alto_Tala` (0.7 km: **13.9°**), `Charaque` (3.8 km: **14.1°**) | `Camp_Quellaveco` (5.3 km: **30.2°**), `Alto_Tala` (0.7 km: **33.3°**), `Sarallenque_MQG` (8.0 km: **35.2°**) |

#### Tabla 4B — Detalle de las 10 principales vecinas de `Cortadera` (ordenadas por `cal_te`)

| Vecina | Distancia (km) | $\Delta z$ vs Cortadera (m) | ¿Tiene `D1`? | Horas prueba (`n_te`) | Error crudo `raw_te` (°) | Error entren. `cal_tr` (°) | Error prueba `cal_te` (°) | Error prueba Norte `cal_norte_te` (°) |
|---|---:|---:|:---:|---:|---:|---:|---:|---:|
| `Alto_Tala` | 9.11 | +69 | No (`Avg`) | 2824 | 32.4 | 19.3 | **19.3** | 64.3 |
| `Calientes1` | 6.07 | −288 | No (`Avg`) | 3297 | 28.1 | 21.4 | **20.8** | 60.3 |
| `Tala-1` | 9.42 | +183 | Sí | 3250 | 29.2 | 21.0 | **21.2** | 63.2 |
| `Tala_Legal` | 9.39 | −79 | Sí | 3185 | 37.4 | 21.5 | 21.6 | 63.5 |
| `Papujune` | 7.31 | +392 | Sí | 2805 | 37.9 | 21.2 | **22.0** | **50.7** |
| `Minas_Sur` | 10.75 | +734 | Sí | 1596 | 36.3 | 21.7 | 22.6 | **40.4** |
| `Altarani` | 12.06 | +359 | Sí | 3239 | 51.1 | 23.4 | 23.2 | 59.7 |
| `Charaque` | 11.28 | +252 | No (`Avg`) | 3279 | 30.2 | 23.5 | 24.4 | 68.1 |
| `Camp_Quellaveco` | 9.97 | +213 | Sí | 2548 | 37.6 | 25.4 | 25.2 | 57.3 |
| `Apacheta` (más cercana) | 3.99 | +351 | No (`Avg`) | 3013 | 50.3 | 26.7 | **25.8 (#10)** | 55.5 |

### Explicación
- La proximidad horizontal (`km`) falla cuando cruza **unidades topográficas o pisos altitudinales (`dz > 300 m`)**: `Altarani` (fondo de valle encajonado) está a solo `1.40 km` horizontales de `Minas_Sur`, pero `375 m` más abajo; de noche `Altarani` drena por su ladera SE mientras `Minas_Sur` sigue el régimen alto, y en cambio `Tala-1` y `Charaque` (a 6.4–7.8 km) comparten el ciclo térmico de valle.
- Además, para predecir el **sector norte**, una vecina sin `D1` (como `Alto_Tala` o `Apacheta`) pierde resolución justo cuando el viento cruza 0°/360° porque su propio predictor `src` es un `WindDir_Avg` distorsionado; por eso en el norte de `Cortadera` y `Papujune` ganan estaciones a 6–11 km que tienen `D1` y alta frecuencia de viento norte (`Minas_Sur`, `Alto_Quellaveco`, `Papujune`).

---

## Afirmación 5: Efecto de excluir las estaciones defectuosas

> **Afirmación**: _«Excluir las estaciones defectuosas cambió poco porque con 1/d² mandan las 2–3 más cercanas y la calibración absorbe los desfases constantes.»_

### Veredicto: **Parcial (engañosa en su comprobación experimental)**

Es cierto que `1/d²` concentra entre el **50 % y el 75 % del peso en las 2–3 vecinas más cercanas** y que la calibración circular absorbe cualquier rotación constante durante todo el año. Pero la conclusión de que «excluir las estaciones defectuosas cambió poco» se apoya en una comparación defectuosa por **tres motivos**:
1. **La ejecución «sin `--limpio`» de `consensus_calibrated.py` ya había excluido a mano `Dique_pie_botadero` (`df.st != "Dique_pie_botadero"`)**: `Dique_pie_botadero` está a **`0.55 km` de `Tala-1`**, por lo que con `1/d²` acapara el **`59.3 %` de todo el peso de la red en `Tala-1`**. Si se incluye `Dique_pie_botadero` (Escenario A), el error del IDW en `Tala-1` se dispara de **`24.4° → 62.1°` en crudo** y de **`14.5° → 23.4°` tras calibrar (+8.9° global, +7.2° en el norte)**. Precisamente porque con `1/d²` manda la más cercana, una vecina errática (no meramente rotada) a `0.55 km` destruye el consenso y la calibración no puede absorberla.
2. **En `Papujune`, excluir `Planta_Concentradora` (a `1.57 km`, `20.6 %` del peso `1/d²`) NO «cambió poco»: ¡empeoró el consenso calibrado en `+7.0°` global y `+14.3°` en el norte (`19.4° / 19.8° → 26.4° / 34.1°`)!**: Como el giro de `+73°` de `Planta_Concentradora` ocurrió en abril de 2024, durante todo `2025-11 → 2026-11` fue un desfase **100 % constante**. La tabla de calibración lo absorbía a la perfección y aprovechaba su cercanía a `Papujune`; al excluirla en `--limpio`, el IDW de `Papujune` perdió a su vecina más cercana y quedó dominado por `Alto_Tala` (`2.00 km`, otro piso altitudinal y sin `D1`).
3. **Una tabla de calibración estática NO absorbe giros que ocurren a mitad del año (cambios de escalón en septiembre 2026)**: Cuando `Alto_Quellaveco` (a `0.86 km` de `Minas_Sur`, `51.6 %` de su peso) gira ~90°–120° el `2026-09-15`, la calibración entrenada en todo el año aplica el desfase antiguo (y viceversa, contamina las celdas de entrenamiento con un mes rotado).

### Cifras que lo sustentan

#### Tabla 5A — Impacto en el IDW (`consensus_calibrated.py`) evaluado exactamente sobre las **mismas horas limpias de prueba (`te`)**
*(Formato: `IDW_Crudo → Calibrado_Total / Calibrado_Norte` en grados)*

| Estación | Vecina más cercana en red bruta (`% peso 1/d²`) | Escenario A: Todas (con `Dique_pie_botadero`) | Escenario B: Sin `Dique` (`calib.py` sin `--limpio`) | Escenario C: `--limpio` pero con `Planta_Conc.` | Escenario E: `--limpio` pero con giros sept-2026 | Escenario D: `--limpio` completo (`calib.py --limpio`) |
|---|---|---|---|---|---|---|
| Altarani | `Minas_Sur` (1.40 km, 41.4 %) | 59.4 → 20.0 / 55.6 | 58.3 → 19.5 / 52.2 | 51.7 → 18.4 / 53.5 | 57.8 → 19.9 / 53.8 | 51.8 → **18.3** / 53.8 |
| Alto_Quellaveco | `Minas_Sur` (0.86 km, 57.1 %) | 39.6 → 32.6 / 31.9 | 39.0 → 32.5 / 32.2 | 37.9 → 33.0 / 32.2 | 39.7 → 33.5 / 33.4 | 38.8 → 33.7 / 33.7 |
| Camp_Quellaveco | `Chancado_prim.` (0.65 km, 61.7 %) | 45.9 → 13.2 / 42.1 | 47.3 → 13.1 / 40.6 | 43.8 → 13.1 / 37.7 | 48.2 → 13.0 / 39.9 | 45.7 → **12.8 / 37.8** |
| Cortadera | `Apacheta` (3.99 km, 17.2 %) | 33.5 → 20.7 / 46.1 | 32.8 → 20.6 / 47.2 | 24.7 → 19.0 / 49.9 | 28.6 → 19.2 / 53.4 | 28.0 → 19.2 / 53.3 |
| Minas_Sur | `Alto_Quellaveco` (0.86 km, 51.6 %) | 36.6 → 22.7 / 26.9 | 36.6 → 22.4 / 26.4 | 35.8 → 22.4 / 29.6 | 37.8 → 22.9 / 27.3 | 36.6 → 22.4 / 30.3 |
| **Papujune** | `Planta_Conc.` (1.57 km, **20.6 %**) | 32.0 → 20.8 / 22.0 | 33.5 → 19.9 / 20.3 | 33.8 → **19.4 / 19.8** | 37.1 → 26.8 / 33.6 | 36.8 → **26.4 / 34.1** |
| **Tala-1** | `Dique_pie_bot.` (0.55 km, **59.3 %**) | **62.1 → 23.4 / 39.8** | 24.4 → **14.3 / 32.3** | 23.3 → 14.4 / 31.7 | 25.7 → 14.8 / 33.1 | 24.4 → 14.5 / 32.6 |
| Tala_Legal | `Alto_Tala` (0.69 km, 63.3 %) | 44.3 → 16.3 / 36.7 | 40.9 → 14.8 / 39.4 | 44.0 → 14.7 / 32.7 | 42.2 → 15.3 / 39.0 | 44.4 → 15.0 / 34.9 |

### Explicación
- Hay que distinguir entre **tres tipos de fallo en una vecina**:
  1. **Señal errática o destruida (`Dique_pie_botadero`)**: Si está cerca (`0.55 km` de `Tala-1`, `59.3 %` del peso), ningún desfase constante puede calibrar ruido; excluirla es obligatorio y reduce el error calibrado en `8.9°`.
  2. **Sesgo de orientación constante en todo el periodo (`Planta_Concentradora`, `+73°` desde 2024)**: Es inofensiva (e incluso útil) si el método lleva calibración circular (`Papujune` mejora `7.0°` global y `14.3°` en norte al conservarla), pero tóxica en un IDW crudo sin calibrar.
  3. **Giro brusco a mitad de la ventana (`Cortadera` el `2026-09-13`, `Alto_Quellaveco` el `2026-09-15`, `Sarallenque` el `2026-09-25`, `Alto_Tala` en ago-sept)**: Una calibración estática anual mezcla el régimen pre-giro y post-giro; hay que partir la serie en el salto o excluir el tramo desplazado.

---
## Corrección concreta: Pesos de `consensus_pairs.py` con validación interna

### Diagnóstico del problema en `consensus_pairs.py`
En `consensus_pairs.py` (líneas 48–51), el peso de cada vecina `wgt = 1 / max(e_tr, 5) ** 2` se evalúa sobre las mismas semanas pares (`tr`, `week == 0`) usadas para estimar las 48 celdas de desfase (`16 sectores × 3 franjas`). Esto produce **dos sesgos**:
1. **Sobreajuste de muestras pequeñas (`e_tr` artificialmente bajo)**: Una estación con pocas horas operativas reparte pocas muestras entre las 48 celdas (muchas celdas con $n = 1\text{–}3$ horas tienen error residual in-sample casi nulo). En particular, **`Sarallenque`** (que con `--limpio` solo tiene datos desde el `2026-09-25 21:00`, apenas el **8 %–16 %** de las horas de entrenamiento) obtiene errores in-sample `e_tr` de `15.4°–15.9°`, colándose falsamente en el Top 3 de `Altarani` y `Papujune`.
2. **Omisión de la cobertura temporal al normalizar `1 / error²`**: El promedio `ang(pred[tr], truth[tr]).mean()` ignora los `NaN`. Una vecina que solo estuvo activa 5 semanas (o que en validación deja celdas vacías) recibe el mismo denominador de escala que una estación con 52 semanas completas.

### Tres variantes de validación interna evaluadas (usando solo semanas pares `week == 0`)
- **`M0_Original` (`consensus_pairs.py --limpio`)**: Calibra y mide `e_tr` en todas las semanas pares (`week == 0`).
- **`M1a_Val_Split (tabla_sub)`**: Calibra la tabla en semanas pares de índice par (`week_num % 4 == 0`, semanas 0, 4, 8…), mide `e_val` en las semanas pares restantes (`week_num % 4 == 2`, semanas 2, 6, 10…) y evalúa en prueba (`week == 1`) con la tabla entrenada en esa mitad (`week_num % 4 == 0`).
- **`M1b_Val_Split (tabla_tr)`**: Calcula los pesos `1 / max(e_val, 5)²` mediante la partición interna (`week_num % 4 == 0` → `week_num % 4 == 2`), y luego reajusta los desfases con todas las semanas pares (`week == 0`) para no perder la mitad de las muestras al predecir prueba (`week == 1`).
- **`M1c_Val_2Fold+Cob`**: Validación cruzada interna de 2 pliegues sobre las semanas pares (`week_num % 4 == 0` ↔ `week_num % 4 == 2`), con regularización bayesiana para muestras pequeñas (`e_cv_shrunk = (n·e_cv + 50·45°) / (n + 50)`) y ponderada por la cobertura efectiva de validación (`w = cobertura / e_cv_shrunk²`).

#### Tabla 6A — Cambio en las cifras de prueba por estación (`te`, semanas impares, formato `todas / norte` en grados)

| Estación | `M0_Original` (in-sample `e_tr`) | `M1a_Val_Split` (tabla en mitad de `tr`) | `M1b_Val_Split` (pesos out-of-sample, tabla en `tr`) | `M1c_Val_2Fold+Cob` (CV interna 2-fold + cobertura) | Cambio `M0 → M1b` (`todas / norte`) | Cambio `M0 → M1a` (`todas / norte`) |
|---|---:|---:|---:|---:|---:|---:|
| Altarani | 15.8 / 50.5 | 16.0 / 50.4 | 15.8 / **50.1** | 15.9 / 50.9 | 0.0° / **−0.4°** | +0.2° / −0.1° |
| Alto_Quellaveco | 36.9 / 33.5 | 39.1 / **28.3** | 37.1 / 33.8 | 38.2 / 36.0 | +0.2° / +0.3° | +2.2° / **−5.2°** |
| Camp_Quellaveco | 14.9 / 41.2 | 15.7 / 45.1 | 15.0 / 41.3 | 15.0 / **41.2** | +0.1° / +0.1° | +0.8° / +3.9° |
| Cortadera | 19.8 / 46.1 | 20.8 / **45.2** | **19.7** / 46.1 | 19.9 / 46.8 | **−0.1°** / 0.0° | +1.0° / **−0.9°** |
| Minas_Sur | 25.7 / 31.1 | 25.8 / **26.4** | 25.7 / **31.0** | 26.2 / 31.8 | 0.0° / **−0.1°** | +0.1° / **−4.7°** |
| Papujune | 21.6 / 22.1 | 22.5 / **18.8** | 21.6 / 22.2 | 21.9 / 22.4 | 0.0° / +0.1° | +0.9° / **−3.3°** |
| Tala-1 | 14.1 / 22.4 | 14.4 / 22.6 | 14.1 / 22.4 | 14.2 / 22.5 | 0.0° / 0.0° | +0.3° / +0.2° |
| Tala_Legal | 13.6 / 28.6 | 14.6 / **28.5** | 13.7 / 28.6 | 13.7 / 28.6 | +0.1° / 0.0° | +1.0° / −0.1° |

#### Tabla 6B — Qué vecinas ganan o pierden peso y cómo cambia el Top 3 por estación

| Estación objetivo | Top 3 en `M0_Original` (% del peso total, `e_tr`) | Top 3 en `M1b_Val_Split` (% del peso, `e_val`) | Top 3 en `M1c_CV+Cob` (% del peso, `e_cv`, cobertura) | Mayor caída de peso (`M1b` / `M1c` vs `M0`) | Mayor subida de peso (`M1b` / `M1c` vs `M0`) |
|---|---|---|---|---|---|
| **Altarani** | `Tala-1` (9.3%, 14.9°), `Charaque` (8.5%, 15.5°), **`Sarallenque` (8.1%, 15.9°)** | `Tala-1` (9.2%, 15.8°), `Charaque` (8.1%, 16.8°), `Sarallenque` (7.6%, 17.4°) | `Tala-1` (11.1%, 15.5°, 98%), `Charaque` (10.2%, 16.1°, 99%), **`Tala_Legal` (8.1%, 18.1°, 97%)** | **`Sarallenque`**: −0.5 pp en Split (`15.9°→17.4°`); **−7.5 pp** en CV+Cob (cob=9%) | `Minas_Sur` (+0.5 pp) / **`Tala-1` (+1.8 pp)** |
| **Alto_Quellaveco** | `Minas_Sur` (23.3%, 19.9°), `Papujune` (11.9%, 27.8°), `Sarallenque_MQG` (7.6%, 34.7°) | `Minas_Sur` (22.5%, 21.4°), `Papujune` (11.4%, 30.0°), `Sarallenque_MQG` (7.4%, 37.4°) | `Minas_Sur` (12.6%, 21.1°, 47%), `Papujune` (12.5%, 29.5°, 87%), `Sarallenque_MQG` (9.2%, 37.0°, 100%) | **`Minas_Sur`**: −0.8 pp en Split (`19.9°→21.4°`); **−10.7 pp** en CV+Cob (cob=47%, desde abr-22) | `Apacheta` (+0.6 pp) / **`Sarallenque_MQG` (+1.6 pp)** |
| **Camp_Quellaveco** | `Tala-1` (9.9%, 14.3°), `Chancado_prim.` (9.5%, 14.6°), `Charaque` (7.6%, 16.3°) | **`Chancado_prim.` (9.8%, 17.4°)**, `Tala-1` (9.8%, 17.4°), `Charaque` (7.7%, 19.7°) | `Tala-1` (10.6%, 15.4°, 98%), `Chancado_prim.` (10.3%, 15.6°, 98%), `Charaque` (8.4%, 17.4°, 98%) | **`Sarallenque`**: **−1.4 pp** en Split (`30.1°→60.6°`); **−2.1 pp** en CV+Cob (cob=8%) | `Tala_Legal` (+0.5 pp) / **`Charaque` (+0.9 pp)** |
| **Cortadera** | `Alto_Tala` (9.5%, 19.3°), `Tala-1` (8.1%, 21.0°), **`Papujune` (8.0%, 21.2°)** | `Alto_Tala` (9.7%, 20.1°), **`Calientes1` (8.6%, 21.4°)**, `Tala-1` (8.2%, 21.9°) | **`Calientes1` (8.8%, 22.3°, 100%)**, `Tala-1` (8.7%, 22.1°, 98%), `Alto_Tala` (8.5%, 20.8°, 85%) | `Camp_Quellaveco` (−0.5 pp en Split) / `Minas_Sur` (−4.1 pp en CV+Cob, cob=47%) | **`Calientes1` (+0.8 pp en Split / +1.0 pp en CV+Cob)**, entra al Top 2/Top 1 |
| **Minas_Sur** | `Alto_Quellaveco` (15.5%, 16.8°), `Papujune` (7.2%, 24.7°), `Cortadera` (6.5%, 26.1°) | `Alto_Quellaveco` (15.4%, 18.8°), `Papujune` (7.2%, 27.5°), `Cortadera` (6.8%, 28.2°) | `Alto_Quellaveco` (12.5%, 18.7°, 75%), **`Sarallenque_MQG` (7.7%, 28.3°, 100%)**, `Papujune` (7.5%, 26.9°, 90%) | **`Sarallenque`**: **−2.0 pp** en Split (`28.4°→39.4°`); **−4.8 pp** en CV+Cob (cob=16%) | `Cerro_Salviani` (+0.6 pp) / **`Sarallenque_MQG` (+1.3 pp)** |
| **Papujune** | `Alto_Quellaveco` (11.7%, 17.0°), `Minas_Sur` (8.0%, 20.5°), **`Sarallenque` (7.2%, 21.7°)** | `Alto_Quellaveco` (11.7%, 19.2°), `Minas_Sur` (7.0%, 24.9°), **`Tala-1` (6.5%, 25.8°)** | `Alto_Quellaveco` (11.8%, 18.0°, 83%), **`Tala-1` (7.5%, 25.0°, 99%)**, **`Tala_Legal` (7.0%, 25.7°, 98%)** | `Minas_Sur` (−1.0 pp en Split, `20.5°→24.9°`); **`Sarallenque`** (−0.8 pp en Split y **−6.6 pp** en CV+Cob, sale del Top 3 en ambos) | `Cerro_Salviani` (+0.5 pp) / **`Sarallenque_MQG` (+1.3 pp)** y **`Tala-1`** entra al Top 3 |
| **Tala-1** | `Alto_Tala` (9.4%, 14.6°), `Papujune` (8.5%, 15.3°), `Charaque` (8.5%, 15.3°) | `Alto_Tala` (10.4%, 14.8°), `Papujune` (8.8%, 16.1°), `Charaque` (8.6%, 16.3°) | **`Charaque` (10.2%, 15.9°, 99%)**, **`Altarani` (9.9%, 16.2°, 98%)**, `Alto_Tala` (9.3%, 15.4°, 85%) | **`Sarallenque`**: **−2.2 pp** en Split (`15.8°→20.0°`); **−7.3 pp** en CV+Cob (cob=9%) | **`Alto_Tala` (+1.0 pp)** en Split / **`Charaque` (+1.8 pp)** en CV+Cob |
| **Tala_Legal** | `Tala-1` (10.6%, 12.4°), `Charaque` (9.7%, 13.0°), `Alto_Tala` (9.4%, 13.2°) | **`Charaque` (10.6%, 14.2°)**, `Tala-1` (10.2%, 14.4°), `Alto_Tala` (8.6%, 15.8°) | `Tala-1` (11.5%, 13.8°, 99%), `Charaque` (11.3%, 13.8°, 99%), `Alto_Tala` (8.3%, 15.1°, 86%) | **`Sarallenque`**: **−2.0 pp** en Split (`15.4°→20.8°`); **−6.6 pp** en CV+Cob (cob=10%) | **`Charaque` (+0.9 pp en Split / +1.7 pp en CV+Cob)** |

### Conclusiones de la corrección de pesos
1. **Quién pierde y quién gana peso**:
   - **`Sarallenque` es la gran perdedora en toda la red**: en validación interna `M1b` su error real fuera de muestra salta de `30.1° → 60.6°` en `Camp_Quellaveco`, de `28.4° → 39.4°` en `Minas_Sur`, de `15.8° → 20.0°` en `Tala-1` y de `15.4° → 20.8°` en `Tala_Legal` (perdiendo entre `0.5` y `2.2` puntos porcentuales solo por sobreajuste de celdas, y entre `2.1` y `7.5` pp al ponderar por su cobertura real del 8 %–16 %, saliendo inmediatamente del Top 3 de `Papujune` y `Altarani`).
   - **En `Cortadera`, `Calientes1` sube al Top 2 en `M1b` (+0.8 pp) y al Top 1 en `M1c` (+1.0 pp)**, desplazando a `Papujune` del Top 3 global.
   - **Las estaciones con serie anual limpia y estable (`Tala-1`, `Charaque`, `Calientes1`, `Sarallenque_MQG-15-02`) son las que más peso ganan** (`+0.8` a `+1.8` pp).
2. **Por qué las cifras finales de error en prueba (`M0` vs `M1b`/`M1c`) apenas cambian (`≤ 0.3°`)**:
   - Porque `1 / error²` sobre 16 vecinas cuyos errores están entre `15°` y `35°` reparte el peso de forma **muy plana** (la mejor vecina apenas lleva el `9 %–11 %` del peso total en 6 de las 8 estaciones, y las 16 vecinas votan a la vez). Aunque `Sarallenque` tenía un peso inflado (`7 %–8 %`), solo está presente en las últimas 5 semanas del año (`~10 %` de las horas de prueba), por lo que en el `90 %` restante del año su voto era `NaN` y no intervenía.
   - Eso demuestra que el verdadero cuello de botella de `consensus_pairs.py` no era solo el cálculo in-sample de `e_tr`, sino **ponderar todas las celdas `(sector × franja)` de una vecina con el mismo escalar global `1/e²`**.

---
## Propuesta de método mejorado (mismas semanas impares de prueba `te`)

A partir de los fallos diagnosticados en las Afirmaciones 1–5 y en la validación interna de pesos, evaluamos sobre las **mismas semanas impares de prueba (`week == 1`)** tres mejoras progresivas entrenadas exclusivamente en las semanas pares (`week == 0`):

1. **`M2b_Rcelda_CV_Regimen` (Ponderación por concentración circular de celda $R_{s,k}$ y error CV por régimen)**:
   - En `consensus_pairs.py`, todas las celdas `(sector × franja)` de una vecina pesan igual, aunque en una celda la relación sea unidireccional ($R_{s,k} = |\bar{z}_{s,k}| \approx 0.95$) y en otra sea bimodal o ruidosa ($R_{s,k} \approx 0.2$, como el drenaje nocturno de `Altarani` frente a `Tala-1`).
   - Ponderar cada predicción instantánea por $R_{s,k}^3 \cdot \left(\frac{n_{s,k}}{n_{s,k}+10}\right)^3$ multiplicado por el peso de validación cruzada interna (2-fold CV) desglosado según si el consenso preliminar apunta o no al sector norte (`|c| ≤ 55°`).
2. **`M2_Top5_Rcelda_CV` (Selección de las Top-5 vecinas por validación interna 2-fold CV + concentración $R_{s,k}^3$ + fallback jerárquico de celda)**:
   - Elimina la cola de 11 vecinas mediocres que diluyen el promedio vectorial (cuyo peso acumulado en `1/e²` suma >50 % del voto total), usa el desfase del sector global cuando una celda `(sector × franja)` tiene $n < 5$ muestras en entrenamiento, y pondera las Top-5 vecinas validadas por $R_{s,k}^3 / e_{\text{cv}}^3$.
3. **`M3_Hibrido_Ciego` (Uso selectivo del consenso solo cuando `WindDir_Avg` muestra firma de cruce por el norte)**:
   - Como demostró la Afirmación 1, fuera del sector norte `WindDir_Avg` tiene un error de `3.5°–6.1°` (`11.3°` en `Minas_Sur`) que ningún consenso espacial puro (`12.8°–36.9°`) puede batir. Reemplazar `WindDir_Avg` por el consenso en **todas** las horas destruye las horas limpias fuera del norte.
   - La regla híbrida ciega (sin usar `D1`) conserva `WindDir_Avg` por defecto y solo lo sustituye por el consenso por pares cuando el consenso indica sector norte (`|consenso| ≤ 55°`) y `WindDir_Avg` discrepa fuertemente (`|WindDir_Avg − consenso| > 55°` y `|WindDir_Avg| > 45°`).

#### Tabla 7 — Comparación de métodos propuestos frente a `consensus_pairs.py` y `WindDir_Avg` (semanas impares de prueba `te`, formato `todas / norte` en grados)

| Estación | `WindDir_Avg` propio | `M0_Original` (`consensus_pairs.py`) | `M1b_Val_Split` (pesos validados) | `M2b_Rcelda_CV_Regimen` (todas las vecinas, $R_{s,k}^3$) | `M2_Top5_Rcelda_CV` (Top-5 CV + $R_{s,k}^3$ + fallback) | `M3_Hibrido_Ciego` (`Avg` + consenso solo en cruces N) |
|---|---:|---:|---:|---:|---:|---:|
| Altarani | 7.8 / 66.7 | **15.8** / 50.5 | **15.8 / 50.1** | 16.1 / 58.8 | 16.6 / 62.9 | **7.7** / 59.1 |
| Alto_Quellaveco | 16.0 / 39.3 | 36.9 / 33.5 | 37.1 / 33.8 | 34.4 / 28.0 | **28.2 / 20.9** | **12.7** / 34.2 |
| Camp_Quellaveco | 10.0 / 95.4 | 14.9 / **41.2** | 15.0 / 41.3 | 14.4 / 46.8 | **13.8** / 44.2 | 11.0 / 61.9 |
| Cortadera | 9.8 / 72.5 | 19.8 / **46.1** | 19.7 / **46.1** | 20.1 / 60.0 | **19.3** / 61.3 | 10.5 / 60.4 |
| Minas_Sur | 33.7 / 81.2 | 25.7 / 31.1 | 25.7 / 31.0 | 25.9 / 32.5 | **21.8 / 26.0** | **24.8** / 44.8 |
| Papujune | 17.4 / 57.1 | 21.6 / 22.1 | 21.6 / 22.2 | 21.9 / 21.6 | **19.2 / 19.7** | **12.1** / 26.9 |
| Tala-1 | 9.7 / 50.2 | 14.1 / **22.4** | 14.1 / **22.4** | 14.5 / 28.9 | **13.9** / 30.7 | **8.6** / 31.3 |
| Tala_Legal | 7.1 / 71.1 | 13.6 / **28.6** | 13.7 / **28.6** | 13.7 / 34.1 | **12.8** / 37.1 | 7.2 / 48.0 |

### Qué aporta cada método y qué limitación tiene
1. **`M2_Top5_Rcelda_CV` mejora el error global del consenso espacial en 7 de las 8 estaciones** y logra las mayores ganancias donde el viento del norte es un régimen real y frecuente (`Alto_Quellaveco`: **`36.9° / 33.5° → 28.2° / 20.9°`**, −8.7° total y −12.6° en norte; `Minas_Sur`: **`25.7° / 31.1° → 21.8° / 26.0°`**, −3.9° / −5.1°; `Papujune`: **`21.6° / 22.1° → 19.2° / 19.7°`**, −2.4° / −2.4°).
   - *Por qué pierde en el norte de estaciones con poco norte (`Altarani` 6 % norte, `Cortadera` 8.5 %, `Tala_Legal` 4.7 %)*: En esas estaciones, el viento rara vez se estabiliza en el norte; las horas con `|D1| ≤ 45°` caen dentro de celdas de transición o abanico nocturno cuya concentración circular $R_{s,k}$ es baja. Al ponderar por $R_{s,k}^3$, ganan peso las vecinas que están en celdas diurnas/drenaje muy concentradas (que apuntan fuera del norte). Por tanto, **$R_{s,k}^3$ con Top-5 debe usarse en estaciones de régimen norte frecuente (>20 % de las horas)**, mientras que en estaciones donde el norte es una transición esporádica (<12 % de las horas) conviene mantener el voto no penalizado por $R_{s,k}^3$ (`M1b_Val_Split`).
2. **`M3_Hibrido_Ciego` es el único esquema horario que mejora simultáneamente el error global de toda la serie respecto a `WindDir_Avg` propio** en las 5 estaciones con más problemas de cruce por el norte (`Minas_Sur` `33.7° → 24.8°`, `Papujune` `17.4° → 12.1°`, `Alto_Quellaveco` `16.0° → 12.7°`, `Tala-1` `9.7° → 8.6°`, `Altarani` `7.8° → 7.7°`), confirmando que el consenso espacial debe emplearse como **detector/prior de régimen norte** y nunca como sustituto indiscriminado de `WindDir_Avg` fuera del norte.

---

## Resumen de veredictos y archivos generados

| Punto del encargo | Veredicto | Hallazgo clave en una línea |
|---|---|---|
| **Afirmación 1** (`WindDir_Avg` fuera del norte) | **Parcial** | El error real fuera del norte es `3.7°–5.7°` (`12.1°` en `Minas_Sur`), no `7–17°`; pero hay un `3.3 %–13.2 %` de horas con `\|D1\|>45°` y cruce parcial (`SD1 ~ 50–65°`) donde `Avg` falla `49–58°` y el consenso lo bate en 8/8 estaciones. |
| **Afirmación 2** (Fallo de `25–58°` del IDW crudo) | **Parcial** | Los flujos locales imponen un suelo de `23°–51°`, pero en el sector norte hasta `36°–50°` del error del IDW crudo vienen de meter vecinas sin `D1` cuyo `WindDir_Avg` está invertido (~180°). |
| **Afirmación 3** (Pares mejora el norte en 6/8) | **Parcial** | Aritméticamente cierto si se entrena con el oráculo `D1`, pero si se entrena en estaciones que solo tienen `WindDir_Avg` (incluso filtrando horas limpias `\|A\|>45°`) falla `60°–106°` en el norte porque las celdas de flujo norte quedan sesgadas o vacías. |
| **Afirmación 4** (Mejor vecina ≠ más cercana) | **Parcial** | Cierto cuando hay salto altitudinal (`dz > 300 m`) o vecina sin `D1`, pero falso en `Alto_Quellaveco ↔ Minas_Sur` (`0.86 km`, `dz=20 m`, #1 en todo); en `Cortadera`, `Calientes1` es #2 en prueba global (`20.8°`) y `Minas_Sur` es #1 en el norte (`40.4°`). |
| **Afirmación 5** (Excluir defectuosas cambió poco) | **Parcial** | Engañoso: `calib.py` sin `--limpio` ya excluía `Dique_pie_botadero` (`59.3 %` del peso en `Tala-1`; incluirla empeora `Tala-1` de `14.5°` a `23.4°`), y excluir `Planta_Concentradora` (desfase constante de `+73°`) empeoró `Papujune` de `19.4°/19.8°` a `26.4°/34.1°`. |
| **Corrección de pesos** (`consensus_pairs.py`) | **Corregido** | La validación interna desmonta el sobreajuste de `Sarallenque` (`e_tr=15–30° → e_val=17–61°`, cae hasta `−7.5 pp` con cobertura y sale del Top 3), sube a `Calientes1` al Top 1–2 de `Cortadera`, y cambia el error global en `≤ 0.3°` por el reparto plano de `1/e²` entre 16 vecinas. |

- **Script reproducible**: [`explorar_qaqc/wind_vector/consensus/audit/r1/r1_audit.py`](file:///C:/Users/gfigueroa/OneDrive%20-%20greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc/wind_vector/consensus/audit/r1/r1_audit.py)
- **Informe completo**: [`explorar_qaqc/wind_vector/consensus/audit/r1/INFORME.md`](file:///C:/Users/gfigueroa/OneDrive%20-%20greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc/wind_vector/consensus/audit/r1/INFORME.md)
