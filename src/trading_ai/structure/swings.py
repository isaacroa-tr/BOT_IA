"""Detección de estructura de mercado (swing points / legs / cambio de tendencia).

Especificación acordada con el usuario el 2026-07-04 (reinicio completo de Fase 0,
ver docs/PROJECT_STATE.md y docs/rule_decisions.md para el detalle de la conversación):

1. Se detectan pivots locales crudos (cada vela que es máximo o mínimo respecto a
   sus dos vecinas inmediatas), fusionando pivots consecutivos del mismo tipo y
   quedándose con el más extremo, para que la secuencia alterne siempre high/low.
2. Existe una tendencia vigente (alcista o bajista) y un "origen": el pivot en
   contra de la tendencia que hay que romper para que la tendencia cambie.
3. Cada pivot A FAVOR de la tendencia (ej. un low nuevo estando bajista) cierra la
   pierna actual (origen -> ese pivot) SOLO SI además supera -- con cierre de
   vela M5, no mecha -- el último punto EXTERNO (ya validado) del mismo tipo.
   Si no lo supera, es un pivot interno a la pierna externa vigente y no cuenta
   como pierna propia (se descarta, no cambia ningún estado). Corrección
   2026-07-04: la versión anterior de este punto no pedía superar nada, y eso
   marcaba como pierna pivots que en realidad eran ruido interno (ej. EURUSD
   4H, 3 jul: un high que no llegaba a superar el high externo del 2 jul se
   marcaba como pierna igual).
4. Cada pivot EN CONTRA de la tendencia (el rebote) se revisa contra el último
   punto EXTERNO (ya validado) de SU PROPIO tipo -- no contra el rebote más
   reciente. Si NO lo rompe, ese pivot pasa a ser candidato a nuevo "origen"
   -- pero solo si es MÁS EXTREMO que el candidato actual (más bajo si es un
   low, más alto si es un high); si es menos extremo que el candidato ya
   guardado, se descarta y el candidato viejo se mantiene. Si SÍ rompe el
   último punto externo -- cierre de vela M5, no mecha -- la tendencia
   cambia: el nuevo origen es el último punto a favor de la tendencia vieja
   (el final de la última pierna confirmada), y este mismo pivot cierra la
   primera pierna de la tendencia nueva. El candidato a origen se reinicia
   (vacío) cada vez que se confirma una pierna nueva (continuación o cambio
   de tendencia), para que solo compita contra los rebotes posteriores a esa
   pierna, no contra todo el historial. Corrección 2026-07-04 (segunda
   vuelta): la versión anterior comparaba contra el "origen" (el rebote más
   reciente, sin importar tamaño) -- eso permitía que un simple rebote DENTRO
   del rango de la última pierna grande disparara un "cambio de tendencia"
   completo. Se corrigió comparando contra el último punto EXTERNO. Corrección
   2026-07-04 (tercera vuelta): comparar contra el último punto externo
   arreglaba eso, pero en temporalidades con mucho historial (1D) el punto
   externo puede quedar anclado a un extremo de años atrás que nunca se
   vuelve a tocar, y entonces retrocesos reales (ej. EURUSD 1D, la baja de
   sep-nov 2025 hasta 1.14688) nunca "rompen" nada y quedan sin marcar --
   además, el candidato a origen se quedaba con el ÚLTIMO rebote antes de la
   ruptura en vez del más profundo de todo el tramo (ej. marcaba 1.16701 de
   ene 2026 en vez de 1.14688 de nov 2025, el mínimo real de esa bajada).
   Ahora el candidato a origen rastrea el más extremo desde la última pierna
   confirmada, no el más reciente.
5. Para arrancar (bootstrap) en cualquier temporalidad: se corre el mismo
   algoritmo desde el inicio del historial disponible de esa misma temporalidad.
   El estado se autocorrige en el primer cambio de tendencia real, así que la
   tendencia/origen inicial arbitraria no importa para el resultado en el
   presente. Cada temporalidad se resuelve con su propio historial, sin
   necesitar datos de otras temporalidades (eso es solo para contexto/confianza
   visual del usuario, no para el cálculo).
"""

from __future__ import annotations

import pandas as pd


def _raw_pivots(df: pd.DataFrame) -> list[tuple[int, int]]:
    """Pivots locales crudos: cada vela que es máximo o mínimo respecto a sus
    dos vecinas inmediatas. Una vela puede ser pivot high y low a la vez (vela
    de rango amplio); en ese caso se emiten ambos eventos, ordenados según la
    dirección de la vela (alcista -> low antes que high; bajista -> al revés),
    ya que solo hay OHLC, no datos de tick.

    Corrección 2026-07-12: la comparación es tolerante a empates del lado
    IZQUIERDO (>=/<=) y estricta del lado DERECHO (>/<). Con las dos
    comparaciones estrictas, una meseta (dos velas consecutivas con el mismo
    high, o el mismo low) no generaba pivot en NINGUNA de las dos velas --
    cada una perdía contra la otra por no ser "estrictamente" mayor/menor.
    Eso podía borrar el único pivot que separaba dos rachas de velas del
    mismo tipo mucho más adelante (ver docs/rule_decisions.md, caso real
    EURUSD 1H 2026-07-02 11:00/12:00), haciendo que un low posterior
    genuino se comparara -- y perdiera -- contra un low mucho más viejo y
    profundo, en vez de quedar registrado como su propio swing. Con la
    meseta resuelta a favor de la ÚLTIMA vela (el toque final antes de que
    el precio revierta), ese low posterior ya no compite contra el viejo.
    """
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    opens = df["open"].to_numpy()
    closes = df["close"].to_numpy()
    n = len(df)

    pivots: list[tuple[int, int]] = []
    for i in range(1, n - 1):
        is_high = highs[i] >= highs[i - 1] and highs[i] > highs[i + 1]
        is_low = lows[i] <= lows[i - 1] and lows[i] < lows[i + 1]
        if is_high and is_low:
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


def detect_raw_swings(df: pd.DataFrame) -> list[tuple[int, int, float]]:
    """Devuelve cada pivot crudo como (posición, tipo, precio), alternado.

    tipo: 1 = swing high, -1 = swing low. Pivots consecutivos del mismo tipo se
    fusionan quedándose con el más extremo.
    """
    if len(df) < 3:
        return []

    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()

    stack_pos: list[int] = []
    stack_type: list[int] = []

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

    return [
        (pos, typ, highs[pos] if typ == 1 else lows[pos])
        for pos, typ in zip(stack_pos, stack_type)
    ]


def _m5_body_break_time(m5_df: pd.DataFrame, level: float, direction: int, start_ts, end_ts):
    """Primer timestamp M5 en (start_ts, end_ts] donde el CIERRE cruza `level` en
    `direction`. direction=1 busca cierre por encima (ruptura de un high);
    direction=-1 busca cierre por debajo (ruptura de un low). Mecha sola no
    cuenta como ruptura.
    """
    sub = m5_df.loc[start_ts:end_ts]
    sub = sub[sub.index > start_ts]
    if direction == 1:
        hit = sub.index[sub["close"] > level]
    else:
        hit = sub.index[sub["close"] < level]
    return hit[0] if len(hit) else None


def detect_trend_legs(
    df: pd.DataFrame,
    raw_swings: list[tuple[int, int, float]],
    m5_df: pd.DataFrame,
) -> tuple[list[tuple[int, int, float, int]], int, tuple[int, int, float]]:
    """Piernas confirmadas siguiendo la tendencia vigente + cambios de tendencia.

    Devuelve:
    - `legs`: lista de (pos_origen, pos_fin, precio_fin, tendencia) -- cada
      pierna confirmada, en la dirección de la tendencia vigente al momento de
      cerrarse. `tendencia` es 1 (alcista, pierna low->high) o -1 (bajista,
      pierna high->low).
    - `tendencia_vigente`: 1 o -1, la tendencia actual (después de la última
      pierna/origen procesado).
    - `origen_vigente`: (pos, tipo, precio) del origen actual -- el punto en
      contra de la tendencia que hay que romper (cierre M5) para que cambie.

    Requiere al menos 2 pivots para arrancar: el primero se usa como semilla de
    origen, el segundo determina la tendencia inicial (arbitraria -- se
    autocorrige en el primer cambio de tendencia real, ver docstring del
    módulo).
    """
    if len(raw_swings) < 2:
        return [], 0, (raw_swings[0] if raw_swings else None)

    bar_duration = df.index.to_series().diff().mode().iloc[0]

    origin = raw_swings[0]
    trend = raw_swings[1][1]  # el tipo del segundo pivot define la tendencia inicial
    # ultimo punto EXTERNO (validado) de cada tipo -- lo que hay que superar
    # (cuerpo M5) para que un pivot a favor de la tendencia cuente como pierna.
    last_external = {raw_swings[0][1]: raw_swings[0], raw_swings[1][1]: raw_swings[1]}
    legs: list[tuple[int, int, float, int]] = [(origin[0], raw_swings[1][0], raw_swings[1][2], trend)]
    pending_origin = None  # candidato a origen mas extremo desde la ultima pierna confirmada

    for i in range(2, len(raw_swings)):
        pos, typ, price = raw_swings[i]

        # tanto a favor como en contra de la tendencia, la unica pregunta es:
        # ¿este pivot supera -- con cierre M5 -- el ultimo punto EXTERNO de su
        # propio tipo? Si no, es ruido interno a la pierna externa vigente.
        le_pos, _, le_price = last_external[typ]
        broke = _m5_body_break_time(
            m5_df, le_price, typ, df.index[le_pos], df.index[pos] + bar_duration
        )

        if typ == trend:
            if broke is not None:
                legs.append((origin[0], pos, price, trend))
                last_external[typ] = (pos, typ, price)
                # el origen de esta pierna queda validado tambien del otro lado
                # -- ya no alcanza con romper un rebote viejo/insignificante
                # para el proximo cambio de tendencia, hay que romper ESTE.
                last_external[-typ] = origin
                pending_origin = None  # se reinicia: a competir de nuevo desde cero
            # si no supera, se descarta -- no cambia origen ni ningun estado
        else:
            if broke is not None:
                # cambia la tendencia: el nuevo origen es el fin de la ultima pierna,
                # y este mismo pivot (el que rompio) cierra la primera pierna nueva.
                last_leg_end_pos = legs[-1][1]
                last_leg_end_price = legs[-1][2]
                origin = (last_leg_end_pos, trend, last_leg_end_price)
                trend = typ
                legs.append((origin[0], pos, price, trend))
                last_external[typ] = (pos, typ, price)
                last_external[-typ] = origin
                pending_origin = None
            else:
                # candidato a origen: solo reemplaza si es MAS extremo que el actual
                if pending_origin is None or (
                    price < pending_origin[2] if typ == -1 else price > pending_origin[2]
                ):
                    pending_origin = (pos, typ, price)
                    origin = pending_origin

    return legs, trend, origin
