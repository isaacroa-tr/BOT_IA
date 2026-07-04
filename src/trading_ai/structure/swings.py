"""Detección de estructura de mercado a partir de pivots locales fusionados.

Historial de este módulo (ver docs/rule_decisions.md para el detalle):
1. Ventana fija de N velas (`smc.swing_highs_lows`) — marcaba mini-rebotes
   como si fueran estructura real, sin respetar HH/HL ni LH/LL.
2. Confirmación por reversión de ATR — corregía la secuencia, pero el umbral
   de tamaño (ATR_MULT) es arbitrario y se comía swings reales que el
   usuario sí considera válidos.
3. Esta versión: pivots locales (cada vela que es el extremo entre sus dos
   vecinas inmediatas, sin excepción) fusionados hasta alternar. No hay
   ningún parámetro de tamaño/umbral — solo la forma real del precio.

Algoritmo:
1. Un pivot high es una vela cuyo high es mayor que el de la vela anterior
   y la siguiente (pivot low, simétrico con los lows). Esto captura
   literalmente cada giro del precio, sin perderse ninguno.
2. Se recorren los pivots en orden; cuando dos pivots del mismo tipo
   aparecen seguidos sin un pivot del tipo opuesto de por medio, se
   descarta el menos extremo y se conserva el otro. Se repite hasta que
   la secuencia alterna perfectamente (high, low, high, low, ...).

El resultado usa el mismo formato que `smartmoneyconcepts.smc.swing_highs_lows`
(columnas HighLow: 1=swing high/-1=swing low, Level: precio) para poder
alimentar directamente `smc.ob()` y el resto de funciones de esa librería.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def detect_structural_swings(df: pd.DataFrame) -> pd.DataFrame:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    n = len(df)

    swing_type = np.full(n, np.nan)
    swing_level = np.full(n, np.nan)

    if n < 3:
        return pd.DataFrame({"HighLow": swing_type, "Level": swing_level}, index=df.index)

    # Paso 1: pivots locales crudos (cada extremo entre sus dos vecinas inmediatas).
    merged_idx: list[int] = []
    merged_type: list[int] = []

    for i in range(1, n - 1):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            pivot_pos, pivot_type = i, 1
        elif lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            pivot_pos, pivot_type = i, -1
        else:
            continue

        # Paso 2: fusiona con el pivot anterior si es del mismo tipo,
        # quedándose con el más extremo, hasta que la secuencia alterne.
        if merged_type and merged_type[-1] == pivot_type:
            prev_pos = merged_idx[-1]
            is_more_extreme = (
                highs[pivot_pos] > highs[prev_pos]
                if pivot_type == 1
                else lows[pivot_pos] < lows[prev_pos]
            )
            if is_more_extreme:
                merged_idx[-1] = pivot_pos
        else:
            merged_idx.append(pivot_pos)
            merged_type.append(pivot_type)

    for pos, typ in zip(merged_idx, merged_type):
        swing_type[pos] = typ
        swing_level[pos] = highs[pos] if typ == 1 else lows[pos]

    return pd.DataFrame({"HighLow": swing_type, "Level": swing_level}, index=df.index)
