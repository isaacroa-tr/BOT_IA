"""Transferencia: concepto propio del usuario (ver docs/rule_decisions.md),
sin equivalente estándar en librerías SMC.

Definición exacta (reprecisada 2026-07-12, ver docs/rule_decisions.md para el
detalle completo de la conversación -- esta versión reemplaza la del
2026-07-04, que usaba toda la zona del OB como nivel de toque):

Antes de que una pierna L termine de formarse, hay un retroceso previo
(`retro_leg`): si la pierna anterior es un CHoCH (tendencia OPUESTA a L),
`retro_leg` es esa misma pierna anterior; si es un BOS (MISMA tendencia que
L), el retroceso nunca validó como pierna propia, así que se reconstruye como
pseudo-pierna opuesta desde el fin de la pierna anterior hasta el origen de L.

Corrección 2026-07-12: en el caso BOS, el origen de L casi nunca coincide con
el fin exacto de la pierna anterior en `legs` -- `swings.py` puede profundizar
el origen varias velas (a veces cientos) después de esa pierna, sin que eso
quede registrado como una pierna propia (ver docstring de
`detect_structural_swings`/`detect_trend_legs`). La versión anterior de este
archivo exigía que coincidieran exactamente, lo que descartaba ~6 de cada 10
piernas (todas las BOS con retroceso profundizado) y dejaba el conteo de
transferencias BOS en cero en toda la historia de todas las temporalidades.
Ahora la pseudo-pierna se reconstruye igual sin importar el tamaño del hueco;
solo se descarta el caso degenerado (sin ninguna vela de margen, cuando la
profundización cae exactamente en el cierre de la pierna anterior).

A `retro_leg` se le calcula su Order Block (`detect_order_block`, sin
cambios). La vela límite de ese OB -- "vela 1" -- es el borde del primer FVG
de `retro_leg` contando desde su propio origen. Mientras L se forma:

1. El precio TOCA vela 1: un pivot genuino (extremo local real, no cualquier
   mecha de paso) a favor de la tendencia de L cae dentro del rango PROPIO de
   vela 1 (entre su low y su high) -- no en toda la zona del OB de
   `retro_leg`. Cualquier mecha que se pase de ese rango invalida el toque
   (más estricto que la regla de cierre M5 usada en el resto del criterio).
2. El precio RETROCEDE desde ahí, dejando un pivot interno nuevo (en contra de
   la tendencia de L) -- ese pivot es la "transferencia".
3. El precio vuelve a moverse a favor de L y rompe estructura de verdad,
   validando el fin de la pierna L (ya cubierto por `swings.py`, sin cambios
   acá).

A la transferencia se le calcula su propio OB con la misma
`detect_order_block()`, tratando el tramo toque→transferencia como una pierna
nueva (tendencia opuesta a L, mismo signo que `retro_leg`).

La relevancia de OB-B (el OB de `retro_leg`) pasa a este punto de
transferencia una vez que OB-B queda roto. Pueden encadenarse (transferencia
sobre una transferencia anterior), pero eso no se resuelve acá -- ver nota de
"contexto" en rule_decisions.md.
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
    completa (toca vela 1 del OB de `retro_leg`, retrocede sin superarla).

    Cada resultado: leg_index (índice en `legs`), touch_pos (pivot que tocó
    vela 1), pos/price (el pivot de retroceso = la transferencia), trend (tipo
    del pivot de transferencia, opuesto a la tendencia de la pierna L),
    retro_ob (el OB de `retro_leg`, "OB-B"), transfer_ob (el OB propio de la
    transferencia, tramo toque->transferencia -- puede ser None si ese tramo
    no tiene ningún FVG), kind ("BOS" o "CHoCH" según si la pierna anterior
    era de la misma tendencia o de la opuesta).
    """
    result = []
    for i in range(1, len(legs)):
        leg = legs[i]
        prev_leg = legs[i - 1]
        o_pos, e_pos, _price, trend = leg

        if prev_leg[3] == trend:
            # BOS: pierna anterior de la MISMA tendencia -- el origen de L no
            # tiene por qué coincidir con el fin exacto de esa pierna anterior:
            # el retroceso real suele profundizarse varias velas después (el
            # candidato a origen se corrige hacia un pivot más extremo sin que
            # eso quede registrado como pierna propia -- ver swings.py). El
            # retroceso previo nunca validó como pierna propia -- se
            # reconstruye como pseudo-pierna opuesta desde el fin de la
            # pierna anterior hasta el origen real de L.
            if prev_leg[1] >= o_pos:
                continue  # sin margen para un retroceso propio (misma vela límite)
            origin_price = df.loc[df.index[o_pos], "low" if trend == 1 else "high"]
            retro_leg = (prev_leg[1], o_pos, origin_price, -trend)
            kind = "BOS"
        else:
            # CHoCH: la pierna anterior ES el retroceso completo (tendencia
            # opuesta). Por construcción de swings.py, un cambio de tendencia
            # real siempre deja prev_leg[1] == o_pos exactamente.
            if prev_leg[1] != o_pos:
                continue
            retro_leg = prev_leg
            kind = "CHoCH"

        retro_ob = detect_order_block(df, retro_leg)
        if retro_ob is None:
            continue

        # "vela 1": la vela límite del OB de retro_leg. El toque se compara
        # contra el rango PROPIO de esa vela (su low/high), no contra toda la
        # zona del OB -- ninguna mecha puede pasarse de ese rango.
        candle1 = df.iloc[retro_ob["boundary_pos"]]
        candle1_low, candle1_high = candle1["low"], candle1["high"]

        inner = [(pos, typ, p) for pos, typ, p in raw_swings if o_pos < pos < e_pos]
        for j in range(len(inner) - 1):
            pos, typ, p = inner[j]
            if typ == trend and candle1_low <= p <= candle1_high:
                t_pos, t_typ, t_price = inner[j + 1]
                if t_typ != trend:
                    transfer_leg = (pos, t_pos, t_price, -trend)
                    transfer_ob = detect_order_block(df, transfer_leg)
                    result.append(
                        {
                            "leg_index": i,
                            "touch_pos": pos,
                            "pos": t_pos,
                            "price": t_price,
                            "trend": -trend,
                            "retro_ob": retro_ob,
                            "transfer_ob": transfer_ob,
                            "kind": kind,
                        }
                    )
                break

    return result
