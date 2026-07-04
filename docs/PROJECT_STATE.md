# Estado del proyecto

> Este archivo es lo primero que hay que leer al retomar el proyecto en una sesión nueva
> (otra terminal, otro día). Se actualiza al final de cada sesión de trabajo.
> El plan completo aprobado vive en `docs/` como referencia de fases; aquí solo va el estado vivo.

## Fase actual

**Fase 1 completa (pipeline de datos), a punto de arrancar Fase 0** (especificación iterativa
de reglas) sobre datos reales ya descargados.

## Qué está hecho

- Estructura de carpetas creada (`config/`, `docs/`, `notebooks/00_rule_spec/`, `src/trading_ai/`, `scripts/`, `tests/`).
- Entorno virtual `.venv` (Python 3.10) creado e instalado (`pip install -e .`): pandas, mplfinance,
  MetaTrader5, smartmoneyconcepts, xgboost, shap, jupyter, etc. Todo instala sin errores.
- `config/symbols.yaml`, `config/timeframes.yaml`, `config/strategy_rules.yaml` creados con placeholders y lo ya confirmado (FVG/imbalance = FORMALIZADO).
- `docs/rule_decisions.md` creado con el mapa de conceptos y su estado (ver ese archivo para el detalle de cada regla).
- **Fase 1 (pipeline de datos) implementada y probada en vivo** contra el terminal MT5 del usuario
  (cuenta Pepperstone-Demo, login 61553390 — el terminal debe estar abierto y logueado para que
  `scripts/run_ingest.py` funcione):
  - `data/schema.py`, `data/mt5_client.py`, `data/store.py`, `data/ingest.py`, `strategy/interfaces.py` (interfaz `DataProvider`).
  - Se descargaron ~3 años de EURUSD/GBPUSD/US30/NAS100 en las 7 temporalidades configuradas → `data/raw/mt5/<symbol>/<timeframe>.parquet` (gitignored).
  - **Nota técnica importante**: `copy_rates_range` de MT5 falla con "Invalid params" si el rango
    pedido de una sola vez devolvería demasiadas barras (~71k+ observado para M15). `ingest.py`
    ahora pide los datos en trozos (`_CHUNK_DAYS` por timeframe) y concatena. Aun así, para M1/M5
    algunos símbolos devolvieron conteos redondos sospechosos (exactamente 100000 barras en varios
    casos) mientras otros no — no se investigó a fondo la causa exacta; **revisar antes de confiar
    en M1/M5 para el backtester real de Fase 4** (podría haber un límite adicional de MT5 o huecos
    reales de historia en el broker).
  - Código en la rama local `fase1-pipeline-datos` (no mergeada a main todavía — pendiente de tu revisión).

## Qué está pendiente (próximo paso concreto)

1. Revisar y aprobar (o pedir ajustes a) la rama `fase1-pipeline-datos` para mergearla a `main`.
2. Empezar el notebook `notebooks/00_rule_spec/01_swing_points.ipynb`: detectar swing points con heurística laxa sobre los datos ya descargados, renderizar ejemplos, iterar con el usuario.

## Conceptos de la estrategia — estado (ver docs/rule_decisions.md para detalle)

| Concepto | Estado |
|---|---|
| Multi-timeframe (jerarquía) | DEJADO A LA IA (parcial) — v1 usa jerarquías configurables plausibles |
| FVG / imbalance | **FORMALIZADO** (FVG clásico de 3 velas, confirmado) |
| Estructura interna (BOS/CHoCH internos) | Pendiente de especificar |
| Transferencia | Pendiente de especificar (concepto propio, sin equivalente estándar) |
| Order blocks / oferta-demanda | Pendiente de especificar (criterios generales ya confirmados) |
| Gatillo de entrada / confirmación | DEJADO A LA IA (parcial) — no es checklist AND fijo |
| Regla de salida (SL/TP) | Pendiente — debe cerrarse antes de Fase 3/4 |

## Ramas activas

- `main` — scaffold inicial, ya pusheado a `https://github.com/isaacroa-tr/BOT_IA`.
- `fase1-pipeline-datos` — pipeline de datos MT5 completo y probado, **solo local todavía**
  (el usuario pidió no subirla a GitHub por ahora hasta revisarla).

## Decisiones pendientes de aprobación del usuario

- Aprobar (o pedir cambios a) la rama `fase1-pipeline-datos` antes de mergear a `main` y/o subirla a GitHub.
- El siguiente hito que requiere revisión visual del usuario es el primer lote de ejemplos del
  notebook de swing points (Fase 0, paso 1).
