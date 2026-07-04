# Estado del proyecto

> Este archivo es lo primero que hay que leer al retomar el proyecto en una sesión nueva
> (otra terminal, otro día). Se actualiza al final de cada sesión de trabajo.
> El plan completo aprobado vive en `docs/` como referencia de fases; aquí solo va el estado vivo.

## Fase actual

**Fase 0 — concepto "swings/legs" en iteración activa con el usuario.** Pipeline de datos (Fase 1)
completo. El concepto de swing points/estructura de mercado NO está cerrado todavía — vamos por la
5ª iteración, cada vez más cerca pero con un detalle pendiente que el usuario todavía no ha
explicado (ver "Próximo paso" abajo). Sesión pausada a pedido del usuario (cansado), se retoma
mañana.

## Qué está hecho

- Estructura de carpetas, entorno virtual (Python 3.10), dependencias instaladas.
- `config/symbols.yaml`, `config/timeframes.yaml`, `config/strategy_rules.yaml`.
- **Fase 1 (pipeline de datos)** implementada y probada en vivo contra MT5 (Pepperstone-Demo, login
  61553390 — el terminal debe estar abierto y logueado). ~3 años de EURUSD/GBPUSD/US30/NAS100 en 7
  temporalidades descargados a `data/raw/mt5/` (gitignored). Nota pendiente: revisar profundidad
  real de M1/M5 antes de confiar en ellos para el backtester (ver commit de Fase 1 para detalle).
  Vive en la rama local `fase1-pipeline-datos` (no mergeada a main, el usuario pidió no subirla a
  GitHub todavía).

### Fase 0 — historial completo del concepto "swings/legs" (`src/trading_ai/structure/swings.py`)

Este es el hilo más largo e inconcluso de la sesión. Iteraciones, en orden:

1. **Ventana fija de N velas** (`smc.swing_highs_lows` de la librería `smartmoneyconcepts`) —
   rechazada: marcaba ruido, no respetaba secuencia Higher High/Higher Low ni Lower High/Lower Low.
   El usuario mandó una imagen de referencia (`docs/reference_images/Ejemplo de estructura de
   mercado alcista en una temporalidad arbitraria.jpg`) mostrando el patrón esperado.
2. **Confirmación por reversión de ATR** (`atr_mult` sobre el ATR local) — rechazada: umbral
   arbitrario que se comía swings reales que el usuario sí consideraba válidos.
3. **Pivots locales (1 vela) fusionados hasta alternar, sin umbral** — el usuario pidió esto
   explícitamente ("prefiero pivots"). Generaba demasiados puntos en todo el histórico (~6300 en 3
   años de 1H) pero funcionaba bien para ventanas cortas ("últimos N legs").
4. **Confirmación por ruptura recursiva** (un swing solo se confirma si rompe el swing del mismo
   tipo anterior a su retroceso) — el usuario pidió esto también, pero **probado extensamente
   (múltiples ventanas de tiempo, múltiples fechas de inicio) siempre colapsa la estructura a muy
   pocos puntos** (3-6 en 3 años, o 3-4 en solo 2-3 meses) — no reproduce estructura reciente
   razonable. **Descartada** — no volver a intentar esta variante tal cual.
5. **Estado actual**: el usuario mandó 2 imágenes de referencia muy valiosas —
   `docs/reference_images/Como yo habría marcado las ultimas 4 legs en EURUSD.png` (1H) y
   la misma pero en 4H — marcando a mano 6 puntos concretos. Al cruzarlos con los datos reales:
   - El usuario notó que **piensa en términos de 4H incluso mirando 1H** ("estaba eliminando el
     ruido de 1H sin darme cuenta") — pista importante: la escala de "swing real" depende de la
     temporalidad de referencia.
   - Se encontró y corrigió un **bug real**: una vela puede ser pivot high Y pivot low a la vez
     (vela de rango amplio); el código anterior (`if/elif`) solo capturaba uno de los dos,
     perdiendo silenciosamente el otro (justo un low que el usuario había marcado). Ahora
     `_raw_pivots()` emite ambos eventos, ordenados según la dirección de la vela (alcista → low
     antes que high; bajista → al revés, ya que solo hay OHLC, no ticks). Ver
     `detect_structural_swings_list()` (nueva función, sin pérdida — no reutiliza el índice de
     `df` como clave, porque una sola vela puede aportar 2 swings).
   - Con ese bug corregido, aplicando el detector simple (pivots + fusión, **sin** la regla de
     ruptura del punto 4) directamente sobre velas 4H, **los 6 puntos de referencia del usuario
     aparecen todos correctamente**.
   - Pero también aparecen **~8 puntos "extra"** que el usuario no marcó a mano, dentro de la misma
     ventana. Se generó una imagen comparativa (`notebooks/00_rule_spec/output/comparacion_4H_target_vs_extra.png`,
     puntos grandes rojo/verde = los del usuario, naranja/azul chico = los extra) para discutirlo.

## Próximo paso concreto (retomar aquí mañana)

El usuario dijo, textualmente, que hay dos razones por las que descarta esos puntos "extra":
1. **Algunos son simplemente muy pequeños** (posible criterio de significancia/tamaño relativo —
   ojo: esto es justo lo que ATR intentaba capturar y se rechazó antes; puede que la forma de
   medir "pequeño" sea distinta a ATR, o que aplique combinado con el punto 2).
2. **Hay una regla adicional que el usuario notó que tiene pero todavía NO ha explicado.**
   Mañana hay que preguntarle directamente cuál es esa regla antes de seguir ajustando código.

No adivinar más variantes algorítmicas sin esa explicación — ya se probaron ATR, ruptura
recursiva, y ventanas fijas de varios tamaños (3 a 10 velas) sin reproducir exactamente sus 6
puntos sin extras (ver commits de la rama `fase0-swings` para el detalle de cada intento fallido).

Una vez cerrado esto para 4H, falta:
- Confirmar si la misma lógica (aplicada a la temporalidad "nativa" de cada caso, no forzosamente
  4H) sirve para 1D, 1H, M30, M15, M5, M1, o si cada temporalidad necesita su propio ajuste.
- Formalizar en `docs/rule_decisions.md` y `config/strategy_rules.yaml` una vez cerrado.
- Seguir con order blocks/transferencia (ya usan `smc.ob()` alimentado por estos swings, pero
  deben re-verificarse una vez que el detector de swings quede definitivo).

## Conceptos de la estrategia — estado (ver docs/rule_decisions.md para detalle)

| Concepto | Estado |
|---|---|
| Multi-timeframe (jerarquía) | DEJADO A LA IA (parcial) — v1 usa jerarquías configurables plausibles |
| FVG / imbalance | **FORMALIZADO** (FVG clásico de 3 velas, confirmado) |
| Swings / legs / estructura | **EN ITERACIÓN ACTIVA** — ver historial arriba, no cerrado |
| Estructura interna (BOS/CHoCH internos) | Pendiente de especificar |
| Transferencia | Pendiente de especificar (concepto propio, sin equivalente estándar) |
| Order blocks / oferta-demanda | Depende de que cierre "swings/legs" primero |
| Gatillo de entrada / confirmación | DEJADO A LA IA (parcial) — no es checklist AND fijo |
| Regla de salida (SL/TP) | Pendiente — debe cerrarse antes de Fase 3/4 |

## Ramas activas

- `main` — scaffold inicial, ya pusheado a `https://github.com/isaacroa-tr/BOT_IA`.
- `fase1-pipeline-datos` — pipeline de datos MT5 completo y probado, **solo local todavía**.
- `fase0-swings` — todo el trabajo de este documento (notebooks, `swings.py`, imágenes de
  referencia). Rama activa actual. **Solo local, no pusheada.**

## Decisiones pendientes de aprobación del usuario

- Preguntar la regla adicional que el usuario mencionó y no explicó (ver "Próximo paso").
- Aprobar la rama `fase1-pipeline-datos` y decidir si subir `fase0-swings` a GitHub.
