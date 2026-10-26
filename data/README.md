# Paquete de datos de viento

Último año de las tablas de los dataloggers, solo columnas de viento, para trabajar sin los `.dat` originales.
Lo genera `uv run python -m wind_vector.data_pack` en el equipo que tiene `references/` y `datafiles/data_1h`.
Son datos del cliente: este repositorio debe seguir siendo privado.

## Ficheros

| Fichero | Contenido |
|---|---|
| `<fichero>_Table3_wind.csv.gz` | Tabla de 5 min deduplicada |
| `<fichero>_Table1_wind.csv.gz` | Tabla de 60 min deduplicada |
| `aligned_<estación>.csv.gz` | Una fila por hora con sus 12 registros de 5 min (solo estaciones con D1) |

- `TIMESTAMP` es el fin del intervalo (convención de Campbell). La hora HH:00 agrupa los 5 min de HH-1:05 a HH:00.
- Deduplicación: ante timestamps repetidos se conserva el último registro del fichero (ver `loader._deduplicate`).
- El año se cuenta hacia atrás desde el último registro de 5 min de cada estación (descarga del 2026-10-23).

## Estaciones

| Estación | Fichero | Sensor | Columnas |
|---|---|---|---|
| Cortadera | `AAQ_Est_Cortadera_CR1000X` | veleta | velocidad media y máxima, `WindDir_Avg`, D1, SD1, velocidad vectorial |
| Papujune | `AAQ_Est_Papujune_CR1000X` | veleta | ídem |
| Alto Quellaveco | `AAQ_Alto_Quellaveco_CR1000X` | veleta | ídem |
| Tala-1 | `AAQ_Est_Tala-1_CR310X` | veleta | ídem |
| Tala Legal | `AAQ_Tala_Legal` | veleta | ídem |
| Minas Sur | `AAQ_Minas_Sur` | veleta | ídem; solo desde 2026-04-22 |
| Cerro Salviani | `AAQ_Cerro_Salviani_CR310X` | ClimaVUE | velocidad media y máxima, `WindDir_Avg` |
| Calientes1 | `AAQ_Est_Calientes1_CR310x` | ClimaVUE | ídem |
| Sarallenque MQG-15-02 | `Sarallenque_MQG-15-02` | ClimaVUE | ídem |

Los scripts de `wind_vector/` leen de aquí cuando no encuentran `wind_vector/output/aligned_*.csv.gz` ni los `.dat`.
