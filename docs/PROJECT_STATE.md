# Estado del proyecto

> Este archivo es lo primero que hay que leer al retomar el proyecto en una sesión nueva
> (otra terminal, otro día). Se actualiza al final de cada sesión de trabajo.
> El plan completo aprobado vive en `docs/` como referencia de fases; aquí solo va el estado vivo.

## Fase actual

**Fase 0 — concepto "swings/legs" reiniciado desde cero (2026-07-04).** Pipeline de datos (Fase 1)
completo. Tras varias iteraciones sin llegar a una regla definitiva, el usuario pidió borrar el
historial detallado de este documento y de `rule_decisions.md`, vaciar `swings.py`, y volver a
describir el criterio completo desde el principio. El historial de iteraciones previas sigue
disponible en el historial de git de la rama `fase0-swings` (commits anteriores a este reset).

## Qué está hecho

- Estructura de carpetas, entorno virtual (Python 3.10), dependencias instaladas.
- `config/symbols.yaml`, `config/timeframes.yaml`, `config/strategy_rules.yaml`.
- **Fase 1 (pipeline de datos)** implementada y probada en vivo contra MT5 (Pepperstone-Demo, login
  61553390 — el terminal debe estar abierto y logueado). ~3 años de EURUSD/GBPUSD/US30/NAS100 en 7
  temporalidades descargados a `data/raw/mt5/` (gitignored). Nota pendiente: revisar profundidad
  real de M1/M5 antes de confiar en ellos para el backtester (ver commit de Fase 1 para detalle).
  Vive en la rama local `fase1-pipeline-datos` (no mergeada a main, el usuario pidió no subirla a
  GitHub todavía).

### Fase 0 — concepto "swings/legs" (`src/trading_ai/structure/swings.py`)

Reiniciado desde cero el 2026-07-04 a pedido del usuario: se vació `swings.py` y se quitó de
aquí el historial detallado de iteraciones previas (ventanas fijas, ATR, ruptura recursiva,
pivots simples, clasificación externa/interna). Ese historial completo sigue disponible en el
log de git de la rama `fase0-swings` si hace falta retomar algo puntual de ahí.

Imágenes de referencia relevantes (`docs/reference_images/` y `piernas_a_mi_estilo.jpg` en la
raíz del repo): diagramas de HH/HL, marcas manuales del usuario en EURUSD 1H/4H, y un diagrama
de "piernas a mi estilo" mostrando cómo el usuario agrupa oscilaciones internas dentro de una
leg mayor.

## Próximo paso concreto (retomar aquí)

- El usuario va a describir de nuevo, desde cero, el criterio completo para identificar
  swings/legs/estructura de mercado. Escuchar y documentar antes de volver a escribir código.
- Una vez descrito, formalizar en `docs/rule_decisions.md` y `config/strategy_rules.yaml`.
- Seguir con order blocks/transferencia (dependen de que cierre "swings/legs" primero).

## Conceptos de la estrategia — estado (ver docs/rule_decisions.md para detalle)

| Concepto | Estado |
|---|---|
| Multi-timeframe (jerarquía) | DEJADO A LA IA (parcial) — v1 usa jerarquías configurables plausibles |
| FVG / imbalance | **FORMALIZADO** (FVG clásico de 3 velas, confirmado) |
| Swings / legs / estructura | Pendiente de especificar — reiniciado desde cero (2026-07-04) |
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

- Aprobar la rama `fase1-pipeline-datos` y decidir si subir `fase0-swings` a GitHub.
