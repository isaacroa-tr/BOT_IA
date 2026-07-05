"""Transferencia: concepto propio del usuario (2026-07-04, ver docs/rule_decisions.md),
sin equivalente estándar en librerías SMC.

Secuencia confirmada: antes de que una pierna L termine de formarse, hay un
retroceso previo (el tramo entre el fin de la pierna anterior y el origen de L).
Ese retroceso tiene su propio order block (OB-B, ver `order_blocks.py`).
Mientras L se está formando:
1. El precio TOCA la zona de OB-B (un pivot a favor de la tendencia de L cae
   dentro del rango de OB-B).
2. El precio RETROCEDE desde ahí, dejando un pivot interno nuevo (en contra de
   la tendencia de L) -- ese pivot es la "transferencia".
3. El precio vuelve a moverse a favor de L y rompe todo, incluido OB-B,
   validando el fin de la pierna L.

La relevancia de OB-B pasa a este punto de transferencia una vez que OB-B queda
roto. Pueden encadenarse (transferencia sobre una transferencia anterior), pero
eso no se resuelve acá -- ver nota de "contexto" en rule_decisions.md.

Corrección 2026-07-04 (segunda vuelta): esto aplica tanto si la pierna anterior
es un CHoCH (pierna previa de tendencia OPUESTA -- el retroceso completo, ya
es OB-B directamente) como si es un BOS (pierna previa de la MISMA tendencia --
en ese caso el "retroceso" no quedó guardado como pierna propia porque nunca
validó por sí solo; se reconstruye como una pierna pseudo-opuesta desde el fin
de la pierna anterior hasta el origen de L, y se le calcula su propio OB igual
que a cualquier otra pierna).
"""

from __future__ import annotations

import pandas as pd

from trading_ai.zones.order_blocks import detect_order_block


def detect_transferencias(
    df: pd.DataFrame,
    legs: list[tuple[int, int, float, int]],
    raw_swings: list[tuple[int, int, float]],
) -> list[dict]:
    """Devuelve una transferencia por cada pierna donde se cumple la secuencia
    completa (toca OB-B, retrocede, y la pierna ya validada implica la ruptura).

    Cada resultado: leg_index (índice en `legs`), touch_pos (pivot que tocó
    OB-B), pos/price (el pivot de retroceso = la transferencia), trend (tipo
    del pivot de transferencia, opuesto a la tendencia de la pierna L), ob
    (el order block del retroceso previo, OB-B), kind ("BOS" o "CHoCH" según
    si la pierna anterior era de la misma tendencia o de la opuesta).
    """
    result = []
    for i in range(1, len(legs)):
        leg = legs[i]
        prev_leg = legs[i - 1]
        o_pos, e_pos, _price, trend = leg

        if prev_leg[1] != o_pos:
            continue  # el origen de L no es el fin de la pierna anterior

        if prev_leg[3] == trend:
            # BOS: el retroceso previo nunca validó como pierna propia -- se
            # reconstruye como pseudo-pierna opuesta (fin de la anterior ->
            # origen de L) para poder calcularle su propio OB.
            origin_price = df.loc[df.index[o_pos], "low" if trend == 1 else "high"]
            retro_leg = (prev_leg[1], o_pos, origin_price, -trend)
            kind = "BOS"
        else:
            # CHoCH: la pierna anterior ES el retroceso completo (tendencia opuesta).
            retro_leg = prev_leg
            kind = "CHoCH"

        ob = detect_order_block(df, retro_leg)
        if ob is None:
            continue

        inner = [(pos, typ, p) for pos, typ, p in raw_swings if o_pos < pos < e_pos]
        for j in range(len(inner) - 1):
            pos, typ, p = inner[j]
            if typ == trend and ob["bottom"] <= p <= ob["top"]:
                t_pos, t_typ, t_price = inner[j + 1]
                if t_typ != trend:
                    result.append(
                        {
                            "leg_index": i,
                            "touch_pos": pos,
                            "pos": t_pos,
                            "price": t_price,
                            "trend": -trend,
                            "ob": ob,
                            "kind": kind,
                        }
                    )
                break

    return result
