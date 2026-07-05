"""Order blocks (OB), a partir de la definición del usuario (2026-07-04, ver
docs/rule_decisions.md): dentro de una pierna (ver `trading_ai.structure.swings`),
escaneando desde el FINAL de la pierna hacia el ORIGEN, el OB es la zona desde el
origen hasta la mecha de la primera vela (yendo hacia atrás) que ya no forma parte
de la cadena de FVG del impulso -- en la práctica, el borde izquierdo del PRIMER
FVG (el más cercano al origen) dentro de esa pierna.
"""

from __future__ import annotations

import pandas as pd


def _first_fvg_mid(df: pd.DataFrame, lo: int, hi: int, direction: int) -> int | None:
    """Posición de la vela del medio del primer FVG clásico de 3 velas dentro de
    df[lo:hi] (inclusive), en la dirección de la pierna. direction=1 (alcista):
    hueco si low[i+1] > high[i-1]. direction=-1 (bajista): hueco si
    high[i+1] < low[i-1]. Devuelve la posición i más chica (más cercana al origen).
    """
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    for i in range(lo + 1, hi):
        if i + 1 > hi:
            break
        if direction == 1:
            if lows[i + 1] > highs[i - 1]:
                return i
        else:
            if highs[i + 1] < lows[i - 1]:
                return i
    return None


def detect_order_block(df: pd.DataFrame, leg: tuple[int, int, float, int]) -> dict | None:
    """OB de una pierna (origen, fin, precio_fin, tendencia). None si la pierna
    no tiene ningún FVG (no se puede marcar OB sin imbalance).

    Devuelve dict: origin_pos, boundary_pos (la vela límite, borde izquierdo del
    primer FVG), top, bottom (rango de precio de la zona), trend (tipo de la
    pierna que lo originó -- un OB de pierna bajista es una zona de resistencia,
    de pierna alcista es zona de soporte).

    El rango de precio de la zona usa el extremo PROPIO del origen y de la vela
    límite -- no el máximo/mínimo de todas las velas intermedias. Corrección
    2026-07-04: la versión anterior usaba `.max()`/`.min()` sobre todo el tramo
    origen->límite, y una vela intermedia sin relación con el FVG (con una mecha
    más profunda que la propia vela límite) contaminaba el borde de la zona.
    """
    o_pos, e_pos, _price, trend = leg
    fvg_mid = _first_fvg_mid(df, o_pos, e_pos, trend)
    if fvg_mid is None:
        return None
    boundary_pos = fvg_mid - 1
    origin_price = df.loc[df.index[o_pos], "low" if trend == 1 else "high"]
    boundary_row = df.iloc[boundary_pos]
    if trend == 1:
        top, bottom = boundary_row["high"], origin_price
    else:
        top, bottom = origin_price, boundary_row["low"]
    return {
        "origin_pos": o_pos,
        "boundary_pos": boundary_pos,
        "top": top,
        "bottom": bottom,
        "trend": trend,
    }
