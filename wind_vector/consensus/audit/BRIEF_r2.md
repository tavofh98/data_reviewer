Lee primero `explorar_qaqc/wind_vector/consensus/audit/CONTEXTO.md`: tu papel, los datos y las reglas.

# Encargo r2: las estaciones con más error y los giros
Carpeta de salida: `explorar_qaqc/wind_vector/consensus/audit/r2/`. Informe: `r2/INFORME.md`.
Punto de partida: `audit/03_claims_6_to_9.py` (ya implementa buena parte de esto) y `consensus_diagnosis.py`.

## Afirmaciones a escrutar
6. Altarani: de noche el 96 % de las horas viene de 90–180° por su propia ladera, no por un fallo. Cuando de noche
   Tala-1 marca 230–290° (104 h), Altarani se reparte entre SE (43 %) y NO (51 %), y ningún desfase único lo
   predice. ¿Es el sitio o el sensor? Busca evidencia en contra: su propio pasado (2021–2025), SD1, velocidad,
   saltos, otras vecinas.
7. Cortadera: de noche su viento se abre en abanico de 0° a 135°; las vecinas indican «noche de drenaje» pero no la
   posición dentro del abanico, y la calibración apunta al centro (~100°): de ahí 50–60° de error con norte.
   ¿Hay alguna variable (velocidad, hora, SD1, otra vecina) que sí indique la posición en el abanico?
8. Camp_Quellaveco: su error nocturno es del sensor (reubicación de 2022 a un sitio resguardado, 54 % de calmas
   nocturnas, anemómetro que no arranca tras la calibración del 2026-09-10), no del método.
9. Cortadera (desde 2026-09-13) y Alto_Quellaveco (desde 2026-09-15) giraron el sensor: de día ~280° → ~200° y
   ~326° → ~220°. ¿Podría ser estacional o un fallo de la vecina de referencia? Compara con el mismo periodo de
   años anteriores y con varias vecinas; estima el ángulo del giro y si es igual de día y de noche.

## Fuera de alcance
El método general del consenso y la detección de mezclas a 5 min: los revisan otros encargos.

## Informe
Para cada afirmación: veredicto (se sostiene, parcial o refutada), las cifras que lo sustentan, el script y tu
explicación. Para el punto 9, deja el ángulo estimado y la fecha y hora de inicio que mejor encajan.
