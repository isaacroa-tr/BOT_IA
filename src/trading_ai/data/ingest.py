"""Descarga OHLCV de MT5 para todos los símbolos/timeframes configurados y los guarda como Parquet.

Uso: ver scripts/run_ingest.py
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from trading_ai.data import mt5_client, store

CONFIG_ROOT = Path("config")

# MT5 rechaza copy_rates_range con "Invalid params" cuando el rango pedido
# devolvería demasiadas barras en una sola llamada (~71k observado para M15 en
# este broker). Se pide en trozos y se concatena para no depender de ese límite.
_CHUNK_DAYS = {
    "M1": 20,
    "M5": 60,
    "M15": 180,
    "M30": 365,
    "1H": 365,
    "4H": 365 * 2,
    "1D": 365 * 5,
}


def _load_yaml_list(filename: str, key: str) -> list[str]:
    with open(CONFIG_ROOT / filename, encoding="utf-8") as f:
        return yaml.safe_load(f)[key]


def _fetch_chunked(symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
    chunk_days = _CHUNK_DAYS[timeframe]
    chunks = []
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(days=chunk_days), end)
        chunks.append(mt5_client.fetch_ohlcv(symbol, timeframe, chunk_start, chunk_end))
        chunk_start = chunk_end
    df = pd.concat(chunks)
    return df[~df.index.duplicated(keep="last")].sort_index()


def ingest_all(start: datetime, end: datetime) -> None:
    symbols = _load_yaml_list("symbols.yaml", "symbols")
    timeframes = _load_yaml_list("timeframes.yaml", "timeframes")

    mt5_client.connect()
    try:
        for symbol in symbols:
            for timeframe in timeframes:
                print(f"Descargando {symbol}/{timeframe}...")
                df = _fetch_chunked(symbol, timeframe, start, end)
                store.save_ohlcv(symbol, timeframe, df)
                print(f"  {len(df)} velas guardadas.")
    finally:
        mt5_client.disconnect()
