Lee primero `explorar_qaqc/wind_vector/consensus/audit/CONTEXTO.md`: tu papel, los datos y las reglas.

# Encargo r3: ¿sirve el consenso para detectar las mezclas del norte?
Carpeta de salida: `explorar_qaqc/wind_vector/consensus/audit/r3/`. Informe: `r3/INFORME.md`.
Punto de partida: `audit/04_5min_and_alternatives.py`, `wind_vector/north_mixture.py` y `wind_vector/INFORME.md` §3.8
(el modelo de mezclas: cada `WindDir_Avg` de 5 min A es o la dirección real (H0) o una mezcla de muestras a ambos
lados del norte (H1)). Las estaciones del protocolo con D1 tienen error horario de 34.5° con norte usando solo A
(V1) y 9.8° con el clasificador de dos etapas.

## Afirmación a escrutar
10. El consenso de vecinas no sirve como sustituto de la dirección, pero sí como información de régimen para que
    el clasificador distinga una mezcla del norte de un viento real que da el mismo A. Ejemplo: de noche en
    Cortadera nunca sopla del oeste, así que un A de ~240° con régimen de drenaje tiene que ser una mezcla.

## Qué medir
Usa SOLO los ficheros ya alineados `explorar_qaqc/data/aligned_<estación>.csv.gz` (una fila por hora con sus 12
registros de 5 min y la verdad D1; formato descrito en `explorar_qaqc/data/README.md` y en `wind_vector/loader.py`).
No leas los .dat de `references/`: son de 100 MB o más.
1. En los registros de 5 min de Cortadera, Papujune y Tala-1 con A en 150–300° (zona ambigua), etiqueta H1 (D1 a
   ≤ 45° del norte) frente a H0 (D1 a ≥ 90° del norte). Calcula el consenso horario de las vecinas (lógica de
   `consensus_pairs.py`, con las exclusiones del contexto) y mide cuánto separa H1 de H0: AUC, y la razón de
   verosimilitud según el consenso esté cerca o lejos del norte.
2. Compara esa separación con la de los rasgos que ya usa el clasificador (`north_mixture.features`): ¿aporta el
   consenso información que los rasgos propios no tienen? Una forma: AUC de una regresión logística con y sin el
   rasgo de consenso, validada fuera de muestra por semanas.

## Fuera de alcance
Reentrenar el protocolo completo de `wind_vector/protocol.py` (tarda más que tu tiempo) y revisar estaciones
concretas.

## Informe
Veredicto sobre la afirmación 10 con las cifras de los puntos 1 y 2 por estación, los scripts, y tu lectura de si
vale la pena meter el consenso en el clasificador. Si ves una forma mejor de usar las vecinas, pruébala y compárala.
