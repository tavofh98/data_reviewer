# Revisión de datos de viento — metodología y criterios

_Redactado: 2026-09-23 · Validado con el caso Sarallenque (FINDINGS.md §9) y una revisión de toda la
red, 2023-07 → 2026-09._

Sirve para encontrar estaciones cuyo viento no es comparable con el de sus vecinas y para
distinguir la causa: un giro del sensor, un cambio de exposición, una reubicación o un fallo del
sensor. Los criterios se aplican en orden: los primeros criban toda la red y los últimos se
reservan para el caso sospechoso.

---

## 1. Convenciones

- **Dirección de procedencia**, en grados desde el norte y en sentido horario: 0° = N, 90° = E,
  180° = S, 270° = O. 258° significa que el viento **viene** del OSO. Los pétalos de una rosa
  apuntan hacia el origen del viento.
- **Media vectorial**, nunca aritmética: se promedian las componentes u = v·sen θ y w = v·cos θ y
  se reconstruye el ángulo. La media aritmética de 350° y 10° da 180°, y la vectorial da 0°.
- **Calma**: velocidad < 0.5 m/s (`qc.CALM_WS`). La dirección de una calma no significa nada: pesa
  cero en la media vectorial y no entra en las rosas.
- **Franjas**: día 10–17 h y noche 22–06 h, en la hora de la base. Las horas de transición se
  descartan porque su régimen cambia con la estación (el amanecer se adelanta ~1 h de junio a
  diciembre).
- **Constancia direccional**: R = |vector medio| / velocidad media, entre 0 y 1. Vale 1 cuando la
  dirección no se mueve.
- **Datos**: horarios, con el QC de `qc.py`. Los tramos ya conocidos como malos se excluyen antes
  de comparar (p. ej., la veleta pegada de Huachunta del 2026-02-26 al 2026-05-24).

---

## 2. Qué sabemos de la física

**Brisas de ladera.** De día el aire se calienta y sube la pendiente, así que el viento viene del
lado bajo. De noche se enfría y baja, así que viene del lado alto. Donde manda la ladera local, la
dirección de noche coincide con hacia dónde sube el terreno, y la de día es la opuesta.

Comprobado en la red (último año):

| Estación | Terreno sube hacia | Esperado día / noche | Observado día / noche |
|---|---|---|---|
| Altarani (fondo de valle abierto al NO) | 140° | 320° / 140° | 303° / 143° |
| Alto_Quellaveco (se sube desde el NO) | 109° | 289° / 109° | 284° / 109° |
| Sarallenque, antes de 2025-07 | 48° | 228° / 48° | ~245° / ~78° |

**Cuándo no aplica.**
- **Manda el valle, no la ladera:** Tala-1, Minas_Sur, Cortadera. Siguen el flujo de sus vecinas,
  no su ladera de 90–360 m.
- **Terreno casi llano** (pendiente ≤ 4°): Vizcachas, Titire, Huachunta. Manda el flujo regional.
- **Terreno modificado después del año 2000:** el DEM (SRTM) no ve el tajo ni los botaderos
  (Camp_Quellaveco, Chancado, Sarallenque, Mina_Norte).

**Altura del sensor.** Cambia la velocidad y el ciclo diario de la velocidad (a 10 m sopla más de
día que a 2 m), no la dirección. Cambiar la altura no gira una rosa.

---

## 3. Criterios de cribado (toda la red)

Cada estación se compara con sus **4 vecinas más cercanas a menos de 20 km**. Restar lo que hacen
las vecinas en el mismo mes quita la estación del año y los cambios regionales.

### A. Régimen frente a la ladera

- **Cálculo:** con el DEM (SRTM 30 m) se toman anillos de 90, 180 y 360 m en 8 acimuts y se ajusta
  un plano: su gradiente da hacia dónde sube el terreno. Error = diferencia angular entre la
  dirección observada del último año y la esperada (día: la opuesta a la subida; noche: la subida).
- **Umbral:** error > 60°.
- **Detecta:** errores constantes de orientación, que los demás criterios no ven porque no
  cambian en el tiempo (Chalsos: 94° de día; Dique_pie_botadero: 111° de noche).
- **Limitaciones:** los casos de §2. **Solo sirve de apoyo:** un aviso de A sin aviso de B, C o D
  ni diferencia con las vecinas suele ser relieve, no sensor.

### B. Saltos de dirección frente a las vecinas

- **Cálculo:** por mes y franja, dirección vectorial de la estación. Anomalía = diferencia con su
  mediana circular del periodo. Residual = anomalía menos la mediana de las anomalías de sus
  vecinas en ese mes.
- **Umbral:** |residual| > 45° durante **3 o más meses seguidos**. Los avisos sueltos en la época
  húmeda (dic–mar) o que cambian de signo son variación del tiempo, sobre todo en el altiplano,
  donde las vecinas están a 6–16 km.
- **Detecta:** giros, reorientaciones y reubicaciones con fecha (Sarallenque desde 2025-10 de día;
  Alto_Quellaveco de 2024-05 a 2025-02).
- **Limitación:** no ve un error presente en todo el periodo, porque la mediana de referencia ya
  lo incluye. Eso lo cubre A.

### C. Saltos de velocidad frente a las vecinas

- **Cálculo:** por mes, razón = velocidad media de la estación / mediana de sus vecinas. Se compara
  **el mismo mes de años distintos**, porque la razón tiene ciclo estacional.
- **Umbral:** cambio > 30 % sostenido.
- **Detecta:** cambios de altura, de exposición o de sensor (Calientes1: de 2.0–2.4 en 2024 a
  1.4–1.7 desde la semana del 2025-04-28, sin cambio de dirección).
- **Limitación:** si una vecina cambia, su efecto aparece en todas las estaciones que la usan
  (Tala-1 y Planta_Concentradora bajan a la vez en nov-2023: sospechar primero de la vecina
  común).

### D. Dirección fija

- **Cálculo:** sobre datos **sin QC**, rachas de horas consecutivas con la misma dirección (±1°) y
  viento ≥ 1 m/s.
- **Umbral:** ≥ 12 h.
- **Detecta:** veletas mecánicas pegadas (Huachunta: 54 rachas entre 2026-02-26 y 2026-05-23;
  Chancado_primario: 168 h en mar-2024). La regla `STUCK` del QC exige el valor idéntico y se
  pierde una veleta que oscila décimas de grado.
- **Nota:** un sónico (WindSonic, ClimaVUE) no tiene partes móviles. Si repite la dirección,
  sospechar del registro o del logger, no del sensor.

---

## 4. Diagnóstico del caso sospechoso

### E. Envolvente semanal frente a una vecina de control

- **Cálculo:** por semana, percentiles 2 y 98 de la dirección horaria (el borde inferior y el
  superior de la serie) y direcciones vectoriales de día y de noche. Junto a la misma tabla, una
  vecina estable a pocos km.
- **Lectura:**
  - **Los cuatro indicadores se mueven el mismo ángulo y la vecina no:** el sensor giró. Sarallenque,
    6 de octubre de 2025: −49°, −45°, −54° y −70°, un giro de ~−50°.
  - **Un borde fijo durante semanas:** hay un obstáculo. Cuando un obstáculo corta un sector, el
    viento lo rodea y las lecturas se amontonan en su borde. Sarallenque: borde inferior en 111°
    durante 13 semanas. Ningún régimen natural produce un borde tan fijo.
  - **Todo salta de semana en semana:** montaje provisional o sensor suelto. Esos tramos no se usan.

### F. Periodos limpios antes y después

Se eligen a ojo, sobre la serie, dos tramos estables y de al menos un mes, uno antes y otro después
del cambio (en Sarallenque: 2025-05-01 → 2025-06-30 y 2025-11-17 → 2026-01-09).

1. **Giro por correlación circular.** Histograma de dirección en bins de 10°, por franja. Se gira
   el histograma de después de 10° en 10° y se busca el giro que más se parece al de antes
   (similitud coseno). Se da la similitud con y sin el giro.
2. **Control estacional.** Lo mismo con las vecinas: su giro entre los dos periodos es lo que
   aporta la estación del año. En Sarallenque, las vecinas giran de noche entre 0° y −20°.
3. **Hora a hora.** Diferencia entre las direcciones vectoriales de después y de antes, por
   bloques de 2 h. **Un giro del sensor da la misma diferencia en todas las horas.** Si el día y
   la noche difieren, además del giro cambió la exposición.
4. **Usar la noche como referencia.** El drenaje nocturno viene del lado alto de la ladera, que
   rara vez está tapado, así que da la estimación más limpia del giro.
5. **Ocupación por sectores de 30°**, con los datos de después ya corregidos. Un sector que pasa a
   0 % y un sector vecino que acumula lo que falta es un obstáculo.
6. **Velocidad por hora relativa a la vecina de control**, antes y después, para separar el efecto
   del obstáculo del de la estación.

---

## 5. Cómo interpretar la combinación

| Lo que se ve | Causa | Qué hacer |
|---|---|---|
| Todos los indicadores de E se mueven el mismo ángulo; F da la misma diferencia día y noche; la velocidad no cambia | **Giro del sensor** (marca de norte mal alineada, mástil o shelter girado) | Corregible sumando un ángulo por tramo, una vez medido en campo |
| La noche da un giro limpio; el día difiere; un sector vacío y otro amontonado; la velocidad cambia | **Giro + cambio de exposición** (traslado a un punto con obstáculos) | Corregir el giro; el sector y la franja afectados no son comparables |
| Cambian dirección y velocidad, cambia la presión reducida (`BARO_DEV`) o la coordenada | **Reubicación** | Nueva coordenada y, si hace falta, nueva `z_baro`, desde la fecha del traslado |
| Solo cambia la velocidad (C), la dirección no | **Altura, exposición o sensor** | Comparar solo la forma del ciclo, no el nivel, hasta confirmarlo en campo |
| Dirección fija (D) con viento | **Veleta mecánica pegada** | Excluir el tramo |
| Error constante frente a la ladera y a las vecinas (A), sin fecha | **Orientación mal desde la instalación** | Confirmar con brújula; corregir si es un ángulo fijo |

**Lo que los datos no pueden cerrar solos.** Si además del giro cambió la exposición, el ángulo
exacto queda con ±10–30° de incertidumbre. Lo cierra una lectura con brújula de la marca de norte
del sensor, corregida por la declinación magnética. Las fotos de campo ayudan si se hacen
orientadas: una mirando al norte y otra al sur, con fecha y GPS.

---

## 6. Caso de validación: Sarallenque

| Paso | Resultado |
|---|---|
| B | desde 2025-10 el día se aparta de −80° a −125° de sus vecinas cada mes, y la noche entre 93° y 179° (en valor absoluto); las vecinas, estables |
| C | velocidad media de día de 2.0 a 2.4 m/s; +30 % relativa a Sarallenque_MQG en periodos limpios |
| E | tres tramos estables tras el traslado, unidos por giros puros (6 oct: ~−50°; ~17 nov: ~+30°); borde inferior fijo en 111° desde el 17 nov |
| F noche | giro de **180° (±10°)**: similitud 0.98 con el giro y 0.01 sin él; hora a hora de 172° a 184° |
| F día | tras restar 180°, el día viene de ~299° contra ~247° antes (las vecinas: ±20°); el sector S–SO–O (165–285°) pasa del 39 % de las horas a 0 %, y el de 300° del 0.4 % al 52 % |
| Conclusión | giro de 180° del shelter con el sensor + un obstáculo al S–SO–O en el nuevo punto |

Detalle e hipótesis: FINDINGS.md §9. Reporte con mapa y rosas:
`sarallenque_wind/reporte_viento_sarallenque.html`.

---

## 7. Herramientas

- `sarallenque_wind/build_report.py`: rosas de día y de noche antes y después, en un mapa con el
  relieve; series semanales; tabla de relieve con el DEM. Reutilizable para otra estación
  cambiando `TARGET`, `REFERENCES`, `CHANGE` y `PERIODS`.
- Los criterios A–D y E–F se calcularon con scripts de exploración que no están en el proyecto.
  Este documento da lo necesario para reproducirlos.
