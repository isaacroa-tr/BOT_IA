# Bitácora de decisiones de reglas

Un registro por concepto de la estrategia. Cada concepto queda en uno de tres estados:

- **FORMALIZADO** — regla objetiva cerrada, codificada en `config/strategy_rules.yaml`.
- **PARAMETRIZADO-PENDIENTE** — hay una regla con hueco; se usa una heurística provisional marcada como ajustable.
- **DEJADO A LA IA** — no se puede articular como regla; se documenta con ejemplos concretos donde la decisión del usuario difirió de la regla objetiva. Alimenta el feature engineering de la Fase 7.

---

## Multi-timeframe (análisis top-down)

**Estado: DEJADO A LA IA (parcialmente)**

El usuario confirmó que el uso de temporalidades (1D→M1) es contextual, sin jerarquía fija — depende de dónde se ve mejor la estructura/zona ese día. Para v1 (Fase 3) se usa un conjunto de jerarquías plausibles configurables en `config/timeframes.yaml` (`candidate_hierarchies`), documentado explícitamente como simplificación deliberada. El criterio real de selección de temporalidad es candidato a ser parte de lo que el modelo de IA capture (Fase 7), no una regla determinista.

## Swings / legs / estructura de mercado

**Estado: pendiente de especificar (Fase 0) — reiniciado desde cero el 2026-07-04**

Se descartaron varias iteraciones previas (ventanas fijas, confirmación por ATR, ruptura
recursiva, detector de pivots simple con clasificación externa/interna) sin llegar a una regla
que el usuario aceptara como definitiva. El detalle completo de esas iteraciones quedó fuera de
este documento a pedido del usuario, pero sigue disponible en el historial de git de la rama
`fase0-swings` (commits previos al reset) por si hace falta retomar algo de ahí.

Imágenes de referencia en `docs/reference_images/` (y `piernas_a_mi_estilo.jpg` en la raíz del
repo, pendiente de mover a esa carpeta):
- `Ejemplo de estructura de mercado alcista en una temporalidad arbitraria.jpg` (diagrama HH/HL genérico).
- `Como yo habría marcado las ultimas 4 legs en EURUSD.png` (1H, con anotaciones de OB/transferencia).
- `Como yo habría marcado las ultimas 4 legs en EURUSD en 4H.png` (la misma referencia en 4H).

## FVG / Imbalance

**Estado: FORMALIZADO**

Confirmado por el usuario: su definición de "imbalance" sí es el FVG clásico (gap de 3 velas), no una variante propia. No requiere iteración adicional en Fase 0.

## Estructura interna (BOS/CHoCH internos)

**Estado: pendiente de especificar (Fase 0)**

El usuario indicó que hay estructura interna (rangos internos dentro de un swing mayor) que quiere tratar en detalle. Sin definición todavía — pendiente para el notebook `03_bos_choch_internal.ipynb`. Su relación con "swings/legs" (¿concepto separado o la misma pieza de diseño?) queda abierta hasta que se re-especifique swings/legs desde cero.

## Order blocks / zonas de oferta-demanda

**Estado: criterio de marcado FORMALIZADO (2026-07-04) — falta cerrar invalidación/mitigación**

El usuario aclaró que hay muchos "tipos" de OB pero todos se marcan igual: dentro de una pierna
(según la definición de `swings.py`), escaneando desde el FINAL de la pierna hacia el ORIGEN, el
OB es la zona desde el origen de la pierna hasta la mecha de la primera vela (yendo hacia atrás)
que **ya no** forma parte de la cadena de FVG del impulso. Ejemplo confirmado: pierna alcista
low(vela1)→high(vela10), velas 4-6 forman una cadena de FVG (imbalances encadenados), vela 3 es
la primera vela (yendo de la 10 hacia la 1) que no tiene FVG asociado → el OB es la zona
vela1→vela3 (la consolidación/base antes de que arranque el impulso), no solo la última vela
opuesta como en la definición ICT clásica de un único FVG.

Pendiente todavía: regla exacta de invalidación/mitigación (mecha vs. cierre) y si aplica el
mismo criterio a "muchos tipos" que el usuario mencionó sin detallar.

## Transferencia

**Estado: criterio FORMALIZADO (2026-07-12, reprecisado respecto a la versión del 2026-07-04)**

Concepto propio del usuario, sin equivalente estándar en librerías SMC. Ejemplo de referencia:
`ejemplo_transferencia.jpg` (el dibujo `piernas_a_mi_estilo.jpg` no alcanzaba a mostrar el caso
con precisión).

Definición exacta (reemplaza la versión de 2026-07-04, que usaba la zona completa del OB como
nivel de toque -- ver historial de git de este archivo para la versión vieja):

1. `retro_leg` = el retroceso previo al origen de la pierna nueva L. Si la pierna anterior
   (`prev_leg`) es de tendencia OPUESTA a L (**CHoCH**), `retro_leg` = `prev_leg` directamente. Si
   `prev_leg` es de la MISMA tendencia que L (**BOS**), el retroceso previo nunca validó como
   pierna propia -- se reconstruye como una pseudo-pierna opuesta desde el fin de `prev_leg` hasta
   el origen de L (el origen real de L casi nunca coincide con el fin exacto de `prev_leg` --
   `swings.py` puede profundizar el origen muchas velas después sin que quede registrado como
   pierna propia; la pseudo-pierna se reconstruye igual, sin importar el tamaño de ese hueco --
   bug corregido 2026-07-12, la versión anterior exigía coincidencia exacta y dejaba el conteo de
   transferencias BOS en cero en toda la historia).
2. Se calcula el Order Block de `retro_leg` con la función ya existente `detect_order_block()`
   (sin cambios respecto a la definición de OB ya formalizada). La vela límite de ese OB (el
   borde del primer FVG de `retro_leg`, contando desde SU origen) es "vela 1".
3. Mientras se forma L, tiene que aparecer un **pivot genuino** (un extremo local real de la
   secuencia de swings, no cualquier mecha de paso) del tipo a favor de la tendencia de L, cuyo
   precio caiga **dentro del rango propio de vela 1** (entre su low y su high) -- no en toda la
   zona del OB de `retro_leg`, solo en el rango de esa vela puntual. Cualquier mecha posterior que
   supere ese rango (por fuera de vela 1, en la dirección de continuación) invalida el toque --
   más estricto que la regla de cierre M5 usada en el resto del criterio (acá ninguna mecha puede
   pasarse, no solo el cierre).
4. El siguiente pivot (en contra de la tendencia de L) inmediatamente después de ese toque es la
   **transferencia**.
5. A ese pivot se le calcula su propio Order Block con la misma `detect_order_block()`, tratando
   el tramo toque→transferencia como una pierna nueva (tendencia opuesta a L, mismo signo que
   `retro_leg`). Esa zona es la que se dibuja como "Transferencia" en `ejemplo_transferencia.jpg`.
6. Después el precio rompe estructura de verdad desde ese pivot, validando L (la ruptura en sí ya
   está cubierta por la lógica de piernas existente en `swings.py`, sin cambios).

La relevancia (la zona a la que hay que prestarle atención si el precio retrocede después) pasa
de OB-B (el OB de `retro_leg`) a este punto de transferencia, una vez que OB-B queda
roto/invalidado por el impulso del paso 6.

**Transferencias encadenadas**: confirmado por el usuario que sí puede pasar -- el mismo patrón
se puede repetir sobre T1 (se toca, retrocede, rompe) generando T2, y así sucesivamente. Pero el
peso/relevancia de cada Tn depende del contexto: mientras la pierna principal no se rompa (no
retroceda más allá de su propio origen), varias zonas quedan relevantes al mismo tiempo -- el OB
del origen de la pierna principal sigue teniendo peso independientemente de cuántas
transferencias haya encadenadas después. No es "la última transferencia reemplaza a todas las
anteriores"; es una jerarquía de zonas simultáneamente vigentes, similar a la relatividad
externa/interna que ya vimos en swings/legs.

**Importante (corrección del enfoque general del proyecto, 2026-07-04)**: el usuario aclaró que
no quiere dejar nada "a criterio de la IA" de forma permanente -- la intención es formalizar
TODO como reglas explícitas, para después poder encontrar un subconjunto de reglas que expliquen
los trades reales. Lo que en Fase 0 parece "contextual" (cómo priorizar varias zonas vigentes a
la vez, ej. transferencia T2 vs. el OB de la pierna principal) no es un criterio permanentemente
difuso -- se formaliza más adelante, en la fase de combinar varias temporalidades para tomar
decisiones (ahí es donde entra "el contexto": dónde está el precio ubicado respecto a la última
pierna de cada temporalidad). Queda pendiente para esa fase, no para el modelo de IA. Sin
formalizar todavía tampoco: el caso simétrico bajista de transferencia (por simetría debería ser
el mismo criterio invertido).

## Gatillo de entrada / confirmación

**Estado: DEJADO A LA IA (parcialmente)**

El usuario confirmó que las señales de confirmación (CHOCH/BOS en LTF, patrón de vela, barrido de liquidez) no son un checklist AND fijo — pueden estar presentes en cualquier combinación. Además, cuando el movimiento en HTF **no** es muy extenso, a veces entra sin ninguna confirmación. Para v1 (Fase 3) se generan candidatos por combinación de señales presentes/ausentes, maximizando recall; el patrón real de cuándo cada combinación es suficiente es candidato a ser capturado por el modelo de IA.

## Regla de salida (SL/TP)

**Estado: pendiente de especificar (Fase 0/antes de Fase 3-4)**

No definida todavía. Debe cerrarse antes de construir el backtester (Fase 4).
