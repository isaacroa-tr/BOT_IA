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

**Estado: EN ITERACIÓN ACTIVA (no cerrado) — ver `docs/PROJECT_STATE.md` para el estado sesión a sesión**

Historial resumido (detalle completo en PROJECT_STATE.md y en los commits de la rama `fase0-swings`):
1. Ventana fija de N velas → rechazada, marcaba ruido sin respetar HH/HL ni LH/LL.
2. Confirmación por reversión de ATR → rechazada, umbral arbitrario que se comía swings válidos.
3. Pivots locales fusionados hasta alternar (sin umbral) → pedido explícito del usuario, funciona
   bien para ventanas cortas pero es muy denso sobre todo el histórico.
4. Confirmación por ruptura recursiva (romper el swing del mismo tipo anterior) → pedido también
   por el usuario, pero **descartada tras pruebas extensas**: colapsa la estructura a muy pocos
   puntos sin importar la ventana de tiempo usada. No volver a intentar esta variante tal cual.
5. Bug real encontrado y corregido: una vela puede ser pivot high y low a la vez (rango amplio);
   el código con `if/elif` perdía uno de los dos silenciosamente. Corregido en
   `detect_structural_swings_list()` (`src/trading_ai/structure/swings.py`).
6. Con el bug corregido, el detector simple (pivots + fusión, sin ruptura) aplicado sobre velas
   4H reproduce los 6 puntos que el usuario marcó a mano como referencia, pero también genera
   ~8 puntos "extra" no marcados. El usuario indicó que descarta esos extras por dos razones:
   (a) algunos son simplemente muy pequeños, y (b) hay una regla adicional que notó tener pero
   **todavía no ha explicado** — pendiente para la próxima sesión, preguntar directamente antes
   de seguir probando variantes de código a ciegas.

Imágenes de referencia en `docs/reference_images/`:
- `Ejemplo de estructura de mercado alcista en una temporalidad arbitraria.jpg` (diagrama HH/HL genérico).
- `Como yo habría marcado las ultimas 4 legs en EURUSD.png` (1H, con anotaciones de OB/transferencia).
- `Como yo habría marcado las ultimas 4 legs en EURUSD en 4H.png` (la misma referencia en 4H).

## FVG / Imbalance

**Estado: FORMALIZADO**

Confirmado por el usuario: su definición de "imbalance" sí es el FVG clásico (gap de 3 velas), no una variante propia. No requiere iteración adicional en Fase 0.

## Estructura interna (BOS/CHoCH internos)

**Estado: pendiente de especificar (Fase 0)**

El usuario indicó que hay estructura interna (rangos internos dentro de un swing mayor) que quiere tratar en detalle. Sin definición todavía — pendiente para el notebook `03_bos_choch_internal.ipynb`.

## Transferencia

**Estado: pendiente de especificar (Fase 0)**

Concepto propio del usuario, fundamental para su estrategia: cuando el precio rompe una zona/order block, o rompe un high/low que tiene dibujado un OB sin mitigar, la relevancia de esa zona se transfiere a otra zona cercana. Sin equivalente estándar en librerías SMC (`smartmoneyconcepts` no lo cubre) — se construirá 100% custom en `zones/transfer.py` una vez formalizado con ejemplos reales en el notebook correspondiente de Fase 0.

## Order blocks / zonas de oferta-demanda

**Estado: pendiente de especificar (Fase 0)**

Criterios ya confirmados por el usuario (a formalizar con parámetros concretos en Fase 0):
- Última vela opuesta antes del impulso.
- Requiere FVG (imbalance clásico) tras el impulso.
- Zona debe estar "fresca" (no testeada desde su formación) — regla exacta de invalidación (mecha vs. cierre) pendiente.
- Requiere ruptura de estructura (BOS/CHOCH) confirmada.

## Gatillo de entrada / confirmación

**Estado: DEJADO A LA IA (parcialmente)**

El usuario confirmó que las señales de confirmación (CHOCH/BOS en LTF, patrón de vela, barrido de liquidez) no son un checklist AND fijo — pueden estar presentes en cualquier combinación. Además, cuando el movimiento en HTF **no** es muy extenso, a veces entra sin ninguna confirmación. Para v1 (Fase 3) se generan candidatos por combinación de señales presentes/ausentes, maximizando recall; el patrón real de cuándo cada combinación es suficiente es candidato a ser capturado por el modelo de IA.

## Regla de salida (SL/TP)

**Estado: pendiente de especificar (Fase 0/antes de Fase 3-4)**

No definida todavía. Debe cerrarse antes de construir el backtester (Fase 4).
