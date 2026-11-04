Lee primero `explorar_qaqc/wind_vector/consensus/audit/CONTEXTO.md`: tu papel, los datos y las reglas.

# Encargo r1: el método del consenso
Carpeta de salida: `explorar_qaqc/wind_vector/consensus/audit/r1/`. Informe: `r1/INFORME.md`.
Punto de partida: `audit/02_claims_1_to_5.py` (ya implementa buena parte de esto) y `consensus_pairs.py`.

## Afirmaciones a escrutar
1. Fuera del sector norte, `WindDir_Avg` y D1 de la misma estación casi coinciden (error 7–17°) porque salen de las
   mismas muestras; por eso ningún consenso de vecinas puede superar al dato propio fuera del norte.
2. El consenso IDW crudo (vectores u, v ponderados por velocidad y 1/d²) falla 25–58° por los flujos locales
   (drenaje, laderas, tajo), no por un defecto del método.
3. Calibrar cada vecina por separado (desfase circular por sector de 22.5° × franja día/noche/transición) y
   combinarlas por su acierto mejora el sector norte en 6 de 8 estaciones (p. ej. Papujune 34° → 22°).
4. La mejor vecina no es la más cercana (Cortadera se predice mejor desde Alto_Tala, Tala-1 y Papujune).
5. Excluir las estaciones defectuosas cambió poco porque con 1/d² mandan las 2–3 más cercanas y la calibración
   absorbe los desfases constantes.

## Además, una corrección concreta
En `consensus_pairs.py` el peso de cada vecina (1/error²) se calcula sobre las mismas horas con que se calibró.
Rehaz el peso con validación interna (p. ej. calibrar en semanas pares de índice par y medir el peso en las pares
restantes) y di cuánto cambian las cifras de prueba por estación y qué vecinas ganan o pierden peso.

## Fuera de alcance
Las estaciones concretas (Altarani, Cortadera y Camp_Quellaveco como sitio o sensor), los giros de septiembre y las
tablas de 5 min: los revisan otros encargos.

## Informe
Para cada afirmación: veredicto (se sostiene, parcial o refutada), las cifras que lo sustentan, el script y tu
explicación. Después, la corrección de los pesos con su tabla. Si propones un método mejor, inclúyelo con cifras
comparables (mismas semanas de prueba).
