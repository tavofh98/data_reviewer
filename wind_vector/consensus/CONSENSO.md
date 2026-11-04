# Consenso espacial de la dirección del viento

_Exploración del 2026-11-03. Datos horarios de `database_duck` desde 2025-11-01. Verdad: `WindDir_D1_WVT` de la
estación evaluada (8 estaciones con D1). Error = diferencia angular 0–180°; «norte» = D1 a ≤ 45° del norte;
horas con > 1 m/s en la evaluada. Evaluación en semanas impares, ajuste en semanas pares._

## Pregunta

¿Pueden las vecinas («campo de vientos» de la red) ayudar a reconstruir la dirección vectorial horaria donde solo
hay `WindDir_Avg`, sobre todo con viento del sector norte, donde el promedio aritmético falla?

## Conclusión (revisión escéptica del 2026-11-04, `audit/r1`–`r3`)

**No. La línea del consenso se cierra; el rescate de la dirección se hace con el clasificador de mezclas de 5 min
(`../protocol.py`, `../north_mixture.py`), sin vecinas.**

1. **El consenso calibrado solo funciona donde ya hay D1** (`audit/r1`, afirmación 3). Calibrar las vecinas contra
   el `WindDir_Avg` de la propia estación, que es lo único que hay en una estación sin D1, dispara el error con norte
   (todas / norte): Cortadera 25.0 / 102.8, Papujune 33.5 / 77.1, Tala-1 19.1 / 59.8, peor que el `WindDir_Avg`
   sin corregir. La tabla aprende el propio error o, si se filtran las horas dudosas, se queda sin horas del norte.
   Verificado.
2. **El consenso no aporta al clasificador de 5 min** (`audit/r3`). Un solo rasgo propio, el salto entre registros
   consecutivos, separa las mezclas mejor (AUC 0.964) que cualquier versión del consenso (0.91–0.93). Añadido al
   clasificador completo, el AUC sube menos de 0.001. Entrenando en dos estaciones y evaluando en la tercera, el
   error con norte empeora de 8.8° a 9.3–9.4°.
3. **El ejemplo que motivaba el consenso era falso.** De noche en Cortadera sí sopla del O–SO: con `WindDir_Avg`
   en 210–270° solo el 16 % de las horas es mezcla del norte (168 h, verificado en la tabla horaria; 14 % a 5 min
   según `audit/r3`). Lo que separa mezcla de viento real es la propia serie: con saltos > 45° entre registros de
   5 min hay mezcla; estable (≤ 25°), el 98.8 % es viento real.
4. **Correcciones a los hallazgos de abajo** (`audit/r1`):
   - Fuera del norte `WindDir_Avg` falla 3.7–5.7° (Minas_Sur 12.1°), no 7–17° (esa cifra era de todas las horas).
     Verificado.
   - Excluir vecinas sí importa: Dique_pie_botadero, a 0.55 km de Tala-1, se lleva el 59 % del peso 1/d²; excluir
     Planta_Concentradora, cuyo desfase es constante en el periodo, empeoró Papujune de 19.4 / 19.8 a 26.4 / 34.1.
   - Meter vecinas sin D1 contamina el consenso con norte: solo con vecinas con D1, Cortadera baja de 89° a 39°.
   - Pesos con validación interna: Sarallenque pierde peso; las cifras cambian ≤ 0.3°.
5. **Alternativa no adoptada** (`audit/r3` §5, sin verificar): el vector medio de toda la red sin calibrar baja el
   error con norte de 10.4° a 9.3° en validación entre estaciones. Ganancia de segundo orden que ata cada estación al
   estado del resto de la red.

## Hallazgos (2026-11-03, antes de la revisión)

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
pedir los partes de esas fechas. La revisión (`audit/r2`) los mide como giros rígidos, iguales de día y de noche:
Cortadera −73° ± 4° desde 2026-09-13 13:00 y Alto_Quellaveco −88° ± 5° desde 2026-09-15 12:00 (verificado:
−74° / −71° frente a Calientes1 y −85° / −94° frente a Minas_Sur, día / noche). Se restituyen sumando +73° y
+88°. Los fallos nuevos de sensor y de sitio están en `met_viewer/FINDINGS.md` §8.

## Pendiente

- Decidir si los giros de septiembre se corrigen (+73°, +88°) o se excluyen en `met_viewer/stations.py`
  (`WIND_EXCLUDED`), y pedir los partes de campo de esas visitas.
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
