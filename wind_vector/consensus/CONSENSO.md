# Consenso espacial de la dirección del viento

_Exploración del 2026-11-03. Datos horarios de `database_duck` desde 2025-11-01. Verdad: `WindDir_D1_WVT` de la
estación evaluada (8 estaciones con D1). Error = diferencia angular 0–180°; «norte» = D1 a ≤ 45° del norte;
horas con > 1 m/s en la evaluada. Evaluación en semanas impares, ajuste en semanas pares._

## Pregunta

¿Pueden las vecinas («campo de vientos» de la red) ayudar a reconstruir la dirección vectorial horaria donde solo
hay `WindDir_Avg`, sobre todo con viento del sector norte, donde el promedio aritmético falla?

## Hallazgos

1. **Interpolar sin más no sirve.** Media de vectores (u, v) de las vecinas ponderada por velocidad y 1/d²: error
   medio 25–58° en todas las horas, frente a 7–17° del `WindDir_Avg` propio (salvo Minas_Sur, 33°). Con toda la red,
   solo con las 8 con D1 o solo a ≤ 4 km, el resultado es parecido (`consensus_idw.py`).
2. **El consenso sigue el régimen con un desfase sistemático por estación.** En Cortadera cambia de régimen
   día/noche a la vez que la estación, desplazado 40–60°. Calibrando un desfase circular por (sector de 22.5° del
   consenso × franja día/noche/transición) baja a 13–34° en todas las horas y 30–54° con norte
   (`consensus_calibrated.py --limpio`).
3. **Por pares rinde más con viento del norte.** Cada vecina calibrada por separado y combinada con peso
   1/error² de entrenamiento (`consensus_pairs.py --limpio`):

   | Estación | `WindDir_Avg` propio | Por pares | Vecinas que más aciertan |
   |---|---|---|---|
   | Altarani | 7.8 / 66.7 | 15.8 / 50.5 | Tala-1, Charaque, Sarallenque |
   | Alto_Quellaveco | 16.0 / 39.3 | 36.9 / 33.5 | Minas_Sur, Papujune, Sarallenque_MQG |
   | Camp_Quellaveco | 10.0 / 95.4 | 14.9 / 41.1 | Tala-1, Chancado, Charaque |
   | Cortadera | 9.8 / 72.5 | 19.8 / 46.1 | Alto_Tala, Tala-1, Papujune |
   | Minas_Sur | 33.7 / 81.2 | 25.7 / 31.1 | Alto_Quellaveco, Papujune, Cortadera |
   | Papujune | 17.4 / 57.1 | 21.6 / 22.1 | Alto_Quellaveco, Minas_Sur, Sarallenque |
   | Tala-1 | 9.7 / 50.2 | 14.1 / 22.4 | Alto_Tala, Papujune, Charaque |
   | Tala_Legal | 7.1 / 71.1 | 13.6 / 28.6 | Tala-1, Charaque, Alto_Tala |

   Error medio en grados, todas las horas / norte. La vecina útil no es la más cercana.
4. **Fuera del norte, el dato propio no se mejora.** `WindDir_Avg` y D1 salen de las mismas muestras de 5 s; solo
   divergen al cruzar 0°/360°. El consenso aporta en el sector norte.
5. **Dónde falla el consenso** (`consensus_diagnosis.py --limpio`): poco de día (7–10°), mucho de noche y en
   transiciones, y con viento flojo (1–2 m/s: 34–39°; > 4 m/s: 6–12°). Sin meses anómalos.
   - Altarani: de noche el 96.1 % de las horas viene de 90–180° (su ladera). Cuando de noche Tala-1 marca
     230–290° (104 h), Altarani se reparte entre SE (43.3 %) y NO (51.0 %): ningún desfase único lo predice.
   - Cortadera: de noche se abre en abanico de 0° a 135°; las vecinas indican el régimen, no la posición en el
     abanico, y la calibración apunta al centro.
   - Camp_Quellaveco: horas del norte casi todas a 1–2 m/s en transiciones; sensor ya documentado (FINDINGS §8,
     criterio G).
6. **Relojes alineados**: la temperatura de todas las estaciones del núcleo coincide con desfase 0 h
   (`clock_alignment.py`).

## Vecinas excluidas (`--limpio`)

Dique_pie_botadero, Chalsos, Mina_Norte y Planta_Concentradora enteras; Sarallenque hasta 2026-09-25 20:00;
Ilo, Huachunta, Vizcachas y Titire por distancia; horas < 0.5 m/s en toda la red. Tramos nuevos, aún no
anotados en `met_viewer/FINDINGS.md`:

| Estación | Tramo | Evidencia |
|---|---|---|
| Cortadera | desde 2026-09-13 11:00 | de día ~280° → ~200° (semanal) mientras Calientes1 sigue en ~271° |
| Alto_Quellaveco | desde 2026-09-15 11:00 | de día ~326° → 186–245° mientras Minas_Sur sigue en ~298° |
| Planta_Concentradora | desde 2024-04-06 | de día +73° respecto a Papujune; coseno del ciclo diario con vecinas −0.15 a 0.44 (antes 0.77–0.95) |
| Alto_Tala | 2026-08-18 05:00 → 2026-09-23 15:00 | giro de ~+50° frente a Tala-1 (sin verificación propia) |
| Charaque | 2026-01-14 14:00 → 01-15 12:00 y 2026-01-28 14:00 → 01-29 07:00 | registro congelado (dirección y velocidad fijas) |
| Sarallenque_MQG-15-02 | 2026-02-16 14:00 → 02-17 09:00 | registro congelado |

Cortadera y Alto_Quellaveco empiezan con registros perdidos hacia el mediodía (firma de visita de campo):
pedir los partes de esas fechas.

## Pendiente

- El peso de cada vecina en `consensus_pairs.py` se calcula sobre las mismas horas con que se calibró
  (señalado en una auditoría externa): sobrepondera vecinas con pocas horas, como Sarallenque desde 2026-09-25.
  Calcularlo con semanas no usadas en la calibración.
- Auditoría externa escéptica en curso (`AUDIT_BRIEF.md`): relanzar si no terminó.
- Siguiente paso propuesto: usar el consenso como rasgo de régimen en el clasificador de mezclas del norte del
  protocolo de 5 min (`../protocol.py`) y comprobar si baja de 9.8° con norte. En las estaciones sin D1 habría que
  calibrar con sus horas limpias (regla R4).
- Nuevas tablas de 5 min en `references/` (2026-11-03): Altarani, Alto_Tala, Apacheta, Calacaja, Camp_Quellaveco,
  Charaque, PCHAP, Planta_Concentradora, Sarallenque. DME3_Cortadera solo llega a 2026-04-13.

## Reproducir

Desde `explorar_qaqc/`, con `PYTHONIOENCODING=utf-8`:

```
uv run python wind_vector/consensus/consensus_calibrated.py --limpio
uv run python wind_vector/consensus/consensus_pairs.py --limpio
uv run python wind_vector/consensus/consensus_diagnosis.py --limpio
uv run python -m wind_vector.spatial_consensus    # visor: output/consenso_espacial.html
```

`met_viewer/stations.py` no importa mientras falte `python_programas/anglo_reporte/matrices.py`; estos scripts
leen las coordenadas como texto.
