"""Detección de estructura de mercado por confirmación de reversión (no por ventana fija).

A diferencia de un detector de fractales de ventana fija (que marca cualquier
extremo local rodeado de N velas más pequeñas, capturando ruido de rango), aquí
un swing se extiende mientras el precio sigue haciendo nuevos extremos en la
misma dirección, y solo se confirma cuando aparece una reversión real —medida
como un retroceso de al menos `atr_mult` veces el ATR desde ese extremo—. Así
la secuencia resultante respeta Higher Highs/Higher Lows (alcista) o Lower
Highs/Lower Lows (bajista) por construcción, y cada leg queda ligado a un
movimiento impulsivo real (de donde sale el order block correspondiente).

Nota de diseño: la primera versión de este detector confirmaba un swing solo
cuando el precio rompía el swing opuesto anterior COMPLETO (el extremo
estructural previo). Eso resultó demasiado estricto — en una tendencia larga,
el precio puede tardar años en romper el extremo opuesto, así que colapsaba
tendencias enteras en un solo leg en vez de mostrar los HH/HL o LH/LL
intermedios. El umbral de ATR local corrige eso: confirma cada leg con
reversión genuina, sin exigir que se invalide toda la estructura previa.

El resultado usa el mismo formato que `smartmoneyconcepts.smc.swing_highs_lows`
(columnas HighLow: 1=swing high/-1=swing low, Level: precio) para poder
alimentar directamente `smc.ob()` y el resto de funciones de esa librería.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _atr(df: pd.DataFrame, period: int) -> np.ndarray:
    high, low, close = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    return pd.Series(tr).rolling(period, min_periods=1).mean().to_numpy()


def detect_structural_swings(
    df: pd.DataFrame, atr_period: int = 14, atr_mult: float = 3.0
) -> pd.DataFrame:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    atr = _atr(df, atr_period)
    n = len(df)

    swing_type = np.full(n, np.nan)
    swing_level = np.full(n, np.nan)

    if n < 2:
        return pd.DataFrame({"HighLow": swing_type, "Level": swing_level}, index=df.index)

    direction = "up"  # dirección del leg candidato en curso
    candidate_price = highs[0]
    candidate_idx = 0

    for i in range(1, n):
        threshold = atr_mult * atr[i]
        if direction == "up":
            if highs[i] > candidate_price:
                candidate_price = highs[i]
                candidate_idx = i
            elif candidate_price - lows[i] >= threshold:
                swing_type[candidate_idx] = 1
                swing_level[candidate_idx] = candidate_price
                direction = "down"
                candidate_price = lows[i]
                candidate_idx = i
        else:  # direction == "down"
            if lows[i] < candidate_price:
                candidate_price = lows[i]
                candidate_idx = i
            elif highs[i] - candidate_price >= threshold:
                swing_type[candidate_idx] = -1
                swing_level[candidate_idx] = candidate_price
                direction = "up"
                candidate_price = highs[i]
                candidate_idx = i

    return pd.DataFrame({"HighLow": swing_type, "Level": swing_level}, index=df.index)
