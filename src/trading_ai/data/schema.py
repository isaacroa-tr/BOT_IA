"""Esquema OHLCV canónico.

Todo módulo de structure/, zones/, signals/ y strategy/ opera únicamente sobre
DataFrames con este esquema — nunca sobre objetos específicos de MT5 (ni, en el
futuro, de un motor tipo QuantConnect/LEAN). Esto es lo que permite cambiar la
fuente de datos sin tocar la lógica de estrategia (ver docs/roadmap_future_scaling.md).
"""

from __future__ import annotations

import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def validate_ohlcv(df: pd.DataFrame) -> None:
    """Lanza un error si el DataFrame no cumple el esquema canónico.

    Esquema: índice datetime en UTC, ordenado ascendentemente, sin duplicados,
    y columnas open/high/low/close/volume en minúsculas.
    """
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas OHLCV: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("El índice debe ser un DatetimeIndex")
    if df.index.tz is None or str(df.index.tz) != "UTC":
        raise ValueError("El índice debe estar en UTC")
    if not df.index.is_monotonic_increasing:
        raise ValueError("El índice debe estar ordenado ascendentemente")
    if df.index.has_duplicates:
        raise ValueError("El índice no debe tener timestamps duplicados")
