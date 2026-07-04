"""Interfaces abstractas que desacoplan la estrategia de la fuente de datos.

Ver docs/roadmap_future_scaling.md: hoy `DataProvider` lo implementa
`MT5DataProvider` (data/mt5_client.py); en el futuro podría implementarlo
un `LeanDataProvider` sin tocar structure/, zones/, signals/ ni strategy/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class DataProvider(ABC):
    @abstractmethod
    def get_ohlcv(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Devuelve un DataFrame con el esquema canónico (ver data/schema.py)."""
        raise NotImplementedError
