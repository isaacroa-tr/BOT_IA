# Estado del proyecto

> Este archivo es lo primero que hay que leer al retomar el proyecto en una sesión nueva
> (otra terminal, otro día). Se actualiza al final de cada sesión de trabajo.
> El plan completo aprobado vive en `docs/` como referencia de fases; aquí solo va el estado vivo.

## Fase actual

**Fase 0 — swings/legs formalizado, order blocks y transferencia formalizados e implementados
(sesión 2026-07-12/13, rama `flip-branch`).** Pipeline de datos (Fase 1) completo. El criterio de
swings/legs que se reinició desde cero el 2026-07-04 ya quedó descrito, formalizado y codificado
en `src/trading_ai/structure/swings.py` (no está vacío). Order blocks y transferencia también
están formalizados e implementados (`order_blocks.py`, `transfer.py`). Esta sesión encontró y
corrigió dos bugs reales (uno en `swings.py`, uno en `transfer.py`) mientras se revisaba el chart
interactivo contra casos puntuales que el usuario señaló a mano -- ver detalle abajo y en
`docs/rule_decisions.md`.

## Qué está hecho

- Estructura de carpetas, entorno virtual (Python 3.10), dependencias instaladas.
- `config/symbols.yaml`, `config/timeframes.yaml`, `config/strategy_rules.yaml`.
- **Fase 1 (pipeline de datos)** implementada y probada en vivo contra MT5 (Pepperstone-Demo, login
  61553390 — el terminal debe estar abierto y logueado). ~3 años de EURUSD/GBPUSD/US30/NAS100 en 7
  temporalidades descargados a `data/raw/mt5/` (gitignored, se refresca corriendo
  `.venv\Scripts\python.exe scripts\run_ingest.py --years 3` con MT5 abierto y logueado). Nota
  pendiente: revisar profundidad real de M1/M5 antes de confiar en ellos para el backtester (ver
  commit de Fase 1 para detalle). Vive en la rama local `fase1-pipeline-datos` (no mergeada a
  main, el usuario pidió no subirla a GitHub todavía).

### Fase 0 — swings/legs (`src/trading_ai/structure/swings.py`)

Criterio completo implementado: pivots locales crudos fusionados a la secuencia más extrema,
tendencia vigente + origen (el punto que hay que romper con CIERRE M5 para cambiar de
tendencia), origen que se profundiza sin quedar registrado como pierna propia mientras la
tendencia no cambia. Detalle completo del criterio en el docstring del módulo y en
`docs/rule_decisions.md`.

**Fix 2026-07-12 (`_raw_pivots`):** la comparación era estricta (`>`/`<`) en ambos lados, así que
una meseta (dos velas seguidas con el mismo high, o el mismo low) no generaba pivot en NINGUNA de
las dos. Eso podía borrar el único pivot que separaba dos rachas del mismo tipo mucho más
adelante, haciendo que un pivot posterior genuino compitiera -- y perdiera -- contra un extremo
mucho más viejo en vez de quedar registrado como su propio swing. Ahora es tolerante a empates del
lado izquierdo, estricta del derecho (se queda con la ÚLTIMA vela de la meseta). Caso real que
disparó el fix: EURUSD 1H 2026-07-02 11:00/12:00 (mismo high exacto, ver conversación de sesión).
Impacto en conteo de piernas (EURUSD, historia completa): 1D 12→12, 4H 190→188, 1H 609→630, M30
1067→1099, M15 1818→1888, M5 4550→4741, M1 3213→3782.

### Fase 0 — order blocks (`src/trading_ai/zones/order_blocks.py`)

Criterio de marcado FORMALIZADO: dentro de una pierna, la zona desde el origen hasta el borde del
primer FVG del impulso (contando desde el origen). Sin cambios esta sesión. Pendiente: regla
exacta de invalidación/mitigación (mecha vs. cierre) y los "muchos tipos" de OB que el usuario
mencionó sin detallar.

### Fase 0 — transferencia (`src/trading_ai/zones/transfer.py`)

Reprecisada dos veces esta sesión respecto a la versión original del 2026-07-04 (ver
`docs/rule_decisions.md` para la definición completa vigente). Resumen: `retro_leg` (CHoCH =
pierna anterior directamente; BOS = pseudo-pierna reconstruida) tiene su propio OB; "vela 1" es
la vela límite de ese OB; un pivot genuino a favor de la tendencia de la pierna nueva tiene que
caer dentro del rango PROPIO de esa vela (no toda la zona del OB) sin que ninguna mecha la
supere; el siguiente pivot en contra es la transferencia, y se le calcula su propio OB.

**Dos bugs reales encontrados y corregidos esta sesión** (además del fix de `swings.py` de
arriba):
1. El caso BOS nunca se evaluaba de verdad: exigía que el origen de la pierna nueva coincidiera
   EXACTAMENTE con el fin de la pierna anterior, pero `swings.py` profundiza el origen sin dejar
   eso registrado como pierna propia -- esa coincidencia exacta rara vez se daba. Antes del fix,
   cero transferencias BOS se detectaban en toda la historia de todas las temporalidades.
2. La búsqueda de toque/transferencia dentro de una pierna cortaba en `< e_pos` (estricto), lo que
   excluía el caso de una vela de rango amplio que es a la vez el pivot de retroceso
   (transferencia) Y, con su otro extremo, la misma vela que confirma la ruptura de la pierna.
   Ahora corta en `<= e_pos`.

Pendiente: caso simétrico bajista sin verificar con un ejemplo real explícito (los ejemplos reales
de esta sesión fueron todos alcistas); seguir revisando el chart contra más casos manuales del
usuario -- cada vez que se señaló un caso puntual salió un bug real, así que vale la pena seguir.

### Chart interactivo de validación (`notebooks/00_rule_spec/generate_chart_inspector.py`)

Script COMMITTEADO y reproducible (antes se regeneraba con scripts sueltos que no quedaban
guardados, lo que hacía que el zigzag de piernas pareciera cambiar entre sesiones sin razón clara
-- el usuario lo notó y pidió que dejara de pasar). Separa a propósito el dibujo del zigzag de
piernas (consume `swings.py` sin tocarlo) de la capa de OB/transferencia agregada encima. Genera
`notebooks/00_rule_spec/output/chart_inspector.html` (candles + zigzag + OBs + transferencias,
selector de símbolo/temporalidad, tooltip). Para regenerar con datos frescos: refrescar
`data/raw/mt5/` (ver arriba) y correr `.venv\Scripts\python.exe
notebooks\00_rule_spec\generate_chart_inspector.py`.

## Próximo paso concreto (retomar aquí)

- Seguir revisando `chart_inspector.html` contra más ejemplos manuales del usuario, en especial el
  caso simétrico bajista de transferencia (todavía no probado explícitamente).
- Decidir si mergear `flip-branch` a `fase0-swings` (o directamente a `main`) una vez que el
  usuario dé el visto bueno definitivo a los fixes de esta sesión.
- Cerrar la regla de invalidación/mitigación de order blocks (mecha vs. cierre) y los "muchos
  tipos" de OB.
- Especificar estructura interna (BOS/CHoCH internos) -- sigue sin definición.
- Cerrar regla de salida (SL/TP) antes de Fase 3/4.

## Conceptos de la estrategia — estado (ver docs/rule_decisions.md para detalle)

| Concepto | Estado |
|---|---|
| Multi-timeframe (jerarquía) | DEJADO A LA IA (parcial) — v1 usa jerarquías configurables plausibles |
| FVG / imbalance | **FORMALIZADO** (FVG clásico de 3 velas, confirmado) |
| Swings / legs / estructura | **FORMALIZADO** (`swings.py`) — fix de tie-breaking 2026-07-12 |
| Estructura interna (BOS/CHoCH internos) | Pendiente de especificar |
| Transferencia | **FORMALIZADO** (`transfer.py`) — reprecisada y con 2 bugs corregidos 2026-07-12; falta caso bajista |
| Order blocks / oferta-demanda | Criterio de marcado FORMALIZADO — falta invalidación/mitigación |
| Gatillo de entrada / confirmación | DEJADO A LA IA (parcial) — no es checklist AND fijo |
| Regla de salida (SL/TP) | Pendiente — debe cerrarse antes de Fase 3/4 |

## Ramas activas

- `main` — scaffold inicial, ya pusheado a `https://github.com/isaacroa-tr/BOT_IA`.
- `fase1-pipeline-datos` — pipeline de datos MT5 completo y probado, **solo local todavía**.
- `fase0-swings` — swings/legs formalizado + primera versión de order blocks/transferencia
  (2026-07-04). Pusheada a GitHub.
- `flip-branch` — creada desde `fase0-swings` el 2026-07-12, antes de tocar `swings.py`. Contiene
  la reprecisión de transferencia, los 2 bugs corregidos (BOS en `transfer.py`, tie-breaking en
  `swings.py`), y el script committeado del chart inspector. **Pusheada a GitHub, rama activa
  actual.**

## Decisiones pendientes de aprobación del usuario

- Aprobar la rama `fase1-pipeline-datos`.
- Validar los fixes de `flip-branch` contra más ejemplos manuales antes de decidir el merge a
  `fase0-swings`/`main`.
