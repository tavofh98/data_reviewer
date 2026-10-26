# Informe de carga y alineación de viento

Generado por `wind_vector/build_load_report.py`. Todas las cifras salen de los datos.

- Convención: el TIMESTAMP de Campbell es el fin del intervalo; la hora HH:00 agrupa los registros de 5 min HH-1:05 (m01) ... HH:00 (m12).
- Registro de 5 min válido: WS_ms_Avg y WindDir_Avg no nulos. Hora completa: `n_5min` = 12.
- Tolerancias: dirección 0.1° (redondeo FP2); velocidad 0.01 m/s.
- La prueba de consistencia solo se evalúa en horas completas: las incompletas no pueden compararse (faltan registros), así que NaN y huecos quedan fuera de ese porcentaje.

## Cortadera

### Tablas cargadas

| Tabla | Desde | Hasta | Filas en fichero | Timestamps duplicados (filas sobrantes) | Duplicados con viento distinto | Filas tras deduplicar | Fuera de rejilla |
|---|---|---|---|---|---|---|---|
| 5 min (Table3) | 2023-01-30 17:30:00 | 2026-10-21 11:30:00 | 391830 | 2384 | 0 | 389446 | 0 |
| 60 min (Table1) | 2023-01-30 19:00:00 | 2026-10-21 09:00:00 | 32687 | 229 | 0 | 32458 | 0 |

Qué se hizo: de cada timestamp duplicado se conserva el último registro en orden de fichero (ver docstring de `loader._deduplicate`) y se ordena por tiempo.

### Horas

- Horas en la tabla de 60 min: 32458.
- Con los 12 registros de 5 min válidos: 32305 (99.53 %).
- Incompletas: 153 (0.47 %); de ellas sin ningún registro de 5 min: 0.
- Horas con WS_ms_Avg_h o WindDir_Avg_h nulos en la tabla de 60 min: 0.
- Distribución de `n_5min`: 1: 2, 2: 3, 3: 5, 4: 6, 5: 7, 6: 8, 7: 12, 8: 15, 9: 32, 10: 36, 11: 27, 12: 32305.

### Huecos (>= 6 h son largos)

- Tabla de 5 min: 172 huecos en total, 3 largos.
  - 2026-04-11 12:25:00 -> 2026-04-13 10:15:00 (45.8 h)
  - 2023-08-05 12:55:00 -> 2023-08-06 11:15:00 (22.3 h)
  - 2023-09-18 12:10:00 -> 2023-09-18 18:25:00 (6.2 h)
- Tabla de 60 min: 70 huecos en total, 3 largos.
  - 2026-04-11 11:00:00 -> 2026-04-13 11:00:00 (48.0 h)
  - 2023-08-05 11:00:00 -> 2023-08-06 12:00:00 (25.0 h)
  - 2023-09-18 12:00:00 -> 2023-09-18 19:00:00 (7.0 h)

### Verificación de la convención de tiempo (horas completas)

| Convención | Media de 12 WS_ms_Avg = WS_ms_Avg_h | Máx. de 12 WS_ms_Max = WS_ms_Max_h |
|---|---|---|
| Fin de intervalo (HH-1:05 ... HH:00) | 99.96 % | 99.99 % |
| Inicio de intervalo (HH:00 ... HH:55) | 1.16 % | 3.97 % |

### Prueba de consistencia (horas con los 12 registros)

Horas evaluadas: 32305.

- **WindDir_Avg**: media aritmética de los 12 de 5 min = WindDir_Avg_h (|dif| <= 0.1°): 32295 horas, 99.97 %. Fallan 10.
- **WS_ms_Avg**: media de los 12 de 5 min = WS_ms_Avg_h (|dif| <= 0.01 m/s): 32292 horas, 99.96 %. Fallan 13. (Con tolerancia estricta 0.002 m/s: 99.92 %.)
- Regla de deduplicación alternativa (primer registro en vez del último), cumplimiento de dirección: 99.97 % frente a 99.97 % con el último.

Cruce por el norte (algún WindDir_Avg de 5 min < 90° y otro > 270° en la hora):

| Grupo | Horas | Cumplen dirección |
|---|---|---|
| Con cruce por el norte | 3570 | 100.00 % |
| Sin cruce por el norte | 28735 | 99.97 % |

Por qué falla la dirección (causas excluyentes, por prioridad):

| Causa | Horas |
|---|---|
| WS_ms_Avg también discrepa | 8 |
| WS coincide, sin calma: sin causa identificada | 2 |

Fallos con cruce por el norte: 0 de 10. Error absoluto de los fallos (grados): mediana 0.55, máximo 7.41.

## Papujune

### Tablas cargadas

| Tabla | Desde | Hasta | Filas en fichero | Timestamps duplicados (filas sobrantes) | Duplicados con viento distinto | Filas tras deduplicar | Fuera de rejilla |
|---|---|---|---|---|---|---|---|
| 5 min (Table3) | 2020-11-03 10:55:00 | 2026-10-21 11:30:00 | 833305 | 211875 | 1 | 621430 | 0 |
| 60 min (Table1) | 2020-11-03 11:00:00 | 2026-10-21 09:00:00 | 62147 | 10350 | 0 | 51797 | 0 |

Qué se hizo: de cada timestamp duplicado se conserva el último registro en orden de fichero (ver docstring de `loader._deduplicate`) y se ordena por tiempo.

### Horas

- Horas en la tabla de 60 min: 51797.
- Con los 12 registros de 5 min válidos: 51437 (99.30 %).
- Incompletas: 360 (0.70 %); de ellas sin ningún registro de 5 min: 0.
- Horas con WS_ms_Avg_h o WindDir_Avg_h nulos en la tabla de 60 min: 0.
- Distribución de `n_5min`: 1: 12, 2: 6, 3: 8, 4: 13, 5: 13, 6: 13, 7: 20, 8: 22, 9: 41, 10: 84, 11: 128, 12: 51437.

### Huecos (>= 6 h son largos)

- Tabla de 5 min: 400 huecos en total, 6 largos.
  - 2024-06-02 17:05:00 -> 2024-06-11 18:20:00 (217.2 h)
  - 2023-11-10 09:10:00 -> 2023-11-11 18:40:00 (33.5 h)
  - 2023-04-13 17:15:00 -> 2023-04-14 07:00:00 (13.8 h)
  - 2023-04-14 17:15:00 -> 2023-04-15 07:00:00 (13.8 h)
  - 2023-04-15 17:10:00 -> 2023-04-16 06:55:00 (13.8 h)
- Tabla de 60 min: 122 huecos en total, 10 largos.
  - 2024-06-02 16:00:00 -> 2024-06-11 19:00:00 (219.0 h)
  - 2023-11-10 08:00:00 -> 2023-11-11 19:00:00 (35.0 h)
  - 2023-04-13 17:00:00 -> 2023-04-14 07:00:00 (14.0 h)
  - 2023-04-14 17:00:00 -> 2023-04-15 07:00:00 (14.0 h)
  - 2023-04-15 17:00:00 -> 2023-04-16 07:00:00 (14.0 h)

### Verificación de la convención de tiempo (horas completas)

| Convención | Media de 12 WS_ms_Avg = WS_ms_Avg_h | Máx. de 12 WS_ms_Max = WS_ms_Max_h |
|---|---|---|
| Fin de intervalo (HH-1:05 ... HH:00) | 99.84 % | 99.91 % |
| Inicio de intervalo (HH:00 ... HH:55) | 2.83 % | 4.66 % |

### Prueba de consistencia (horas con los 12 registros)

Horas evaluadas: 51437.

- **WindDir_Avg**: media aritmética de los 12 de 5 min = WindDir_Avg_h (|dif| <= 0.1°): 51346 horas, 99.82 %. Fallan 91.
- **WS_ms_Avg**: media de los 12 de 5 min = WS_ms_Avg_h (|dif| <= 0.01 m/s): 51357 horas, 99.84 %. Fallan 80. (Con tolerancia estricta 0.002 m/s: 99.77 %.)
- Regla de deduplicación alternativa (primer registro en vez del último), cumplimiento de dirección: 99.82 % frente a 99.82 % con el último.

Cruce por el norte (algún WindDir_Avg de 5 min < 90° y otro > 270° en la hora):

| Grupo | Horas | Cumplen dirección |
|---|---|---|
| Con cruce por el norte | 9093 | 99.90 % |
| Sin cruce por el norte | 42344 | 99.81 % |

Por qué falla la dirección (causas excluyentes, por prioridad):

| Causa | Horas |
|---|---|
| WS_ms_Avg también discrepa | 77 |
| WS coincide, sin calma: sin causa identificada | 11 |
| WS coincide; algún registro de 5 min en calma (WS=0) | 3 |

Fallos con cruce por el norte: 9 de 91. Error absoluto de los fallos (grados): mediana 2.94, máximo 197.53.

## Quellaveco

### Tablas cargadas

| Tabla | Desde | Hasta | Filas en fichero | Timestamps duplicados (filas sobrantes) | Duplicados con viento distinto | Filas tras deduplicar | Fuera de rejilla |
|---|---|---|---|---|---|---|---|
| 5 min (Table3) | 2020-11-03 10:45:00 | 2026-10-21 11:30:00 | 641760 | 16914 | 53 | 624846 | 0 |
| 60 min (Table1) | 2020-11-03 11:00:00 | 2026-10-21 09:00:00 | 53548 | 1490 | 0 | 52058 | 0 |

Qué se hizo: de cada timestamp duplicado se conserva el último registro en orden de fichero (ver docstring de `loader._deduplicate`) y se ordena por tiempo.

### Horas

- Horas en la tabla de 60 min: 52058.
- Con los 12 registros de 5 min válidos: 51703 (99.32 %).
- Incompletas: 355 (0.68 %); de ellas sin ningún registro de 5 min: 0.
- Horas con WS_ms_Avg_h o WindDir_Avg_h nulos en la tabla de 60 min: 1.
- Distribución de `n_5min`: 1: 5, 2: 8, 3: 7, 4: 7, 5: 12, 6: 8, 7: 16, 8: 27, 9: 36, 10: 88, 11: 141, 12: 51703.

### Huecos (>= 6 h son largos)

- Tabla de 5 min: 388 huecos en total, 4 largos.
  - 2022-10-27 16:45:00 -> 2022-10-28 08:55:00 (16.2 h)
  - 2021-01-01 22:00:00 -> 2021-01-02 06:45:00 (8.8 h)
  - 2020-12-31 21:55:00 -> 2021-01-01 06:25:00 (8.5 h)
  - 2022-06-24 09:55:00 -> 2022-06-24 17:40:00 (7.8 h)
- Tabla de 60 min: 133 huecos en total, 4 largos.
  - 2022-10-27 16:00:00 -> 2022-10-28 09:00:00 (17.0 h)
  - 2020-12-31 21:00:00 -> 2021-01-01 07:00:00 (10.0 h)
  - 2021-01-01 22:00:00 -> 2021-01-02 07:00:00 (9.0 h)
  - 2022-06-24 09:00:00 -> 2022-06-24 18:00:00 (9.0 h)

### Verificación de la convención de tiempo (horas completas)

| Convención | Media de 12 WS_ms_Avg = WS_ms_Avg_h | Máx. de 12 WS_ms_Max = WS_ms_Max_h |
|---|---|---|
| Fin de intervalo (HH-1:05 ... HH:00) | 99.92 % | 99.98 % |
| Inicio de intervalo (HH:00 ... HH:55) | 1.19 % | 3.69 % |

### Prueba de consistencia (horas con los 12 registros)

Horas evaluadas: 51703.

- **WindDir_Avg**: media aritmética de los 12 de 5 min = WindDir_Avg_h (|dif| <= 0.1°): 51649 horas, 99.90 %. Fallan 54.
- **WS_ms_Avg**: media de los 12 de 5 min = WS_ms_Avg_h (|dif| <= 0.01 m/s): 51662 horas, 99.92 %. Fallan 41. (Con tolerancia estricta 0.002 m/s: 99.47 %.)
- Regla de deduplicación alternativa (primer registro en vez del último), cumplimiento de dirección: 99.81 % frente a 99.90 % con el último.

Cruce por el norte (algún WindDir_Avg de 5 min < 90° y otro > 270° en la hora):

| Grupo | Horas | Cumplen dirección |
|---|---|---|
| Con cruce por el norte | 6747 | 99.96 % |
| Sin cruce por el norte | 44956 | 99.89 % |

Por qué falla la dirección (causas excluyentes, por prioridad):

| Causa | Horas |
|---|---|
| WS_ms_Avg también discrepa | 39 |
| WS coincide, sin calma: sin causa identificada | 15 |

Fallos con cruce por el norte: 3 de 54. Error absoluto de los fallos (grados): mediana 0.80, máximo 66.72.
