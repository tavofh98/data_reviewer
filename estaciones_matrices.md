# Contexto Técnico del Sistema de Monitoreo Ambiental Continuo — Anglo Quellaveco

Este documento resume la estructura de estaciones, matrices ambientales, tecnologías instrumentales, flujos de telemetría y reglas analíticas del proyecto **Anglo American Quellaveco (AAQ)**. Sirve como contexto operativo y de datos para análisis estadísticos y agentes de procesamiento.

---

## 1. Visión General del Parque de Monitoreo

- **50 estaciones físicas canónicas** en contrato activo de monitoreo continuo.
- **6 matrices canónicas** ambientales oficiales.
- **84 puntos lógicos de monitoreo (combinaciones estación-matriz)**: varias estaciones son multi-matriz y comparten caseta, sistema fotovoltaico o datalogger.
- **Fuera de contrato y descarte**:
  - `OESTE 1` es una estación histórica fuera de contrato (descartar para estadísticas activas).
  - Puntos como `PLATAFORMA_T7`, `LIMA_CALIBRACION` o `ALMACEN_AAQ` son **nodos logísticos** (talleres, laboratorios externos de calibración o bodegas), nunca estaciones de monitoreo ambiental.

---

## 2. Las 6 Matrices Canónicas y sus Estaciones

### 2.1. Calidad de aire (17 estaciones)
Monitoreo continuo de material particulado ($PM_{10}$, $PM_{2.5}$, PTS) y gases (cuando aplica).
- **Tecnologías**:
  - *Referencia EPA / MCERTS*: Grimm EDM 180 / 164 (monitores ópticos con sistema de secado activo) y Teledyne T640 (espectrometría óptica/absorción de alta precisión).
  - *Indicativo / Low-cost*: Oizom Dustroid / Polludrone (menor precisión, 80-90% de confiabilidad, vulnerables a saturación en alta humedad).
- **Estaciones (17)**:
  `ALTARANI`, `ALTO TALA`, `APACHETA`, `CALACAJA`, `CALIENTES-1`, `CAMPAMENTO QUELLAVECO`, `CERRO SALVIANI`, `CHANCADO PRIMARIO`, `CHARAQUE`, `DPB-1`, `ILO`, `MINAS NORTE`, `MINAS SUR`, `PLANTA CONCENTRADORA`, `SARALLENQUE 1`, `TALA 1`, `TALA LEGAL`.

### 2.2. Meteorología (27 estaciones)
Monitoreo de parámetros climáticos: temperatura, humedad relativa, velocidad/dirección de viento, precipitación, radiación solar, radiación UV y presión barométrica. Incluye tinas de evaporación para balance hídrico y cumplimiento legal.
- **Tecnologías**: Sensores dedicados (pluviómetros Young/Met One, anemómetros sónicos Gill windSonic, termohigrómetros Rotronic/Vaisala) o estaciones compactas integradas Campbell ClimaVUE 50. Tinas de evaporación Clase A (Pan A) con sistema automático de recarga gobernado por electroválvula y boya.
- **Estaciones (27)**:
  `ALTARANI`, `ALTO QUELLAVECO`, `ALTO TALA`, `APACHETA`, `CALACAJA`, `CALIENTES-1`, `CAMPAMENTO QUELLAVECO`, `CERRO SALVIANI`, `CHALSOS`, `CHANCADO PRIMARIO`, `CHARAQUE`, `CORTADERA`, `DME3-CORTADERA`, `DPB-1`, `EHA-TIT-1`, `HUACHUNTA`, `ILO`, `MINAS NORTE`, `MINAS SUR`, `MQG-15-02`, `PAPUJUNE`, `PLANTA CONCENTRADORA`, `PMC-4`, `SARALLENQUE 1`, `TALA 1`, `TALA LEGAL`, `VIZCACHAS`.

### 2.3. Ruido y Vibraciones (5 estaciones)
Monitoreo continuo de niveles de presión sonora ($L_{eq}$, percentiles estadísticos) y velocidad de partícula por vibración.
- **Tecnologías**: Sonómetros continuos de intemperie SVANTEK SV200A y SV307; vibrómetros triaxiales SVANTEK.
- **Estaciones (5)**:
  `ALTARANI`, `CALIENTES-1`, `CERRO SALVIANI`, `TALA 1`, `TALA LEGAL`.

### 2.4. Agua subterránea (17 estaciones)
Monitoreo de nivel freático / piezométrico y fisicoquímica de fondo en pozos profundos.
- **Tecnologías**: Piezómetros sumergibles In-Situ Level TROLL 500 y Aqua TROLL 200/500 con cable venteado (para compensación de presión barométrica). Contraste obligatorio en cada visita con sonda acústica manual de nivel (*ground truth*).
- **Estaciones (17)**:
  `MQG-15-01`, `MQG-15-03`, `MQG-15-05`, `MQG-15-07`, `MQG-15-08`, `P-03`, `PCP-1`, `PMC-2`, `PMC-3`, `PMC-4`, `PMC-6`, `PMC-7`, `PMP-1`, `PMP-2`, `S-COR-08-01`, `S-COR-08-01B`, `SQ-080-02`.

### 2.5. Estaciones hidrométricas (8 estaciones)
Calidad de agua superficial y nivel/caudal en ríos y quebradas de la cuenca (río Asana, Titire, Vizcachas).
- **Tecnologías**: Sondas multiparámetro sumergibles In-Situ Aqua TROLL 500 (pH, conductividad eléctrica, turbidez y oxígeno disuelto RDO) instaladas dentro de buzones de protección; sensores de nivel por presión o radar.
- **Estaciones (8)**:
  `EHA-QLVIZ-8`, `EHA-QMIL-01`, `EHA-RAS-01`, `EHA-RAS-02`, `EHA-TIT-1`, `EHA-VIZ-0`, `FIL-TUN`, `SDREN-COR`.

### 2.6. Cámaras (10 estaciones)
Vigilancia visual continua de operaciones mineras, clima y estado de infraestructura mediante circuito cerrado CCTV.
- **Tecnologías**: Cámaras PTZ domo Hikvision conectadas a NVR locales en caseta.
- **Estaciones (10)**:
  `ALTARANI`, `CALIENTES-1`, `CERRO SALVIANI`, `CHARAQUE`, `EHA-QMIL-01`, `EHA-RAS-01`, `EHA-RAS-02`, `PLANTA CONCENTRADORA`, `TALA 1`, `TALA LEGAL`.

---

## 3. Co-ubicación y Estaciones Multi-Matriz

Al calcular estadísticas por estación vs. por matriz, considerar que varias estaciones físicas albergan múltiples matrices:

| Grado de Co-ubicación | Cantidad | Estaciones Canónicas |
|---|:---:|---|
| **4 matrices** (Aire, Met, Ruido, Cámaras) | 5 | `ALTARANI`, `CALIENTES-1`, `CERRO SALVIANI`, `TALA 1`, `TALA LEGAL` |
| **3 matrices** (Aire, Met, Cámaras) | 2 | `PLANTA CONCENTRADORA`, `CHARAQUE` |
| **2 matrices** (Aire + Met) | 10 | `ALTO TALA`, `APACHETA`, `CALACAJA`, `CAMPAMENTO QUELLAVECO`, `CHANCADO PRIMARIO`, `DPB-1`, `ILO`, `MINAS NORTE`, `MINAS SUR`, `SARALLENQUE 1` |
| **2 matrices** (Hidrometría + Cámaras) | 3 | `EHA-QMIL-01`, `EHA-RAS-01`, `EHA-RAS-02` |
| **2 matrices** (Hidrometría + Met) | 1 | `EHA-TIT-1` (Titire) |
| **2 matrices** (Agua subterránea + Met) | 1 | `PMC-4` |
| **1 matriz pura** | 28 | 16 pozos de agua subterránea (`MQG-*`, `PMC-*`, etc.), 4 hidrométricas puras (`EHA-QLVIZ-8`, `EHA-VIZ-0`, `FIL-TUN`, `SDREN-COR`), y 8 meteorológicas puras (`ALTO QUELLAVECO`, `PAPUJUNE`, `CORTADERA`, etc.) |

---

## 4. Arquitectura de Transmisión y Modos de Telemetría

Reglas indispensables para calcular porcentajes de disponibilidad y transmisión sin incurrir en falsos negativos:

1. **Dataloggers Centrales (Campbell Scientific CR1000X, CR310, CR800)**:
   - Recolectan Aire, Meteorología, estado de Cámaras e Hidrometría. Transmiten periódicamente a la base central vía módem celular (SIM M2M) o enlaces punto a punto por radiofrecuencia (radioenlaces WAN).
2. **Plataforma SVANNET (Ruido y Vibraciones)**:
   - **Canal independiente**: Los sonómetros y vibrómetros SVANTEK tienen módem celular propio y suben directo a la nube SVANNET del fabricante; no pasan por el datalogger central.
   - *Condición operativa*: `TALA LEGAL` cuenta con telemetría activa; `CALIENTES-1` no tiene cobertura celular por orografía histórica; `ALTARANI` opera fundamentalmente con descargas presenciales.
3. **Estaciones con Esquema 100% Presencial (Sin Telemetría)**:
   - Los 9 piezómetros `MQG-15-01`, `MQG-15-03`, `MQG-15-07`, `SQ-080-02`, `PMP-1`, `PMC-3`, `PMC-6`, `PCP-1` y `S-COR-08-01B` **no cuentan con datalogger ni módem**.
   - **Regla estadística**: La ausencia de datos en servidor en estas estaciones **no es un fallo de transmisión**, sino su arquitectura nominal de diseño (almacenamiento en memoria interna y descarga manual periódica por técnicos de campo).
4. **Fuente autoritativa de conexión: `references/TRANSMISION AAQ 2026_v1.xlsx`** (incorporada 11/09/2026):
   - Una fila por estación canónica con `MODELO/SN`, `TIPO DE COMUNICACIÓN` (RADIOENLACE / CHIP CLARO M2M / CHIP MOVISTAR / SATELITAL), `DIRECCIÓN IP`, `PUERTO`, `PAKBUS_ID` y `NOMBRE_LOGGERNET`. **Si otra fuente la contradice, manda el Excel** y la otra se corrige.
   - **`PAKBUS_ID` es la _dirección_ PakBus, no el puerto.** Solo tiene que ser única dentro de su `PakBusPort`, y cada estación tiene el suyo: una dirección repetida en estaciones distintas **no es una colisión** y no debe reportarse como tal.
   - **`NOMBRE_LOGGERNET` no tiene por qué coincidir con el nombre del `.dat`.** El archivo se llama `<estación LoggerNet>_<tabla>.dat`, pero el nombre configurado puede diferir del que está en disco; la discrepancia no es un error.
   - **`ALTO TALA` transmite por el servidor propio del usuario**, no por este LoggerNet: su fila lleva `-` en IP, puerto y PakBus, y no le corresponde ningún `.dat`.
   - **Configurada pero sin señal no es lo mismo que sin configurar**: `EHA-QLVIZ-8` y `EHA-VIZ-0` están declaradas en LoggerNet con IP y puertos, pero hoy sin señal. Sus `.dat` existen con datos congelados y su `PAKBUS_ID` vacío es coherente, no un hueco.
   - `references/rutas_archivos.txt` lista las rutas de los `.dat` que revisa el analista. Verificado el 11/09/2026: las 38 estaciones conectadas tienen archivo; no falta ninguna ruta.

---

## 5. Sectores Geográficos y Logística Operativa

El sector explica la periodicidad de las visitas y los lapsos sin novedades:

- **Sector MINA (44 estaciones)**: Ubicadas en el tajo, botaderos y concentradora. Base de operaciones: container `PLATAFORMA_T7`. Visitas continuas (cada 2 a 5 días).
- **Sector PUERTO (1 estación - `ILO`)**: Costa sur (instalaciones portuarias). El viaje toma un día entero; visitas de frecuencia mensual o bajo demanda correctiva.
- **Sector ALTA MONTAÑA (5 estaciones: `HUACHUNTA`, `VIZCACHAS`, `EHA-TIT-1`, `EHA-VIZ-0`, `EHA-QLVIZ-8`)**:
  - Zona de puna sobre los 4,200 msnm.
  - La cuadrilla pernocta en campamento propio durante campañas acumuladas de 2 a 3 días consecutivos.
  - Clima extremo: tormentas de nieve cubren los paneles solares y provocan caídas de voltaje de baterías sin que exista daño físico en los equipos.

---

## 6. Diccionario de Alias y Nombres Coloquiales

Para resolver correspondencias al procesar partes crudos o tablas de datalogger:

| Nombre Coloquial / Alias de Campo | Nombre Canónico Oficial | Matriz Principal |
|---|---|---|
| **Asana Arriba** / `P-11` / `EHA-RAS-01 (P-11)` | `EHA-RAS-01` | Estaciones hidrométricas |
| **Asana Abajo** / `P-12` / `EHA-RAS-02 (P-12)` | `EHA-RAS-02` | Estaciones hidrométricas |
| **Vizcachas Arriba** / `VIZ-8` | `EHA-QLVIZ-8` | Estaciones hidrométricas |
| **Vizcachas Abajo** / `VIZ-0` | `EHA-VIZ-0` | Estaciones hidrométricas |
| **Titire** / `EHA-TIT-01` | `EHA-TIT-1` | Estaciones hidrométricas / Met |
| **Dique Pie Botadero** / `Pie Dique Botadero` | `DPB-1` | Calidad de aire / Met |
| `Saralenque` / `Sarallenque` | `SARALLENQUE 1` | Calidad de aire / Met |
| `Tala1` / `TALA-1` | `TALA 1` | Calidad de aire / Met / Ruido / Cámaras |
| `SQ-08-02` / `SQ-080-0` | `SQ-080-02` | Agua subterránea |
| `SCOR-08-01` | `S-COR-08-01` | Agua subterránea |
| `SCOR-08-01B` / `S-COR-08-01 B` | `S-COR-08-01B` | Agua subterránea |
| `PCM-2` / `PCM-4` | `PMC-2` / `PMC-4` | Agua subterránea |

---

## 7. Criterios de Calidad y Comportamiento de Sensores

Aspectos que explican anomalías en series de tiempo y banderas (flags) de control de calidad:

1. **Agua subterránea (Piezómetros)**:
   - Umbral de discrepancia máxima permitida entre sonda manual acústica y datalogger: **$0.05\text{ m}$ ($5\text{ cm}$)**. Diferencias superiores exigen ajuste u offset de programa.
   - Cables de piezómetro cortados en superficie por contratistas de obra impiden la comunicación y ajuste (ej. `PMC-3`), dejando la discrepancia documentada en partes.
2. **Estaciones hidrométricas (Deriva de Turbidez)**:
   - Un ascenso gradual y constante de turbidez suele deberse a la **colmatación de sedimentos en el buzón de protección del multiparámetro**, y no a un cambio en las condiciones del río. Requiere purga y limpieza del buzón.
3. **Meteorología (Tinas de Evaporación Clase A)**:
   - Rango normado de lámina de agua: **$178\text{ mm}$ a $203\text{ mm}$**. Si supera los $210\text{ mm}$, el datalogger registra `NaN` (guarda de cumplimiento).
   - Aumentos simultáneos por encima de $203\text{ mm}$ en varias estaciones corresponden a precipitación regional (lluvia copiosa), no a fallas mecánicas aisladas en las electroválvulas.
4. **Calidad de aire (Interferencia Óptica por Humedad)**:
   - Humedad relativa muy elevada ($\ge 90-95\%$) genera condensación y microgotas de agua que dispersan el haz de luz en los sensores ópticos de partículas, produciendo picos artificiales transitorios de $PM_{10}$ y $PM_{2.5}$ que deben marcarse como `CONDICION_MEDICION` u `OUTLIER`.
