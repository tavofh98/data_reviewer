# El sector norte: qué se puede corregir y con qué precisión

Verdad: `WindDir_D1_WVT` horario. Errores circulares en grados. Misma selección de horas que `analyze.py`. V0 = `WindDir_Avg` horario; V1 = vectores unitarios de Avg 5 min; MED = mediana circular de los 12 registros; R*t* = vectores unitarios sin los registros a más de *t*° de la mediana de la hora.


## cortadera

Horas evaluadas: 32305.

### A. Dónde cae en WindDir_Avg el viento que D1 sitúa cerca del norte (registros de 5 min)

| registros de 5 min | n | % con Avg a ≤ 10° de D1 | % con 10–90° | % con > 90° | SD1 mediana |
|---|---|---|---|---|---|
| D1 a ≤ 20° del norte | 14687 | 17.44 | 36.98 | 45.58 | 12.17 |
| D1 a 20–45° del norte | 21264 | 69.68 | 24.71 | 5.62 | 11.17 |
| D1 a > 45° del norte | 349013 | 97.41 | 2.32 | 0.27 | 10.74 |

- Avg a ≤ 20° del norte: 2263
- D1 a ≤ 20° del norte: 14687
- de los Avg cerca del norte, D1 también: 97.4 %
- de los D1 cerca del norte, Avg también: 15.0 %

### B. Heurísticas por hora

| grupo | n | media | mediana | p95 | %>10° | %>30° |
|---|---|---|---|---|---|---|
| todas las horas · V0 WindDir_Avg horario | 32305 | 14.05 | 0.10 | 98.44 | 21.11 | 14.55 |
| todas las horas · V1 unitarios de Avg 5 min | 32305 | 6.33 | 0.10 | 35.97 | 14.25 | 6.02 |
| todas las horas · MED mediana circular de la hora | 32305 | 7.69 | 1.60 | 36.40 | 16.24 | 6.28 |
| todas las horas · R30 sin registros a > 30° de la mediana | 32305 | 7.19 | 0.12 | 37.66 | 16.95 | 6.57 |
| todas las horas · R45 sin registros a > 45° de la mediana | 32305 | 6.82 | 0.11 | 37.96 | 15.71 | 6.63 |
| todas las horas · R60 sin registros a > 60° de la mediana | 32305 | 6.69 | 0.10 | 38.56 | 15.16 | 6.73 |
| real a ≤ 45° del norte · V0 WindDir_Avg horario | 2893 | 83.67 | 87.47 | 170.70 | 82.30 | 72.93 |
| real a ≤ 45° del norte · V1 unitarios de Avg 5 min | 2893 | 40.12 | 23.83 | 143.10 | 69.37 | 43.24 |
| real a ≤ 45° del norte · MED mediana circular de la hora | 2893 | 40.36 | 25.91 | 143.66 | 71.93 | 45.14 |
| real a ≤ 45° del norte · R30 sin registros a > 30° de la mediana | 2893 | 40.70 | 26.07 | 143.75 | 72.66 | 45.25 |
| real a ≤ 45° del norte · R45 sin registros a > 45° de la mediana | 2893 | 41.37 | 27.71 | 142.83 | 74.49 | 46.98 |
| real a ≤ 45° del norte · R60 sin registros a > 60° de la mediana | 2893 | 41.99 | 29.54 | 141.51 | 75.08 | 49.46 |
| real a ≤ 20° del norte · V0 WindDir_Avg horario | 1116 | 118.19 | 132.93 | 175.42 | 95.97 | 90.95 |
| real a ≤ 20° del norte · V1 unitarios de Avg 5 min | 1116 | 60.56 | 42.75 | 163.92 | 82.80 | 60.13 |
| real a ≤ 20° del norte · MED mediana circular de la hora | 1116 | 61.95 | 43.74 | 165.73 | 89.78 | 65.95 |
| real a ≤ 20° del norte · R30 sin registros a > 30° de la mediana | 1116 | 63.02 | 46.07 | 166.34 | 90.77 | 66.49 |
| real a ≤ 20° del norte · R45 sin registros a > 45° de la mediana | 1116 | 63.76 | 47.85 | 164.94 | 91.94 | 69.35 |
| real a ≤ 20° del norte · R60 sin registros a > 60° de la mediana | 1116 | 64.24 | 50.48 | 164.90 | 91.49 | 71.33 |
| real a > 45° del norte · V0 WindDir_Avg horario | 29412 | 7.21 | 0.10 | 51.50 | 15.09 | 8.81 |
| real a > 45° del norte · V1 unitarios de Avg 5 min | 29412 | 3.00 | 0.09 | 17.81 | 8.82 | 2.36 |
| real a > 45° del norte · MED mediana circular de la hora | 29412 | 4.47 | 1.40 | 18.85 | 10.76 | 2.46 |
| real a > 45° del norte · R30 sin registros a > 30° de la mediana | 29412 | 3.90 | 0.10 | 20.44 | 11.47 | 2.77 |
| real a > 45° del norte · R45 sin registros a > 45° de la mediana | 29412 | 3.42 | 0.09 | 19.30 | 9.93 | 2.67 |
| real a > 45° del norte · R60 sin registros a > 60° de la mediana | 29412 | 3.22 | 0.09 | 18.66 | 9.27 | 2.53 |

### C. Precisión al excluir el sector norte

| grupo | n | media | mediana | p95 | %>10° | %>30° | % de las horas |
|---|---|---|---|---|---|---|---|
| real fuera de ±20° del norte (20–340°) · V0 | 31189 | 10.33 | 0.10 | 72.50 | 18.43 | 11.82 | 96.55 |
| real fuera de ±20° del norte (20–340°) · V1 | 31189 | 4.39 | 0.10 | 25.63 | 11.79 | 4.09 | 96.55 |
| real fuera de ±20° del norte (20–340°) · R45 | 31189 | 4.78 | 0.10 | 27.16 | 12.98 | 4.39 | 96.55 |
| real fuera de ±30° · V0 | 30563 | 8.96 | 0.10 | 63.10 | 17.16 | 10.60 | 94.61 |
| real fuera de ±30° · V1 | 30563 | 3.75 | 0.09 | 22.31 | 10.65 | 3.32 | 94.61 |
| real fuera de ±30° · R45 | 30563 | 4.13 | 0.10 | 23.57 | 11.74 | 3.55 | 94.61 |
| real fuera de ±45° · V0 | 29412 | 7.21 | 0.10 | 51.50 | 15.09 | 8.81 | 91.04 |
| real fuera de ±45° · V1 | 29412 | 3.00 | 0.09 | 17.81 | 8.82 | 2.36 | 91.04 |
| real fuera de ±45° · R45 | 29412 | 3.42 | 0.09 | 19.30 | 9.93 | 2.67 | 91.04 |
| real dentro de ±20° · V0 | 1116 | 118.19 | 132.93 | 175.42 | 95.97 | 90.95 | 3.45 |
| real dentro de ±20° · V1 | 1116 | 60.56 | 42.75 | 163.92 | 82.80 | 60.13 | 3.45 |
| real dentro de ±20° · R45 | 1116 | 63.76 | 47.85 | 164.94 | 91.94 | 69.35 | 3.45 |

| regla | horas aceptadas % | V1 media | V1 p95 | V1 %>10° | V1 %>30° | R45 media | R45 %>10° | aceptadas con real ≤ 20° del norte % | aceptadas con real ≤ 45° del norte % | % de los errores V1 > 30° que quedan dentro |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 WindDir_Avg horario en 20–340° | 99.92 | 6.33 | 36.03 | 14.26 | 6.03 | 6.82 | 15.72 | 3.38 | 8.88 | 100.00 |
| R2 los 12 Avg de 5 min en 20–340° | 96.30 | 5.83 | 32.82 | 12.78 | 5.51 | 6.21 | 13.97 | 2.27 | 6.82 | 88.08 |
| R3 R2 y salto máx. entre registros ≤ 60° | 76.99 | 0.62 | 2.85 | 1.34 | 0.18 | 0.93 | 2.12 | 0.06 | 1.74 | 2.26 |
| R4 R2 y dispersión máx. a la mediana ≤ 45° | 71.65 | 0.35 | 1.23 | 0.55 | 0.04 | 0.35 | 0.55 | 0.01 | 1.59 | 0.46 |
| R5 R2 y dispersión ≤ 20° | 52.37 | 0.10 | 0.21 | 0.04 | 0.01 | 0.10 | 0.04 | 0.00 | 1.43 | 0.05 |


## papujune

Horas evaluadas: 49951.

### A. Dónde cae en WindDir_Avg el viento que D1 sitúa cerca del norte (registros de 5 min)

| registros de 5 min | n | % con Avg a ≤ 10° de D1 | % con 10–90° | % con > 90° | SD1 mediana |
|---|---|---|---|---|---|
| D1 a ≤ 20° del norte | 65895 | 19.91 | 42.31 | 37.78 | 10.59 |
| D1 a 20–45° del norte | 81105 | 72.48 | 24.34 | 3.19 | 8.91 |
| D1 a > 45° del norte | 395176 | 92.22 | 7.47 | 0.31 | 16.14 |

- Avg a ≤ 20° del norte: 11653
- D1 a ≤ 20° del norte: 65895
- de los Avg cerca del norte, D1 también: 98.2 %
- de los D1 cerca del norte, Avg también: 17.4 %

### B. Heurísticas por hora

| grupo | n | media | mediana | p95 | %>10° | %>30° |
|---|---|---|---|---|---|---|
| todas las horas · V0 WindDir_Avg horario | 49951 | 28.14 | 3.50 | 138.83 | 40.31 | 28.03 |
| todas las horas · V1 unitarios de Avg 5 min | 49951 | 13.88 | 2.10 | 72.64 | 29.52 | 13.83 |
| todas las horas · MED mediana circular de la hora | 49951 | 14.38 | 3.80 | 71.23 | 30.17 | 12.82 |
| todas las horas · R30 sin registros a > 30° de la mediana | 49951 | 14.10 | 3.11 | 71.04 | 31.01 | 12.99 |
| todas las horas · R45 sin registros a > 45° de la mediana | 49951 | 13.86 | 2.55 | 70.56 | 30.02 | 13.17 |
| todas las horas · R60 sin registros a > 60° de la mediana | 49951 | 13.72 | 2.25 | 70.23 | 29.37 | 13.28 |
| real a ≤ 45° del norte · V0 WindDir_Avg horario | 14623 | 72.79 | 66.18 | 167.70 | 83.00 | 69.40 |
| real a ≤ 45° del norte · V1 unitarios de Avg 5 min | 14623 | 34.91 | 19.47 | 131.44 | 65.97 | 37.69 |
| real a ≤ 45° del norte · MED mediana circular de la hora | 14623 | 33.17 | 16.30 | 134.05 | 62.30 | 33.47 |
| real a ≤ 45° del norte · R30 sin registros a > 30° de la mediana | 14623 | 32.66 | 15.88 | 133.87 | 61.52 | 32.67 |
| real a ≤ 45° del norte · R45 sin registros a > 45° de la mediana | 14623 | 33.10 | 17.11 | 135.31 | 63.50 | 33.91 |
| real a ≤ 45° del norte · R60 sin registros a > 60° de la mediana | 14623 | 33.54 | 17.90 | 135.30 | 64.54 | 35.15 |
| real a ≤ 20° del norte · V0 WindDir_Avg horario | 6616 | 108.81 | 114.70 | 173.70 | 98.37 | 92.96 |
| real a ≤ 20° del norte · V1 unitarios de Avg 5 min | 6616 | 52.09 | 36.61 | 152.37 | 81.61 | 56.12 |
| real a ≤ 20° del norte · MED mediana circular de la hora | 6616 | 51.10 | 32.51 | 155.64 | 84.17 | 52.72 |
| real a ≤ 20° del norte · R30 sin registros a > 30° de la mediana | 6616 | 51.02 | 32.46 | 156.14 | 85.28 | 52.74 |
| real a ≤ 20° del norte · R45 sin registros a > 45° de la mediana | 6616 | 51.45 | 33.88 | 154.94 | 85.88 | 54.82 |
| real a ≤ 20° del norte · R60 sin registros a > 60° de la mediana | 6616 | 51.69 | 35.12 | 155.62 | 84.92 | 55.96 |
| real a > 45° del norte · V0 WindDir_Avg horario | 35328 | 9.66 | 0.80 | 53.71 | 22.64 | 10.90 |
| real a > 45° del norte · V1 unitarios de Avg 5 min | 35328 | 5.18 | 0.69 | 25.51 | 14.43 | 3.95 |
| real a > 45° del norte · MED mediana circular de la hora | 35328 | 6.60 | 2.40 | 26.81 | 16.87 | 4.27 |
| real a > 45° del norte · R30 sin registros a > 30° de la mediana | 35328 | 6.41 | 1.28 | 29.40 | 18.38 | 4.84 |
| real a > 45° del norte · R45 sin registros a > 45° de la mediana | 35328 | 5.89 | 0.82 | 28.44 | 16.15 | 4.58 |
| real a > 45° del norte · R60 sin registros a > 60° de la mediana | 35328 | 5.52 | 0.73 | 26.73 | 14.82 | 4.22 |

### C. Precisión al excluir el sector norte

| grupo | n | media | mediana | p95 | %>10° | %>30° | % de las horas |
|---|---|---|---|---|---|---|---|
| real fuera de ±20° del norte (20–340°) · V0 | 43335 | 15.82 | 1.65 | 82.95 | 31.44 | 18.11 | 86.76 |
| real fuera de ±20° del norte (20–340°) · V1 | 43335 | 8.05 | 1.21 | 39.34 | 21.56 | 7.38 | 86.76 |
| real fuera de ±20° del norte (20–340°) · R45 | 43335 | 8.12 | 1.44 | 37.27 | 21.49 | 6.81 | 86.76 |
| real fuera de ±30° · V0 | 39957 | 12.57 | 1.20 | 68.21 | 27.11 | 14.40 | 79.99 |
| real fuera de ±30° · V1 | 39957 | 6.49 | 0.92 | 32.01 | 17.83 | 5.48 | 79.99 |
| real fuera de ±30° · R45 | 39957 | 6.83 | 1.08 | 31.78 | 18.31 | 5.44 | 79.99 |
| real fuera de ±45° · V0 | 35328 | 9.66 | 0.80 | 53.71 | 22.64 | 10.90 | 70.73 |
| real fuera de ±45° · V1 | 35328 | 5.18 | 0.69 | 25.51 | 14.43 | 3.95 | 70.73 |
| real fuera de ±45° · R45 | 35328 | 5.89 | 0.82 | 28.44 | 16.15 | 4.58 | 70.73 |
| real dentro de ±20° · V0 | 6616 | 108.81 | 114.70 | 173.70 | 98.37 | 92.96 | 13.24 |
| real dentro de ±20° · V1 | 6616 | 52.09 | 36.61 | 152.37 | 81.61 | 56.12 | 13.24 |
| real dentro de ±20° · R45 | 6616 | 51.45 | 33.88 | 154.94 | 85.88 | 54.82 | 13.24 |

| regla | horas aceptadas % | V1 media | V1 p95 | V1 %>10° | V1 %>30° | R45 media | R45 %>10° | aceptadas con real ≤ 20° del norte % | aceptadas con real ≤ 45° del norte % | % de los errores V1 > 30° que quedan dentro |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 WindDir_Avg horario en 20–340° | 99.93 | 13.89 | 72.67 | 29.54 | 13.84 | 13.86 | 30.04 | 13.18 | 29.22 | 100.00 |
| R2 los 12 Avg de 5 min en 20–340° | 89.20 | 13.04 | 72.93 | 26.32 | 12.86 | 13.15 | 27.25 | 8.01 | 21.57 | 82.92 |
| R3 R2 y salto máx. entre registros ≤ 60° | 63.81 | 3.93 | 17.87 | 9.40 | 2.43 | 4.39 | 10.64 | 1.16 | 10.61 | 11.20 |
| R4 R2 y dispersión máx. a la mediana ≤ 45° | 54.03 | 2.58 | 10.87 | 5.48 | 1.35 | 2.58 | 5.48 | 0.80 | 10.09 | 5.25 |
| R5 R2 y dispersión ≤ 20° | 31.25 | 1.80 | 6.11 | 3.05 | 1.02 | 1.80 | 3.05 | 0.78 | 10.77 | 2.32 |


## quellaveco

Horas evaluadas: 51687.

### A. Dónde cae en WindDir_Avg el viento que D1 sitúa cerca del norte (registros de 5 min)

| registros de 5 min | n | % con Avg a ≤ 10° de D1 | % con 10–90° | % con > 90° | SD1 mediana |
|---|---|---|---|---|---|
| D1 a ≤ 20° del norte | 62170 | 28.28 | 40.66 | 31.06 | 10.63 |
| D1 a 20–45° del norte | 103286 | 82.69 | 15.89 | 1.42 | 9.46 |
| D1 a > 45° del norte | 447115 | 97.21 | 2.60 | 0.19 | 10.13 |

- Avg a ≤ 20° del norte: 15836
- D1 a ≤ 20° del norte: 62170
- de los Avg cerca del norte, D1 también: 99.1 %
- de los D1 cerca del norte, Avg también: 25.2 %

### B. Heurísticas por hora

| grupo | n | media | mediana | p95 | %>10° | %>30° |
|---|---|---|---|---|---|---|
| todas las horas · V0 WindDir_Avg horario | 51687 | 19.30 | 1.01 | 125.03 | 27.51 | 17.86 |
| todas las horas · V1 unitarios de Avg 5 min | 51687 | 7.96 | 0.64 | 39.11 | 19.30 | 6.93 |
| todas las horas · MED mediana circular de la hora | 51687 | 10.04 | 3.80 | 38.70 | 25.16 | 6.99 |
| todas las horas · R30 sin registros a > 30° de la mediana | 51687 | 10.24 | 3.15 | 40.55 | 28.18 | 7.86 |
| todas las horas · R45 sin registros a > 45° de la mediana | 51687 | 9.59 | 1.93 | 41.12 | 25.30 | 8.00 |
| todas las horas · R60 sin registros a > 60° de la mediana | 51687 | 9.01 | 1.02 | 41.01 | 23.17 | 7.84 |
| real a ≤ 45° del norte · V0 WindDir_Avg horario | 13715 | 56.41 | 33.05 | 164.90 | 66.88 | 51.38 |
| real a ≤ 45° del norte · V1 unitarios de Avg 5 min | 13715 | 21.80 | 10.16 | 91.98 | 50.36 | 21.36 |
| real a ≤ 45° del norte · MED mediana circular de la hora | 13715 | 21.45 | 10.14 | 95.12 | 50.30 | 19.64 |
| real a ≤ 45° del norte · R30 sin registros a > 30° de la mediana | 13715 | 21.66 | 10.38 | 97.18 | 50.88 | 20.06 |
| real a ≤ 45° del norte · R45 sin registros a > 45° de la mediana | 13715 | 21.90 | 10.77 | 95.59 | 51.77 | 20.82 |
| real a ≤ 45° del norte · R60 sin registros a > 60° de la mediana | 13715 | 21.98 | 10.71 | 95.59 | 51.75 | 21.39 |
| real a ≤ 20° del norte · V0 WindDir_Avg horario | 5359 | 101.62 | 108.52 | 173.58 | 95.35 | 87.09 |
| real a ≤ 20° del norte · V1 unitarios de Avg 5 min | 5359 | 37.18 | 21.77 | 136.21 | 71.06 | 40.04 |
| real a ≤ 20° del norte · MED mediana circular de la hora | 5359 | 37.78 | 22.36 | 137.57 | 78.71 | 38.27 |
| real a ≤ 20° del norte · R30 sin registros a > 30° de la mediana | 5359 | 38.67 | 23.82 | 138.50 | 81.79 | 39.52 |
| real a ≤ 20° del norte · R45 sin registros a > 45° de la mediana | 5359 | 38.58 | 24.68 | 138.87 | 79.40 | 41.48 |
| real a ≤ 20° del norte · R60 sin registros a > 60° de la mediana | 5359 | 38.17 | 23.99 | 138.37 | 76.51 | 41.56 |
| real a > 45° del norte · V0 WindDir_Avg horario | 37972 | 5.89 | 0.40 | 34.68 | 13.29 | 5.75 |
| real a > 45° del norte · V1 unitarios de Avg 5 min | 37972 | 2.96 | 0.20 | 14.88 | 8.08 | 1.72 |
| real a > 45° del norte · MED mediana circular de la hora | 37972 | 5.92 | 2.90 | 20.80 | 16.08 | 2.43 |
| real a > 45° del norte · R30 sin registros a > 30° de la mediana | 37972 | 6.12 | 2.11 | 25.30 | 19.98 | 3.45 |
| real a > 45° del norte · R45 sin registros a > 45° de la mediana | 37972 | 5.14 | 0.44 | 24.47 | 15.74 | 3.37 |
| real a > 45° del norte · R60 sin registros a > 60° de la mediana | 37972 | 4.32 | 0.25 | 21.92 | 12.85 | 2.94 |

### C. Precisión al excluir el sector norte

| grupo | n | media | mediana | p95 | %>10° | %>30° | % de las horas |
|---|---|---|---|---|---|---|---|
| real fuera de ±20° del norte (20–340°) · V0 | 46328 | 9.77 | 0.60 | 60.15 | 19.66 | 9.85 | 89.63 |
| real fuera de ±20° del norte (20–340°) · V1 | 46328 | 4.58 | 0.40 | 22.51 | 13.31 | 3.10 | 89.63 |
| real fuera de ±20° del norte (20–340°) · R45 | 46328 | 6.23 | 0.99 | 26.87 | 19.04 | 4.13 | 89.63 |
| real fuera de ±30° · V0 | 43061 | 7.74 | 0.50 | 46.94 | 16.31 | 7.71 | 83.31 |
| real fuera de ±30° · V1 | 43061 | 3.75 | 0.29 | 18.49 | 10.53 | 2.34 | 83.31 |
| real fuera de ±30° · R45 | 43061 | 5.61 | 0.65 | 25.40 | 16.93 | 3.67 | 83.31 |
| real fuera de ±45° · V0 | 37972 | 5.89 | 0.40 | 34.68 | 13.29 | 5.75 | 73.47 |
| real fuera de ±45° · V1 | 37972 | 2.96 | 0.20 | 14.88 | 8.08 | 1.72 | 73.47 |
| real fuera de ±45° · R45 | 37972 | 5.14 | 0.44 | 24.47 | 15.74 | 3.37 | 73.47 |
| real dentro de ±20° · V0 | 5359 | 101.62 | 108.52 | 173.58 | 95.35 | 87.09 | 10.37 |
| real dentro de ±20° · V1 | 5359 | 37.18 | 21.77 | 136.21 | 71.06 | 40.04 | 10.37 |
| real dentro de ±20° · R45 | 5359 | 38.58 | 24.68 | 138.87 | 79.40 | 41.48 | 10.37 |

| regla | horas aceptadas % | V1 media | V1 p95 | V1 %>10° | V1 %>30° | R45 media | R45 %>10° | aceptadas con real ≤ 20° del norte % | aceptadas con real ≤ 45° del norte % | % de los errores V1 > 30° que quedan dentro |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 WindDir_Avg horario en 20–340° | 99.73 | 7.97 | 39.20 | 19.34 | 6.95 | 9.61 | 25.36 | 10.15 | 26.34 | 100.00 |
| R2 los 12 Avg de 5 min en 20–340° | 87.42 | 6.59 | 32.63 | 15.08 | 5.48 | 8.28 | 21.30 | 4.47 | 17.94 | 69.18 |
| R3 R2 y salto máx. entre registros ≤ 60° | 66.69 | 1.49 | 7.60 | 3.28 | 0.29 | 2.86 | 8.40 | 0.29 | 11.58 | 2.76 |
| R4 R2 y dispersión máx. a la mediana ≤ 45° | 53.37 | 1.10 | 6.01 | 2.16 | 0.13 | 1.10 | 2.16 | 0.19 | 13.02 | 1.01 |
| R5 R2 y dispersión ≤ 20° | 25.93 | 0.50 | 2.95 | 0.28 | 0.01 | 0.50 | 0.28 | 0.05 | 16.86 | 0.06 |
