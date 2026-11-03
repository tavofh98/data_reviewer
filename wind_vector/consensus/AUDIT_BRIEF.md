Eres un revisor escéptico. Otro analista hizo las afirmaciones de abajo sobre el viento de una red de estaciones meteorológicas en una mina de alta montaña (sur de Perú, 3000–4400 m, relieve muy accidentado, un tajo abierto). Ya se equivocó una vez en esta misma línea: dijo que el consenso de vecinas «no servía» mirando solo el error medio, y resultó que había un desfase sistemático corregible. Parte de la sospecha de que puede volver a estar simplificando o equivocándose. Tu trabajo es intentar refutar cada afirmación con datos y, si encuentras una explicación mejor o un ángulo que él no consideró, proponerlo y probarlo. Sé creativo en los análisis; no te limites a releer su código. Responde en español.

## Datos
DuckDB (abrir SIEMPRE con read_only=True):
`C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db`
Tabla `meteorologia`, horaria (timestamp = fin del intervalo): estacion_id, WindDir_Avg (media aritmética de los ángulos de 5 s del logger), WindDir_D1_WVT (media vectorial unitaria del logger, solo en Altarani, Alto_Quellaveco, Camp_Quellaveco, Cortadera, Minas_Sur [desde 2026-04-22], Papujune, Tala-1, Tala_Legal, Huachunta, Vizcachas), WindDir_SD1_WVT, WS_ms_Avg. Dirección = de dónde viene, grados desde el norte.
Coordenadas UTM (zona 19S) en `C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc/met_viewer/stations.py` (léelas como texto: `"Nombre": Station(easting, northing, z_dem, ...)`).
Documentación de fallos conocidos: `.../explorar_qaqc/met_viewer/FINDINGS.md` (§8, §9) y `WIND_REVIEW.md`.
Tablas de 5 min (Table3) en `C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/references/` (formato TOA5 de Campbell: 4 líneas de cabecera, la 2ª con nombres de columna).
Scripts del análisis (para reproducir o encontrar fallos): en `explorar_qaqc/wind_vector/consensus/`: `consensus_calibrated.py`, `consensus_pairs.py`, `consensus_diagnosis.py`, `consensus_idw.py`. Se ejecutan desde `.../control_calidad/explorar_qaqc` con `uv run python <ruta> --limpio` (el entorno uv de explorar_qaqc tiene duckdb, pandas, numpy, sklearn). Usa PYTHONIOENCODING=utf-8.

Periodo de análisis: 2025-11-01 → 2026-11-03. Estaciones/tramos excluidos como vecinas por fallos documentados: Dique_pie_botadero, Chalsos, Mina_Norte, Planta_Concentradora (todo); Sarallenque hasta 2026-09-25 20:00; Alto_Quellaveco desde 2026-09-15 11:00; Cortadera desde 2026-09-13 11:00; Alto_Tala 2026-08-18 05:00 → 2026-09-23 15:00; Ilo, Huachunta, Vizcachas, Titire (lejanas); horas < 0.5 m/s.

## Afirmaciones a escrutar
1. Fuera del sector norte, `WindDir_Avg` y D1 de la misma estación casi coinciden (error 7–17°) porque salen de las mismas muestras; solo divergen al cruzar 0°/360°. Por eso ningún consenso de vecinas puede superar al dato propio fuera del norte.
2. El consenso IDW crudo (vectores u,v ponderados por velocidad y 1/d²) falla 25–58° porque a 1–8 km dominan flujos locales (drenaje, laderas, tajo), no porque el método esté mal.
3. Calibrar un desfase por (sector de 22.5° × franja día/noche/transición) mejora mucho; calibrar cada vecina por separado y combinarlas por su acierto mejora el sector norte en 6 de 8 estaciones (p. ej. Papujune 34°→22°, Tala-1 33°→22°).
4. La mejor vecina no es la más cercana (Cortadera se predice mejor desde Alto_Tala, Tala-1 y Papujune que desde Calientes1 o Apacheta).
5. Excluir las estaciones defectuosas cambió poco porque con 1/d² mandan las 2–3 más cercanas y la calibración absorbe los desfases constantes.
6. Altarani: de noche el 96 % de las horas viene de 90–180° por su propia ladera (no un fallo); cuando la red gira al oeste de noche (~104 h), Altarani se reparte entre SE (43 %) y NO (51 %) y ningún desfase único puede predecirlo.
7. Cortadera: de noche su viento se abre en abanico de 0° a 135°; las vecinas solo indican «noche de drenaje», no dónde dentro del abanico, y la calibración apunta al centro (~100°): de ahí 50–60° de error con viento del norte.
8. Camp_Quellaveco: su error nocturno es del sensor (reubicación de 2022 a un sitio resguardado, 54 % de calmas nocturnas, anemómetro que no arranca tras la calibración del 2026-09-10).
9. Cortadera (desde 2026-09-13) y Alto_Quellaveco (desde 2026-09-15) giraron el sensor (de día ~280°→~200° y ~326°→~220°).
10. Conclusión: el consenso sirve como información de régimen para un clasificador que detecte las «mezclas del norte» en los promedios de 5 min, no como sustituto de la dirección.

## Ideas que puedes probar (no obligatorias; añade las tuyas)
- ¿Hay otra forma de usar las vecinas que rinda claramente más (vecinas elegidas por similitud y no por distancia, regresión circular, condicionar a régimen sinóptico o a la velocidad, a la estación del año, a un desfase temporal entre estaciones)?
- ¿Los «giros» de la afirmación 9 podrían ser otra cosa (cambio estacional, fallo de la vecina de referencia)?
- ¿Es cierto que Altarani/Cortadera son el sitio y no el sensor? Busca evidencia en contra (SD1, velocidad, saltos, comparaciones con su propio pasado).

## Restricciones
- No modifiques ningún archivo existente ni la base de datos.
- Escribe solo en `explorar_qaqc/wind_vector/consensus/audit/`, y guarda ahí cada script que uses.

## Devuelve
`explorar_qaqc/wind_vector/consensus/audit/INFORME.md`: para cada afirmación 1–10, veredicto (SE SOSTIENE / PARCIAL / REFUTADA), la evidencia numérica y el script que la produce. Después, tus propuestas alternativas probadas con sus cifras. Breve y con números; nada de relleno.
