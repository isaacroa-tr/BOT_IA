"""Capa de acceso a los datos OHLCV en disco (Parquet particionado por símbolo/timeframe).

Ningún otro módulo debe leer/escribir archivos directamente — siempre a través
de `get_ohlcv`/`save_ohlcv`, para que cambiar el formato de almacenamiento no
requiera tocar el resto del código.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from trading_ai.data.schema import validate_ohlcv
from trading_ai.strategy.interfaces import DataProvider

DATA_ROOT = Path("data/raw/mt5")


def _path_for(symbol: str, timeframe: str) -> Path:
    return DATA_ROOT / symbol / f"{timeframe}.parquet"


def save_ohlcv(symbol: str, timeframe: str, df: pd.DataFrame) -> None:
    validate_ohlcv(df)
    path = _path_for(symbol, timeframe)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def get_ohlcv(symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
    path = _path_for(symbol, timeframe)
    if not path.exists():
        raise FileNotFoundError(
            f"No hay datos guardados para {symbol}/{timeframe} en {path}. "
            "Corre scripts/run_ingest.py primero."
        )
    df = pd.read_parquet(path)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    start_ts = start_ts.tz_localize("UTC") if start_ts.tzinfo is None else start_ts.tz_convert("UTC")
    end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
    return df.loc[start_ts:end_ts]


class MT5DataProvider(DataProvider):
    """Implementación de DataProvider sobre los Parquet ya descargados de MT5."""

    def get_ohlcv(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        return get_ohlcv(symbol, timeframe, start, end)
