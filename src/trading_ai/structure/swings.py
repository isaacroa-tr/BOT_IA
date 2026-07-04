"""Detección de estructura de mercado a partir de pivots locales fusionados.

Historial de este módulo (ver docs/rule_decisions.md para el detalle):
1. Ventana fija de N velas (`smc.swing_highs_lows`) — marcaba mini-rebotes
   como si fueran estructura real, sin respetar HH/HL ni LH/LL.
2. Confirmación por reversión de ATR — corregía la secuencia, pero el umbral
   de tamaño (ATR_MULT) es arbitrario y se comía swings reales que el
   usuario sí considera válidos.
3. Confirmación por ruptura recursiva (romper el swing del mismo tipo
   anterior) — colapsaba tendencias completas a 3-6 puntos en 3 años,
   demasiado agresivo: el usuario esperaba varios legs por semana, no por
   año.
4. El usuario marcó manualmente 6 puntos de referencia en 1H y notó que
   en realidad estaba percibiendo la estructura a nivel 4H sin darse
   cuenta ("estaba eliminando el ruido de 1H"). Al aplicar el detector de
   pivots simple (sin ruptura) directamente sobre velas 4H, casi
   reproduce sus puntos exactos -- la escala correcta para "un swing
   real" depende de la temporalidad de referencia, no de un umbral extra.
5. Bug encontrado al validar contra sus datos: una vela puede ser pivot
   high Y pivot low al mismo tiempo (vela de rango amplio). El código
   anterior (`elif`) solo capturaba uno de los dos, perdiendo silenciosamente
   el extremo descartado -- justo el low que el usuario había marcado.
   Ahora se emiten ambos eventos, ordenados según si la vela cierra por
   encima o por debajo de su apertura (vela alcista -> low antes que high;
   vela bajista -> high antes que low), ya que solo tenemos OHLC, no datos
   de tick.

El resultado usa el mismo formato que `smartmoneyconcepts.smc.swing_highs_lows`
(columnas HighLow: 1=swing high/-1=swing low, Level: precio) para poder
alimentar directamente `smc.ob()` y el resto de funciones de esa librería.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _raw_pivots(df: pd.DataFrame) -> list[tuple[int, int]]:
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    opens = df["open"].to_numpy()
    closes = df["close"].to_numpy()
    n = len(df)

    pivots: list[tuple[int, int]] = []
    for i in range(1, n - 1):
        is_high = highs[i] > highs[i - 1] and highs[i] > highs[i + 1]
        is_low = lows[i] < lows[i - 1] and lows[i] < lows[i + 1]
        if is_high and is_low:
            # Vela de rango amplio: es pivot en ambos sentidos. Sin datos de
            # tick, se asume el orden según la dirección de la vela.
            if closes[i] >= opens[i]:
                pivots.append((i, -1))
                pivots.append((i, 1))
            else:
                pivots.append((i, 1))
                pivots.append((i, -1))
        elif is_high:
            pivots.append((i, 1))
        elif is_low:
            pivots.append((i, -1))
    return pivots


def detect_structural_swings_list(df: pd.DataFrame) -> list[tuple[int, int, float]]:
    """Devuelve cada swing confirmado como (posición, tipo, precio), sin pérdida.

    A diferencia de `detect_structural_swings`, no reutiliza el índice de
    `df` como clave -- así una vela que sea pivot high y low a la vez (rango
    amplio) puede aportar dos swings distintos sin que uno pise al otro.
    """
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()

    stack_pos: list[int] = []
    stack_type: list[int] = []

    if len(df) < 3:
        return []

    # Pivots locales crudos (incluyendo velas que son high y low a la vez),
    # fusionados hasta alternar: cuando dos pivots seguidos son del mismo
    # tipo, se conserva el más extremo y se descarta el otro.
    for pivot_pos, pivot_type in _raw_pivots(df):
        if stack_type and stack_type[-1] == pivot_type:
            prev_pos = stack_pos[-1]
            is_more_extreme = (
                highs[pivot_pos] > highs[prev_pos]
                if pivot_type == 1
                else lows[pivot_pos] < lows[prev_pos]
            )
            if is_more_extreme:
                stack_pos[-1] = pivot_pos
            continue

        stack_pos.append(pivot_pos)
        stack_type.append(pivot_type)

        # Nota: se probó además una confirmación por ruptura recursiva (el
        # nuevo pivot debe romper el swing del mismo tipo anterior a su
        # retroceso, si no se descartan ambos). Colapsaba la estructura a
        # muy pocos puntos en cualquier ventana probada (3-4 en varios
        # meses de 4H) -- no reproduce lo que el usuario marcó a mano. Se
        # descartó; ver docs/rule_decisions.md.

    return [
        (pos, typ, highs[pos] if typ == 1 else lows[pos])
        for pos, typ in zip(stack_pos, stack_type)
    ]


def detect_structural_swings(df: pd.DataFrame) -> pd.DataFrame:
    """Versión por-vela (compatible con `smc.ob`) de `detect_structural_swings_list`.

    Limitación conocida: si una vela produce dos swings (high y low a la
    vez), esta representación solo puede guardar uno por posición -- se
    queda con el último de los dos. Para la lista completa sin pérdida usar
    `detect_structural_swings_list`.
    """
    n = len(df)
    swing_type = np.full(n, np.nan)
    swing_level = np.full(n, np.nan)

    for pos, typ, price in detect_structural_swings_list(df):
        swing_type[pos] = typ
        swing_level[pos] = price

    return pd.DataFrame({"HighLow": swing_type, "Level": swing_level}, index=df.index)
