# Roadmap futuro — escalamiento de datos y motor de ejecución

> Documentar solamente. No implementar hasta que el volumen de historia en MT5 (2-3 años) se quede
> corto y el resto del pipeline (Fases 0-8) esté validado.

## Objetivo

Migrar la fuente de datos de MT5 (2-3 años por símbolo) a un motor con mucha más historia,
tipo QuantConnect/LEAN, para backtesting a mayor escala y, eventualmente, ejecución/paper trading
en la nube.

## Qué hace posible esta migración sin retrabajo

- `data/schema.py` define un esquema OHLCV canónico del que depende todo `structure/`, `zones/`,
  `signals/` y `strategy/` — ninguno de esos módulos conoce tipos de MT5 directamente.
- `strategy/interfaces.py` define `DataProvider` como interfaz abstracta. Hoy la implementa
  `MT5DataProvider`; mañana bastaría con implementar `LeanDataProvider` sobre la misma interfaz.
- La lógica de ejecución/salida de trades (`backtest/engine.py`) debe quedar detrás de una interfaz
  separada (`ExecutionModel`) para que un motor de ejecución en la nube sea una implementación
  alternativa, no una reescritura.

## Candidatos a reemplazar más adelante

- El backtester custom de la Fase 4 (`backtest/engine.py`), una vez el volumen de historia lo
  justifique, por el motor de LEAN.
