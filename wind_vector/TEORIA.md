# Promedio de dirección de viento: fundamento teórico

Documento de referencia para decidir si el reporte ambiental debe usar la dirección media de vector
unitario (Θ1, `WindDir_D1_WVT`) en lugar de la media aritmética (`WindDir_Avg`), y si el Θ1 horario
puede derivarse de registros de 5 min.

Convención de estado de cada afirmación: **[V]** verificada en la fuente primaria durante esta
investigación; **[D]** deducción matemática propia (comprobada numéricamente cuando se indica);
**[S]** simulación sintética propia (no son datos de campo); **[NV]** no verificada.

---

## 0. Notación y alcance

- Muestra *i* de 5 s: velocidad $s_i$ (m/s), dirección $\theta_i$ (grados, medida desde el norte en
  sentido horario, "de dónde sopla").
- Vector unitario de la muestra: $\mathbf e_i = (\sin\theta_i,\ \cos\theta_i)$ = (este, norte).
- $N$ = muestras del intervalo (5 min: 60; 1 h: 720). $n$ = muestras con $s_i>0$ (las únicas que
  entran en el cálculo vectorial).
- Dirección de un vector (Ux, Uy): $\Theta=\operatorname{atan2}(U_x,U_y)$ llevada a [0, 360).

Nota sobre el sensor: la combinación "velocidad por pulsos + dirección por potenciómetro" corresponde a
un anemómetro de hélice con veleta (familia 05103). El Gill WindSonic es ultrasónico con salida digital,
no tiene pulsos ni potenciómetro; conviene confirmar cuál es el instalado, porque cambia el umbral de
arranque (calmas, sección 5). [NV: umbral del 05103 no consultado]

Fuentes primarias consultadas (detalle en la sección 8):

| Fuente | Estado |
|---|---|
| Campbell Scientific, CRBasic `WindVector` y "Wind Vector Calculations" (CR6, mismo texto que CR1000X) | [V] texto y ecuaciones leídos (las ecuaciones son imágenes; se leyeron una a una) |
| EPA-454/R-99-005, *Meteorological Monitoring Guidance for Regulatory Modeling Applications* (feb. 2000) | [V] PDF completo, texto extraído |
| EPA-454/B-08-002, *QA Handbook for Air Pollution Measurement Systems, Vol. IV* v2.0 (20/01/2008) | [V] PDF completo, texto extraído |
| WMO-No. 8, *Guide to Meteorological Instruments and Methods of Observation*, 7.ª ed. (2008) | [V] PDF completo. **Ediciones 2018/2021/2023: [NV]** (no se obtuvo su texto) |
| Yamartino (1984), J. Climate Appl. Meteor. 23(9):1362-1366 | [V] la fórmula y la cita (vía EPA, Campbell y Wikipedia); el artículo en sí [NV] |
| NOAA NDBC, "What averaging procedures are performed on the wind measurements?" | [V] |
| ASTM D5741, ISO, VDI 3786-2 | [NV] para la prescripción sobre dirección media (ver 3.4) |

---

## 1. Definiciones y fórmulas

### 1.1 Media aritmética de ángulos y por qué falla

$$\bar\theta_{\text{arit}}=\frac1N\sum_{i=1}^N\theta_i \qquad(\text{es lo que guarda } \texttt{WindDir\_Avg})$$

Es la media correcta en la recta real, pero la dirección vive en un círculo: $\theta$ y $\theta+360^\circ$
son la misma dirección y la media aritmética no lo respeta. Dos consecuencias:

1. **Cruce por el norte.** Para $\{350^\circ,\,10^\circ\}$ la media aritmética es $180^\circ$ y la dirección
   real es $0^\circ$ [D, ejemplo trivial]. El error puede llegar a $\pm180^\circ$.
2. **No es equivariante.** Si se cambia el origen del ángulo (medir desde el este, por ejemplo), la
   media aritmética no se desplaza lo mismo que los datos; una buena media circular sí.

Además, en el 05103 la zona muerta 355–360° se fija a 0°, de modo que lecturas físicas de 357° entran
como 0°; eso es coherente con "norte" y no rompe el vector, pero sí contamina cualquier media aritmética
de un intervalo que toque el norte [D].

**Aclaración terminológica crítica.** La "media escalar" de la guía EPA **no** es `WindDir_Avg`. La EPA
(EPA-454/R-99-005 §6.2.1, ecs. 6.2.4-6.2.5) recomienda el procedimiento de Mitsuta: *desenrolla* la
serie de muestras (suma o resta 360° cuando dos muestras consecutivas difieren más de 180°) y
promedia la serie desenrollada; exige muestreo ≥ 1/s para que ese salto sea detectable. El `Average` de
CRBasic aplicado a la dirección es la media aritmética simple sin desenrollar [dato aportado por el
usuario; la documentación de Campbell consultada no describe `Average`]. Cuando la EPA dice que "la
media escalar es aceptable" se refiere a Mitsuta, no a `WindDir_Avg`.

Con la serie a 5 s, Mitsuta ni siquiera es aplicable con garantías (la EPA pide ≥ 1 Hz) [V], y la EPA
advierte textualmente que el procedimiento "puede dar resultados erróneos si se usa para
post-procesar promedios sub-horarios para obtener un promedio horario, porque no hay garantía de que la
diferencia entre promedios sub-horarios sucesivos sea menor de 180°" [V, §6.2.1].

### 1.2 Dirección media de vector unitario, Θ1 [V: Campbell, ecs. 03-05]

$$U_x=\frac1N\sum\sin\theta_i,\qquad U_y=\frac1N\sum\cos\theta_i,\qquad \Theta_1=\arctan\!\left(\frac{U_x}{U_y}\right)\ (\text{con corrección de cuadrante})$$

Cada muestra tiene longitud 1 sea cual sea la velocidad. Es la dirección de la media circular
(Mardia y Jupp, *Directional Statistics*, 2000; [NV] consulta directa del libro). La EPA la
describe igual (§6.2.2, ecs. 6.2.17-6.2.19) y los dos manuales EPA coinciden en el texto: "in general,
the unit vector result will be comparable to the scalar average wind direction, and may be used to
model plume transport" [V].

Se define con $n$ muestras (aquellas con $s_i>0$, ver 5). La **longitud resultante media**

$$R=\sqrt{U_x^2+U_y^2}\in[0,1]$$

mide la concentración direccional: $R=1$ si todas las muestras apuntan igual; $R\to0$ si están repartidas
uniformemente (la dirección media queda mal definida).

### 1.3 Dirección resultante ponderada por velocidad, Θu [V: Campbell, ecs. 12, 13, 16]

$$U_e=\frac1N\sum s_i\sin\theta_i,\qquad U_n=\frac1N\sum s_i\cos\theta_i,\qquad \Theta_u=\arctan\!\left(\frac{U_e}{U_n}\right)$$

Es la dirección del vector viento medio verdadero (promedio de las componentes u, v). Las muestras
fuertes pesan más. Coincide con Θ1 solo si la velocidad no covaría con la dirección.

Ejemplo [D, comprobado]: mitad de las muestras desde 0° con 1 m/s y mitad desde 90° con 5 m/s. Θ1 = 45°
(una dirección que nunca ocurrió); Θu = 78,7°.

### 1.4 Velocidad escalar S frente a magnitud del vector medio U

$$S=\frac1N\sum s_i\quad[V],\qquad \bar U=\sqrt{U_e^2+U_n^2}\quad[V]$$

(Campbell indica que S **incluye** las muestras de velocidad cero; el cálculo vectorial las excluye.)
Siempre $\bar U\le S$ (desigualdad triangular): el vector medio pierde la parte de la velocidad que se
cancela por cambios de dirección. La WMO lo cuantifica: "the mean vector speed in the average wind
direction is less than the average of all instantaneous wind speeds by a small amount, generally a few
per cent" (WMO-No. 8, 7.ª ed., Parte I cap. 5 §5.8.1) [V].

**Relación U = S·R.** El enunciado exacto no es $\bar U=S\,R$ con $R$ de vectores unitarios. Lo
exacto es

$$\bar U=S\cdot R_s,\qquad R_s=\frac{\left|\sum s_i\,\mathbf e_i\right|}{\sum s_i}\quad(\text{longitud resultante ponderada por velocidad})$$

[D]. $R_s=R$ solo si la velocidad es independiente de la dirección (o constante). Bajo esa hipótesis
$\bar U\approx S\,R$, y para dispersión pequeña $R\approx1-\sigma^2/2$, que es la corrección de
Frenkiel (1951) que recoge la WMO: $\ \bar U/S\approx 1-\sigma_\theta^2/2$ (ec. 5.2 de WMO-No. 8, con
$\sigma_\theta$ en radianes) [V]. Ejemplos: σ = 20° → 0,94 (−6 %); σ = 30° → 0,86 (−14 %) [D].
NDBC usa Θ1 para dirección y promedio escalar para velocidad, y avisa de que esa combinación da
velocidades mayores que un vector verdadero [V].

---

## 2. Desviación estándar de Yamartino

### 2.1 Fórmula [V: Campbell, ecs. 09-10; EPA 6.2.9; QA Handbook 9-10]

$$s_a=\frac1n\sum\sin\theta_i,\quad c_a=\frac1n\sum\cos\theta_i,\quad \varepsilon=\sqrt{1-(s_a^2+c_a^2)},\quad \boxed{\sigma(\Theta_1)=\arcsin(\varepsilon)\,\bigl[1+(\tfrac{2}{\sqrt3}-1)\,\varepsilon^3\bigr]}$$

con $\tfrac2{\sqrt3}-1\approx0{,}1547$. Como $s_a=U_x$ y $c_a=U_y$ de 1.2, se cumple
$$\varepsilon=\sqrt{1-R^2}\qquad[D].$$

Propiedades [D, comprobadas numéricamente]:
- Para dispersión pequeña $\varepsilon\approx\sigma$ (radianes).
- En $\varepsilon=1$ ($R=0$) vale $\tfrac{\pi}{2}\cdot\tfrac{2}{\sqrt3}=\pi/\sqrt3=1{,}8138$ rad $=103{,}92^\circ$, la desviación
  típica de una distribución uniforme en el círculo. Por eso el QA Handbook (§9.6.2) menciona un tope
  de σθ de 103,9° [V]. El rango de la salida es [0°, 103,9°].
- Es un estimador de una pasada (se acumulan solo $\sum\sin$ y $\sum\cos$), por eso lo implementa el
  logger. Yamartino lo comparó con otros estimadores de una pasada y la EPA lo adopta tras la
  evaluación de Turner ("excellent results for most cases") [V]. Se cita que queda típicamente
  dentro de ~2 % de la desviación estándar verdadera y dentro del 15 % en el peor caso
  [fuente secundaria: Wikipedia/AMS; NV en el artículo original].

### 2.2 ¿Se puede invertir para recuperar R?

**Sí, y de forma exacta**, porque σ es una función estrictamente creciente y continua de ε en [0, 1]
(derivada de $\arcsin\varepsilon$ positiva, y el factor entre corchetes también crece) y $R=\sqrt{1-\varepsilon^2}$:

$$\varepsilon=g^{-1}(\sigma),\qquad R=\sqrt{1-\varepsilon^{2}},\qquad g(\varepsilon)=\arcsin\varepsilon\,[1+0{,}1547\,\varepsilon^3]$$

No hay inversa en forma cerrada; se resuelve con un método numérico monótono de una variable
(bisección/Newton) sobre ε en [0,1]. Comprobado numéricamente: ida y vuelta R → σ → R con error < $10^{-6}$ [D].
El efecto de cuantizar σ a 0,01° (resolución FP2) es $\delta R\approx|dR/d\sigma|\,\delta\sigma<10^{-3}$ [D, estimación].

Aproximaciones útiles (σ en radianes) y su validez [D, tabla calculada con la inversa exacta]:

| σ (°) | R exacta | $1-\sigma^2/2$ | $e^{-\sigma^2/2}$ |
|---:|---:|---:|---:|
| 5 | 0,9962 | 0,9962 | 0,9962 |
| 10 | 0,9848 | 0,9848 | 0,9849 |
| 20 | 0,9404 | 0,9391 | 0,9409 |
| 30 | 0,8707 | 0,8629 | 0,8719 |
| 40 | 0,7820 | 0,7563 | 0,7837 |
| 60 | 0,5699 | 0,4517 | 0,5779 |
| 80 | 0,3292 | 0,0252 | 0,3773 |
| 100 | 0,0582 | −0,5231 | 0,2180 |

- $R\approx1-\sigma^2/2$: válida hasta σ ≈ 25° (error < 0,004). Falla por encima de ~40°.
- $R\approx e^{-\sigma^2/2}$: es la inversa de $\sigma=\sqrt{-2\ln R}$ (EPA ec. 6.2.8, atribuida a Mardia [V];
  corresponde a la normal envuelta). Error < 0,01 hasta σ ≈ 60°; mala por encima de 80°.
- Con σ > 80° conviene usar la inversa exacta. En ese régimen R es pequeña y Θ1 casi no tiene sentido
  (ver 4.3), por lo que el error de R apenas influye en el resultado horario.

Condiciones para que la inversión sea válida con los datos del logger [D salvo indicación]:
1. `Subinterval = 0` (el caso: `WindVector(1, WS_ms, WindDir, FP2, False, 0, 0, 0)`). Con subintervalo
   distinto de 0 la σ es un promedio de σ de subintervalos y ya no es función de R global [V: la
   documentación indica que promedia σ de subintervalos].
2. σ debe ser la de Yamartino: con OutOpt 0 lo es; con OutOpt 2 y 4 es el algoritmo de Campbell ponderado por
   velocidad y no sirve para esta inversión [V].
3. Resolución de almacenamiento FP2 [V]: σ con 0,01° entre 8 y 80°, 0,1° por encima; Θ1 con 0,1° entre
   80 y 800. Insignificante para R.
4. Hay que saber contra qué $N$ se dividen $U_x, U_y$ (solo las $n$ muestras con velocidad > 0, o las
   $N$ totales). La documentación publica las ecuaciones solo con "N". [NV]; se puede verificar con datos
   (en bloques con calmas parciales, ver 4.2).

---

## 3. Qué recomiendan los organismos

### 3.1 WMO-No. 8, 7.ª edición (2008) [V]; ediciones posteriores [NV]

- Parte III, cap. 3, §3.5 (Averaging): para "wind speed and direction", la cantidad que debe promediarse
  son las **componentes cartesianas**. El Anexo 1.B de la Parte I (tabla de requisitos) indica para la
  dirección: "Averages computed over Cartesian components".
- Parte I, cap. 5, §5.8.1: "From the fundamental point of view, component averaging is preferable over
  the independent averaging of speed and direction. However, the differences are very small and, for
  most applications, component averages can easily be derived from average speed and direction. This
  also applies to the corresponding standard deviations." Es decir: reconoce expresamente que se puede
  aproximar con velocidad y dirección promedio.
- Parte II, cap. 2 (aeródromos): "Vector averaging is to be preferred to scalar averaging."
- Reporte sinóptico: dirección a la decena de grado más cercana, promedio de 10 min; "Calm" si la
  velocidad media es < 1 kn y la dirección se codifica 00 (§5.1.3).
- σ de dirección: muestreo de ~1 s o 0,25 Hz "suitable in most cases" (§5.8.2).
- Los textos de 2018/2021/2023 **no** se obtuvieron; hay que contrastarlos antes de citar números de página
  de la edición vigente.

### 3.2 EPA-454/R-99-005 (feb. 2000) [V]

- §6.2.1: dirección media "escalar" por Mitsuta (media de la serie desenrollada); σθ por Yamartino
  (ec. 6.2.9). Advierte del error de Mitsuta si se re-promedia a partir de subhorarios.
- §6.2.2: el vector unitario "will be comparable to the scalar average wind direction, and may be used to
  model plume transport".
- §6.9 (Recommendations): modelos gaussianos de estado estacionario deben usar la **velocidad escalar** y la
  dirección media horaria; "unit vector processing (Section 6.2.2) may also be used to estimate the hourly
  scalar mean wind direction". Las estadísticas horarias pueden obtenerse procesando toda la hora **o promediando
  estadísticas subhorarias**; intervalo subhorario recomendado 15 min; se requieren 2 promedios válidos de
  15 min por hora.
- §4.5-4.6: para la media bastan ≥ 60 muestras; para σ, ≥ 360 muestras (precisión 5-10 %). Con escaneo a 5 s
  se cumple en la hora (720) pero no en 5 min (60) para σ.
- §6.2.1: la σθ horaria para estabilidad debe construirse con cuatro valores de 15 min
  ($\sigma_{1h}=[(\sigma_1^2+\sigma_2^2+\sigma_3^2+\sigma_4^2)/4]^{1/2}$, ec. 6.2.10) para reducir el
  efecto del meandro; es una definición distinta de la σ de Yamartino de la hora entera.
- §6.2.3 y 6.9: calma = velocidad menor que el umbral de arranque del anemómetro o la veleta (el mayor); para
  monitoreo en sitio con los umbrales de la Tabla 5-2, calma = < 0,5 m/s. Las calmas se marcan
  (flag); para modelos estacionarios se sube a 1 m/s toda velocidad < 1 m/s, conservando el dato original.

### 3.3 EPA-454/B-08-002, QA Handbook Vol. IV, v2.0 (2008) [V]

- §2.8.1: tras comparar con simulaciones el algoritmo escalar original (Mitsuta) y el vector unitario,
  concluye: "a unit-vector algorithm should be used for calculating scalar wind speed and wind direction".
  Motivo: con rotaciones completas del vane el escalar puede dar errores "up to 180 degrees from a
  correctly interpreted average wind direction".
- §9.6.1-9.6.2: define WDV/WSV (vectorial con velocidad), el vector unitario (ecs. 9-5 a 9-7) y la σθ de
  Yamartino (9-10); σθ "is collected for the sole purpose of estimating lower atmospheric stability";
  tope de 103,9°; combinación de cuatro valores de 15 min para la clase de estabilidad.
- §9.6: las estadísticas se calculan sobre muestras de 1 s y "se reportan como valor horario promedio de
  las 3 600 muestras".
- Orden temporal relevante: la guía de 2000 prefería Mitsuta y admitía el vector unitario como alternativa;
  el Handbook de 2008 invierte la preferencia a favor del vector unitario.

### 3.4 ISO, ASTM y otros

- NOAA NDBC: dirección por vector unitario y velocidad por promedio escalar [V].
- ASTM D5741 (*Characterizing Surface Wind Using a Wind Vane and Rotating Anemometer*): su alcance
  (velocidad, dirección, rachas, desviaciones) fue verificado; **no** se pudo verificar qué dirección media
  prescribe [NV].
- ISO y VDI 3786 parte 2: [NV] no se localizó texto aplicable.
- Campbell Scientific (documentación de WindVector): OutOpt 0 = "EPA-compliant option for straight-line
  Gaussian dispersion models"; la página desaconseja la magnitud del vector medio (OutOpt 2 y 4) para esos
  modelos, aunque puede convenir a modelos de trayectoria variable [V].

### 3.5 Qué estadístico para qué uso

| Uso | Estadístico recomendado | Apoyo |
|---|---|---|
| Rosa de vientos / frecuencias por sector | Θ1 por registro (horario o 10 min). Cualquier media que respete el círculo; la aritmética solo es aceptable en sectores lejos del norte | WMO componentes; EPA 2008 [V] |
| Dispersión gaussiana / transporte de pluma | Θ1 (admitido por EPA 2000 y preferido por EPA 2008) con velocidad escalar S | EPA 2000 §6.9; EPA 2008 §2.8.1; Campbell [V] |
| Modelo de trayectoria variable (puff) | Vector verdadero (Θu, U) puede ser más adecuado | Campbell [V] (indicación, no norma) |
| Reporte de estación (sinóptico) | Promedio de componentes cartesianas a 10 min; dirección en decenas de grado; calma = 00 | WMO [V] |
| Estabilidad (σθ) | Yamartino, y hora por cuatro valores de 15 min | EPA 2000 y 2008 [V] |

---

## 4. Composición temporal: del bloque de 5 min a la hora

### 4.1 Resultado exacto

Para la hora, la suma de vectores unitarios es la suma de las sumas de los bloques *k* = 1…12. Con
$n_k$ = número de muestras de 5 s con $s_i>0$ en el bloque *k*, $\Theta_k$ su Θ1 y $R_k$ su longitud
resultante:

$$\sum_{i\in\text{hora}}\mathbf e_i=\sum_{k=1}^{12}n_k\,R_k\,(\sin\Theta_k,\ \cos\Theta_k)$$

$$\boxed{\Theta_{1,\text{hora}}=\operatorname{atan2}\!\Bigl(\sum_k n_kR_k\sin\Theta_k,\ \sum_k n_kR_k\cos\Theta_k\Bigr)},\qquad R_{\text{hora}}=\frac{\sqrt{(\sum n_kR_k\sin\Theta_k)^2+(\sum n_kR_k\cos\Theta_k)^2}}{\sum_k n_k}$$

[D]. Es una identidad algebraica, no una aproximación: los pesos correctos son $w_k=n_kR_k$
(equivalentemente, componentes $n_kU_{x,k}$ y $n_kU_{y,k}$). Con $R_{\text{hora}}$ se obtiene también la σ de
Yamartino de la hora entera, de forma exacta, por la fórmula de 2.1 [D].

Qué se necesita de cada registro de 5 min: $\Theta_k$ (`WindDir_D1_WVT`), $R_k$ (de `WindDir_SD1_WVT` por la
inversa de 2.2) y $n_k$. El logger **no** guarda $n_k$. Si el bloque no tuvo calmas, $n_k=60$ para todo *k* y se
simplifica (los pesos pasan a ser $R_k$). Si hubo calmas parciales:
- Si Campbell divide $U_x,U_y$ por las $n_k$ muestras válidas [NV], $n_k$ debe estimarse (la única aproximación
  del método exacto) y ignorarlo equivale a peso uniforme (ver tabla 4.4, fila B2).
- Si Campbell divide por $N=60$ [NV], entonces $60R_k$ ya es la longitud del vector suma y $n_k$ no hace falta.
  Se puede determinar cuál es mirando, en bloques con calmas parciales, si $R_k$ recuperada cae.

### 4.2 Qué se pierde si solo se conoce `WindDir_Avg` y la velocidad

De cada registro se conoce únicamente $\bar\theta_k^{\text{arit}}$ y $S_k$. Se pierde:

1. $R_k$ (la concentración del bloque). Sin ella, bloques muy dispersos pesan igual que los muy
   concentrados.
2. $n_k$ (cuántas muestras eran válidas).
3. La propia dirección del bloque: $\bar\theta_k^{\text{arit}}\ne\Theta_k$ en general (errores en 4.3).

Aproximaciones posibles:

- **H1**: peso unitario, $\hat\Theta=\operatorname{atan2}(\sum\sin\bar\theta_k,\ \sum\cos\bar\theta_k)$.
- **H2**: peso por velocidad, $w_k=S_k$. Es la mezcla de Θu con Θ1 y **no** aproxima a Θ1: aumenta el error cuando
  velocidad y dirección covarían.
- **H3**: ignorar $R_k$ (equivale a H1 o H2).
- **H4**: media aritmética de los 12 `WindDir_Avg` (inaceptable cerca del norte).

Estructura del error (orden uno) [D]: si el peso correcto es $a_k=n_kR_k$ y el usado es $b_k$ (ambos
normalizados a suma 1), el error angular horario es aproximadamente
$$\Delta\approx R_{\text{hora}}^{-1}\sum_k(b_k-a_k)\,\sin(\Theta_k-\Theta_{\text{hora}})\ \ [\text{rad}]$$
(además del error de dirección propio de cada bloque). Es proporcional a **cuánto cambia la dirección de un
bloque a otro dentro de la hora** multiplicado por **cuánto se equivocan los pesos**. Si la dirección es estable
dentro de la hora, el error de pesos casi no se nota.

### 4.3 Tamaño del error esperable

Casos donde la dirección del bloque ($\bar\theta_k^{\text{arit}}$) falla [D]:
- **Cruce por el norte**: un bloque cuyas muestras caen a ambos lados del 0° tiene $\bar\theta_k^{\text{arit}}$
  hacia el lado opuesto del círculo. El error del bloque llega a 180° y ninguna recomposición vectorial posterior lo
  repara, porque el dato de partida ya está dañado. Ocurre cuando la dirección del bloque está dentro de ~2σ del norte.
- **σ grande (R pequeña)**: la dirección de un bloque con $R_k\to0$ no está definida; pero su peso también tiende
  a 0, y por eso en el método exacto no importa; en H1 (peso unitario) sí.
- **Calmas**: `WindDir_Avg` promedia también las muestras con velocidad cero (la veleta puede seguir dando una lectura),
  mientras Θ1 las excluye; con calmas parciales, ambos usan conjuntos de muestras distintos.

Simulación sintética [S]. Modelo: 720 muestras/hora, dirección = media + componente lenta AR(1) (τ = 20 min) +
componente rápida AR(1) (τ = 30 s), velocidad lognormal con umbral 0,5 m/s → calma, zona muerta 355–360° → 0,
`WindDir_Avg` y Θ1 de 5 min redondeados a 0,1°, σ a 0,01°; 1 500 horas por escenario. Error angular absoluto
respecto del Θ1 horario calculado con las 720 muestras (media / percentil 95 / máximo, en grados):

| Escenario | σ hora (°) | Calmas | Exacto (Θ1_k, R_k por inversa de σ, n_k) | Θ1_k, peso n_k, sin R_k | Avg_k vectorial, peso 1 | Avg_k vectorial, peso S_k | Media aritm. de 12 Avg |
|---|---:|---:|---|---|---|---|---|
| Estable, lejos del norte (180°) | 11 | 0,1 % | 0,01 / 0,02 / 0,03 | 0,01 / 0,03 / 0,07 | 0,01 / 0,04 / 0,42 | 0,67 / 1,8 / 4,4 | 0,02 / 0,06 / 0,44 |
| Variable, lejos del norte | 23 | 0 % | 0,01 / 0,02 / 0,03 | 0,07 / 0,20 / 0,81 | 0,08 / 0,21 / 0,78 | 1,6 / 4,4 / 9,9 | 0,18 / 0,60 / 2,5 |
| Muy variable, viento débil (180°) | 38 | 2,6 % | 0,01 / 0,02 / 0,03 | 0,32 / 0,90 / 4,7 | 0,69 / 2,0 / 21 | 2,5 / 6,6 / 22 | 1,0 / 3,2 / 22 |
| Calmas frecuentes (este) | 18 | 24 % | 0,01 / 0,02 / 0,03 | 0,04 / 0,11 / 0,33 | 1,35 / 3,6 / 18 | 1,1 / 2,8 / 5,7 | 1,35 / 3,6 / 18 |
| Estable, **cruce por norte** | 11 | 0 % | 0,01 / 0,02 / 0,03 | 0,01 / 0,03 / 0,05 | **65 / 159 / 180** | 65 / 159 / 180 | **102 / 173 / 180** |
| Variable, cruce por norte | 23 | 0 % | 0,01 / 0,02 / 0,03 | 0,07 / 0,19 / 0,57 | 63 / 160 / 180 | 63 / 160 / 180 | 105 / 173 / 180 |
| Calmas, cruce por norte | 18 | 25 % | 0,01 / 0,02 / 0,03 | 0,04 / 0,12 / 0,30 | 57 / 148 / 180 | 59 / 153 / 180 | 105 / 172 / 180 |

Lectura:
1. Si se dispone de $\Theta_k$ y $\sigma_k$ de los registros de 5 min, la recomposición exacta con R recuperada
   por inversión reproduce el Θ1 horario con error < 0,03° (solo redondeo). Es una recomposición, no una
   aproximación [S confirma D].
2. Usar $\Theta_k$ sin $R_k$ (solo peso por número de muestras) ya cuesta poco: p95 < 1° incluso con σ de hora de 38° [S].
3. Con `WindDir_Avg` lejos del norte: error típico < 0,1° en viento estable, 0,7° en muy variable; p95 2–4°; máximos
   de ~20° en horas muy variables o con calmas. Ponderar por velocidad empeora (hasta 6,6° p95) porque estima Θu,
   no Θ1 [S].
4. Con `WindDir_Avg` y cruce por el norte el error no es pequeño: media de 60–100° y p95 > 150°, ya sea por
   promedio aritmético o vectorial de los `Avg` [S]. Cuantitativamente, la fracción de horas afectadas
   es la probabilidad de que la dirección de la hora esté dentro de ~2σ de 0°/360°; en un sitio con viento
   dominante del sector N/NNE/NNW esa fracción puede ser alta, en uno con viento del sur es ~0.
5. Aviso: el modelo es sintético (no incluye ciclo diurno, rotaciones ni deriva de sensor). Las magnitudes sirven
   para jerarquizar métodos, no como incertidumbre de campo.

Criterios de detección derivados [D] (sin código): (a) un bloque está dañado si
$|\bar\theta_k^{\text{arit}}-\Theta_k|$ (diferencia circular) supera unos pocos grados cuando ambos existen;
(b) una hora está en riesgo si la dirección media o algún `Avg_k` está a menos de ~2σ del norte;
(c) las diferencias entre estadísticos deben medirse siempre con la diferencia circular
$((a-b+180)\bmod360)-180$ y nunca con la resta directa.

---

## 5. Tratamiento de calmas (velocidad 0)

Una muestra con $s_i=0$ no tiene dirección definida: el vector es nulo. Por eso Campbell la excluye del
cálculo de Θ1, Θu y σ ("measurements at zero wind speed are not used in vector speed or direction
calculations"), aunque sí entra en la velocidad escalar S [V].

**Por qué aparece 0°.** La documentación consultada dice que, con entradas NAN en velocidad o dirección, la
dirección y la desviación estándar se almacenan como **0** [V]. Para el caso de un intervalo con todas las
muestras en calma (sin vectores acumulados), el valor 0° es consistente con $\operatorname{atan2}(0,0)=0$; que
esa sea la causa exacta no figura en la documentación y se queda como inferencia [NV]. Lo importante es que 0°
**no es una medición**: es el valor por defecto y coincide con la dirección norte.

Consecuencias para cualquier comparación o agregación [D]:
1. Un registro con $S_k=0$ (o con todas las muestras en calma) debe tratarse como **dato faltante** en dirección
   (no como 0°), y en rosas de viento contarse como "calma", no como sector N.
2. Para comparar Θ1 con `WindDir_Avg` hay que tener en cuenta que `WindDir_Avg` sí incluye las muestras en calma.
   Comparación limpia: excluir los bloques con alguna muestra en calma, o al menos los de $S_k$ por debajo del
   umbral.
3. En la recomposición horaria, los bloques calmos tienen peso $n_kR_k=0$ y no entran; si los 12 son calmos,
   la hora es calma (NaN).
4. Umbral de calma: EPA 2000, < 0,5 m/s en monitoreo en sitio, o el umbral de arranque del sensor si es mayor; la WMO,
   < 1 kn (~0,51 m/s), con dirección 00 [V]. Esa codificación "00" es para el reporte sinóptico; en análisis
   estadístico la dirección de una calma debe quedar vacía.
5. Para dispersión (EPA): las calmas se marcan y se conservan los datos originales; los modelos estacionarios
   sustituyen < 1 m/s por 1 m/s [V].

Con velocidades muy bajas (cerca del umbral) la dirección es válida pero ruidosa (meandro); R baja y su
peso en la recomposición se reduce automáticamente, otra ventaja del esquema exacto.

---

## 6. Recomendación fundamentada

1. Reporte ambiental: usar Θ1 (vector unitario) con la velocidad escalar S. Certeza alta (EPA 2008 §2.8.1, WMO 2008, NDBC, Campbell OutOpt 0) [V].
2. `WindDir_Avg` no es válida en horas cuya dirección esté a menos de ~2σ del norte: errores de decenas de grados, hasta 180°. Certeza alta [D, S].
3. Lejos del norte, la diferencia es < 1° con viento estable y p95 de 2–4° con viento muy variable o calmas. Certeza media (simulación sintética) [S].
4. La media aritmética solo sería defendible en un sitio sin vientos de ~330° a ~30°, aceptando ese margen de unos grados; no tiene respaldo normativo. Certeza media-alta.
5. Θu / U solo sería preferible para modelos de trayectoria variable o estudios de advección, no para rosas ni dispersión gaussiana. Certeza media [V: Campbell].
6. El Θ1 horario sale exacto de 12 registros de 5 min con Θ1_k, σ_k (→R_k) y n_k; solo con `WindDir_Avg` es aproximado y no confiable cerca del norte. Certeza alta (identidad algebraica).
7. La inversión de σ exige Subinterval=0 y conocer el denominador (n o N) de Ux, Uy en bloques con calmas parciales. Certeza baja hasta verificarlo con datos [NV].
8. Excluir calmas (S=0 o por debajo de 0,5 m/s) de la dirección y comparar siempre con diferencia circular. Certeza alta [V: Campbell, EPA, WMO].

---

## 7. Resumen de lo no verificado

- Texto de WMO-No. 8 ediciones 2018 y posteriores (solo se leyó la 7.ª ed., 2008).
- Contenido de ASTM D5741, ISO y VDI 3786-2 sobre la dirección media.
- Que `WindDir_Avg` (instrucción `Average`) no desenrolla el ángulo: es dato del usuario, la documentación de
  `Average` no se consultó.
- El denominador exacto (n o N) de $U_x,U_y$ en Campbell y el valor devuelto en intervalos totalmente calmos
  (sólo se documenta el 0 en el caso de entradas NAN).
- El artículo original de Yamartino (1984) y el libro de Mardia y Jupp (2000): se citan a partir de las fuentes
  secundarias y de las guías EPA que los referencian.
- Las cifras de error de la sección 4.3 proceden de una simulación sintética; no son datos de campo.

## 8. Referencias

- Campbell Scientific, CRBasic Editor Help: *WindVector()*.
  https://help.campbellsci.com/crbasic/cr6/Content/Instructions/windvector.htm  y
  *Wind Vector Calculations*: https://help.campbellsci.com/crbasic/cr6/Content/Info/wv_calculations.htm
  (consultadas; ecuaciones leídas de las imágenes de la página).
- Campbell Scientific, tipos de datos (FP2): https://help.campbellsci.com/crbasic/cr1000x/Content/Info/datatypes.htm
- U.S. EPA (2000). *Meteorological Monitoring Guidance for Regulatory Modeling Applications*, EPA-454/R-99-005.
  https://www.epa.gov/sites/production/files/2020-10/documents/mmgrma_0.pdf
- U.S. EPA (2008). *Quality Assurance Handbook for Air Pollution Measurement Systems, Volume IV: Meteorological
  Measurements*, Version 2.0, EPA-454/B-08-002.
  https://19january2021snapshot.epa.gov/sites/static/files/2020-10/documents/volume_iv_meteorological_measurements.pdf
- WMO (2008). *Guide to Meteorological Instruments and Methods of Observation*, WMO-No. 8, 7.ª ed. (copia usada:
  https://www.weather.gov/media/epz/mesonet/CWOP-WMO8.pdf).
- Yamartino, R. J. (1984). A comparison of several "single-pass" estimators of the standard deviation of wind
  direction. *J. Climate Appl. Meteor.*, 23(9), 1362-1366. doi:10.1175/1520-0450(1984)023<1362:ACOSPE>2.0.CO;2
- Mardia, K. V. y Jupp, P. E. (2000). *Directional Statistics*. Wiley. [citada por la EPA como ref. 24; no consultada]
- Frenkiel (1951), citado por WMO-No. 8 §5.8.1 para $\bar U/S=1-\sigma^2/2$. [no consultada directamente]
- NOAA National Data Buoy Center, *What averaging procedures are performed on the wind measurements?*
  https://www.ndbc.noaa.gov/faq/wndav.shtml
