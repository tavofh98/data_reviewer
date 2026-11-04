# Contexto común para la revisión del consenso espacial

## Tu papel
Eres un revisor escéptico de un análisis ajeno sobre el viento de una red de estaciones de una mina de alta montaña
(sur de Perú, 3000–4400 m, relieve accidentado, un tajo abierto). Ese análisis ya se equivocó una vez en esta línea:
concluyó que el consenso de vecinas «no servía» mirando solo el error medio, y había un desfase sistemático
corregible. Parte de la sospecha de que puede estar simplificando otra vez. Intenta refutar sus afirmaciones con
datos; si encuentras una explicación mejor, pruébala. Explica tu razonamiento y tus cifras con libertad.

## Datos
- DuckDB, abrir SIEMPRE con `read_only=True`:
  `C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/database_duck/anglo_ambiental.db`
  Tabla `meteorologia`, horaria (timestamp = fin del intervalo). Columnas útiles: estacion_id, WindDir_Avg
  (media aritmética de los ángulos de 5 s), WindDir_D1_WVT (media vectorial del logger; existe en Altarani,
  Alto_Quellaveco, Camp_Quellaveco, Cortadera, Minas_Sur desde 2026-04-22, Papujune, Tala-1, Tala_Legal),
  WindDir_SD1_WVT, WS_ms_Avg. Dirección = de dónde viene, grados desde el norte.
- Coordenadas UTM 19S: `explorar_qaqc/met_viewer/stations.py`, como texto `"Nombre": Station(easting, northing, z_dem, ...)`.
- Fallos documentados: `explorar_qaqc/met_viewer/FINDINGS.md` §8–§9 y `explorar_qaqc/met_viewer/WIND_REVIEW.md`.
- Resumen del análisis a revisar: `explorar_qaqc/wind_vector/consensus/CONSENSO.md`.
- Scripts del análisis: `explorar_qaqc/wind_vector/consensus/consensus_*.py`.
- Scripts de una revisión anterior que se cortó por tiempo, sin conclusiones escritas:
  `explorar_qaqc/wind_vector/consensus/audit/0*.py`. Reutilízalos: no rehagas lo que ya hacen.

## Cómo ejecutar
Desde `C:/Users/gfigueroa/OneDrive - greengroup.com.pe/Documentos/ANGLO/python_programas/control_calidad/explorar_qaqc`:
`uv run python <script>` con la variable de entorno PYTHONIOENCODING=utf-8. El entorno tiene duckdb, pandas, numpy
y scikit-learn. Los `consensus_*.py` se ejecutan con `--limpio`.

## Periodo y exclusiones
2025-11-01 → 2026-11-03. Fuera como vecinas: Dique_pie_botadero, Chalsos, Mina_Norte y Planta_Concentradora enteras;
Sarallenque hasta 2026-09-25 20:00; Alto_Quellaveco desde 2026-09-15 11:00; Cortadera desde 2026-09-13 11:00;
Alto_Tala 2026-08-18 05:00 → 2026-09-23 15:00; Ilo, Huachunta, Vizcachas y Titire; horas < 0.5 m/s. Validación:
ajuste en semanas pares, evaluación en semanas impares. Error = diferencia angular 0–180° frente a D1;
«norte» = D1 a ≤ 45° del norte.

## Reglas
- Tienes un corte duro de 20 minutos. Escribe tu informe POR PARTES: añade cada conclusión al fichero en cuanto la
  tengas, no al final. Lo que no esté escrito al cortarse se pierde.
- No modifiques ningún fichero existente ni la base. Escribe solo en tu carpeta de salida y guarda ahí cada script.
- Limítate al alcance de tu encargo. No explores el resto del repositorio ni otras variables (temperatura, lluvia…).
- Consultas a la base: filtra por periodo y estaciones; no cargues la tabla entera más de una vez.
