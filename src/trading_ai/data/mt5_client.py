"""Wrapper fino sobre el paquete MetaTrader5.

Requiere que el terminal MT5 esté abierto y logueado en Windows — este módulo
no gestiona credenciales ni abre el terminal, solo se conecta a la instancia
ya corriendo. `copy_rates_range` es una llamada por símbolo+timeframe (MT5 no
expone un fetch multi-timeframe nativo), de ahí que ingest.py itere.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

import MetaTrader5 as mt5

from trading_ai.data.schema import OHLCV_COLUMNS

_TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "1H": mt5.TIMEFRAME_H1,
    "4H": mt5.TIMEFRAME_H4,
    "1D": mt5.TIMEFRAME_D1,
}


class MT5ConnectionError(RuntimeError):
    pass


def connect() -> None:
    if not mt5.initialize():
        raise MT5ConnectionError(f"No se pudo conectar a MT5: {mt5.last_error()}")


def disconnect() -> None:
    mt5.shutdown()


def fetch_ohlcv(symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Descarga velas para un símbolo+timeframe y las normaliza al esquema canónico."""
    if timeframe not in _TIMEFRAME_MAP:
        raise ValueError(f"Timeframe no soportado: {timeframe}")

    rates = mt5.copy_rates_range(symbol, _TIMEFRAME_MAP[timeframe], start, end)
    if rates is None:
        raise MT5ConnectionError(
            f"copy_rates_range devolvió None para {symbol}/{timeframe}: {mt5.last_error()}"
        )

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time").sort_index()
    df = df.rename(columns={"tick_volume": "volume"})
    df = df[OHLCV_COLUMNS]
    return df
