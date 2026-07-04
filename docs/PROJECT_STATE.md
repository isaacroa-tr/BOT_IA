# Estado del proyecto

> Este archivo es lo primero que hay que leer al retomar el proyecto en una sesión nueva
> (otra terminal, otro día). Se actualiza al final de cada sesión de trabajo.
> El plan completo aprobado vive en `docs/` como referencia de fases; aquí solo va el estado vivo.

## Fase actual

**Fase 0 — Especificación iterativa de reglas.** Todavía no se ha corrido ningún notebook de
especificación con datos reales. Se acaba de terminar el scaffold inicial del proyecto.

## Qué está hecho

- Estructura de carpetas creada (`config/`, `docs/`, `notebooks/00_rule_spec/`, `src/trading_ai/`, `scripts/`, `tests/`).
- `pyproject.toml` con dependencias iniciales (pandas, mplfinance, MetaTrader5, smartmoneyconcepts, xgboost, shap, etc.) — **no instaladas todavía**.
- `config/symbols.yaml`, `config/timeframes.yaml`, `config/strategy_rules.yaml` creados con placeholders y lo ya confirmado (FVG/imbalance = FORMALIZADO).
- `docs/rule_decisions.md` creado con el mapa de conceptos y su estado (ver ese archivo para el detalle de cada regla).

## Qué está pendiente (próximo paso concreto)

1. Instalar dependencias (`pip install -e .` desde la raíz) y verificar que el paquete `MetaTrader5`
   puede conectarse con el terminal MT5 corriendo en Windows.
2. Crear `src/trading_ai/data/schema.py` (esquema OHLCV canónico) y `data/mt5_client.py` (wrapper de conexión).
3. Descargar 2-3 años de EURUSD/GBPUSD/US30/NAS100 en varias temporalidades para tener datos reales con qué trabajar en los notebooks de Fase 0.
4. Empezar el notebook `notebooks/00_rule_spec/01_swing_points.ipynb`: detectar swing points con heurística laxa, renderizar ejemplos, iterar con el usuario.

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

Ninguna todavía — el repo local aún no se ha inicializado con git. Próximo paso de infraestructura:
`git init`, commit inicial a `main`, conectar remoto `https://github.com/isaacroa-tr/BOT_IA` (pedir
confirmación al usuario antes del primer push, según el flujo de trabajo acordado).

## Decisiones pendientes de aprobación del usuario

- Ninguna bloqueante ahora mismo; el siguiente hito que requiere su revisión visual es el primer
  lote de ejemplos del notebook de swing points (Fase 0, paso 1).
