"""Genera `notebooks/00_rule_spec/output/chart_inspector.html`: chart interactivo
(velas + zigzag de piernas + order blocks + transferencias) para inspeccionar
visualmente el criterio contra datos reales.

Separación deliberada (ver docs/PROJECT_STATE.md, sesión 2026-07-12): el
zigzag de piernas se calcula UNA sola vez a partir de `swings.py` sin tocarlo
ni reinterpretarlo, y todo lo demás (OBs, transferencias) es una capa que se
agrega encima -- para que iterar sobre transferencia nunca cambie cómo se ve
el zigzag de piernas. Si el zigzag alguna vez necesita cambiar, es porque
`swings.py` cambió, no por tocar este script.

Uso: `python notebooks/00_rule_spec/generate_chart_inspector.py`
(requiere los datos ya descargados en `data/raw/mt5/`, no necesita MT5 abierto).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from trading_ai.data import store  # noqa: E402
from trading_ai.structure.swings import detect_raw_swings, detect_trend_legs  # noqa: E402
from trading_ai.zones.order_blocks import detect_order_block  # noqa: E402
from trading_ai.zones.transfer import detect_transferencias  # noqa: E402

OUTPUT_PATH = PROJECT_ROOT / "notebooks" / "00_rule_spec" / "output" / "chart_inspector.html"

SYMBOLS = ["EURUSD"]
TIMEFRAMES = ["1D", "4H", "1H", "M30", "M15", "M5", "M1"]
N_LEGS_DISPLAY = 25  # piernas más recientes a mostrar por símbolo/temporalidad
PAD_BARS_FRACTION = 0.15


def _final_legs(legs):
    """`legs` trae una entrada por cada ruptura confirmada. Mientras la
    tendencia sigue vigente, el origen puede quedarse IGUAL entre entradas
    consecutivas (varios higher-highs seguidos sin retroceso interno que
    compita) -- eso genera cajas de OB idénticas repetidas. Para dibujar OBs
    sin duplicados, solo nos importa la ÚLTIMA entrada de cada racha de mismo
    origen. Ojo: esto NO alcanza para reconstruir el zigzag -- ver
    `_leg_zigzag`, que necesita la lista completa sin colapsar.
    """
    return [leg for i, leg in enumerate(legs) if i == len(legs) - 1 or legs[i + 1][0] != leg[0]]


def _leg_zigzag(df, legs):
    """Zigzag de piernas -- SOLO consume `legs` (salida cruda de
    `detect_trend_legs`, sin colapsar). No le agregues nada de
    OB/transferencia acá: esta función es la que garantiza que el dibujo de
    piernas no cambie sin importar qué se agregue después.

    Ojo: el origen de una pierna NO cambia solo en cambios de tendencia --
    también puede profundizarse en medio de una racha de la misma tendencia
    (un retroceso interno que no rompe estructura, pero es más extremo que
    el candidato a origen anterior, pasa a ser el origen de la siguiente
    pierna confirmada). Eso significa que el origen de la pierna N+1 puede
    ser distinto del fin de la pierna N sin que haya habido reversión --
    ese origen nuevo es en sí mismo un pivot real (del tipo opuesto a la
    tendencia) que hay que dibujar, o el zigzag deja de alternar high/low.
    """
    points = []
    if not legs:
        return points
    o_pos0, _e_pos0, _price0, trend0 = legs[0]
    origin_price = df.iloc[o_pos0]["low" if trend0 == 1 else "high"]
    points.append({"pos": o_pos0, "price": float(origin_price), "type": -trend0})
    for o_pos, e_pos, price, trend in legs:
        last = points[-1]
        # una misma vela de rango amplio puede ser pivot high Y low a la vez
        # (ver `_raw_pivots` en swings.py) -- comparar solo `pos` no alcanza,
        # dos pivots distintos (uno de cada tipo) pueden compartir posición.
        if not (last["pos"] == o_pos and last["type"] == -trend):
            deeper_price = df.iloc[o_pos]["low" if trend == 1 else "high"]
            points.append({"pos": o_pos, "price": float(deeper_price), "type": -trend})
        points.append({"pos": e_pos, "price": float(price), "type": trend})
    return points


def _ob_payload(ob, lo):
    if ob is None:
        return None
    return {
        "x0": max(ob["origin_pos"] - lo, 0),
        "x1": max(ob["boundary_pos"] - lo, 0),
        "top": float(ob["top"]),
        "bottom": float(ob["bottom"]),
        "trend": ob["trend"],
    }


def build_symbol_tf(symbol: str, timeframe: str) -> dict | None:
    start = datetime(2000, 1, 1, tzinfo=timezone.utc)
    end = datetime.now(timezone.utc)
    df = store.get_ohlcv(symbol, timeframe, start, end)
    m5_df = store.get_ohlcv(symbol, "M5", start, end)

    raw_swings = detect_raw_swings(df)
    legs, trend, _origin = detect_trend_legs(df, raw_swings, m5_df)
    if not legs:
        return None
    transferencias = detect_transferencias(df, legs, raw_swings)

    final_legs = _final_legs(legs)
    final_display = final_legs[-N_LEGS_DISPLAY:]
    first_pos, last_pos = final_display[0][0], final_display[-1][1]
    span = max(last_pos - first_pos, 1)
    pad = max(3, int(span * PAD_BARS_FRACTION))
    lo = max(0, first_pos - pad)
    hi = len(df)
    window = df.iloc[lo:hi]

    candles = [
        {
            "t": ts.strftime("%Y-%m-%d %H:%M"),
            "o": float(row["open"]),
            "h": float(row["high"]),
            "l": float(row["low"]),
            "c": float(row["close"]),
        }
        for ts, row in window.iterrows()
    ]

    leg_points = [dict(p, pos=p["pos"] - lo) for p in _leg_zigzag(df, legs) if p["pos"] >= lo]

    obs = []
    for o_pos, e_pos, price, leg_trend in final_legs:
        if e_pos < lo:
            continue
        ob = detect_order_block(df, (o_pos, e_pos, price, leg_trend))
        payload = _ob_payload(ob, lo)
        if payload:
            obs.append(payload)

    transfer_markers = []
    transfer_obs = []
    for t in transferencias:
        if t["touch_pos"] < lo:
            continue
        transfer_markers.append(
            {
                "pos": t["pos"] - lo,
                "price": float(t["price"]),
                "touch_pos": max(t["touch_pos"] - lo, 0),
                "date": df.index[t["pos"]].strftime("%Y-%m-%d %H:%M"),
                "kind": t["kind"],
                "ob": {
                    "bottom": float(t["retro_ob"]["bottom"]),
                    "top": float(t["retro_ob"]["top"]),
                },
            }
        )
        payload = _ob_payload(t["transfer_ob"], lo)
        if payload:
            transfer_obs.append(payload)

    return {
        "candles": candles,
        "legs": leg_points,
        "obs": obs,
        "transfer_obs": transfer_obs,
        "transferencias": transfer_markers,
        "trend": trend,
    }


def build_data() -> dict:
    data: dict = {}
    for symbol in SYMBOLS:
        data[symbol] = {}
        for timeframe in TIMEFRAMES:
            print(f"{symbol}/{timeframe}...", end=" ")
            try:
                result = build_symbol_tf(symbol, timeframe)
            except FileNotFoundError as exc:
                print(f"saltado ({exc})")
                continue
            if result is None:
                print("sin piernas, saltado")
                continue
            data[symbol][timeframe] = result
            print(f"{len(result['legs'])} puntos de zigzag, {len(result['transferencias'])} transferencias")
            for t in result["transferencias"]:
                print(f"    transferencia ({t['kind']}) en {t['date']}, precio {t['price']:.5f}")
    return data


HTML_TEMPLATE = r"""<title>Inspector de velas — swings/OB/transferencia</title>
<style>
  .viz-root {
    --surface-1: #fcfcfb;
    --page: #f9f9f7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --grid: #e1e0d9;
    --baseline: #c3c2b7;
    --border: rgba(11,11,11,0.10);
    --up: #0ca30c;
    --down: #d03b3b;
    --ob-bull: #2a78d6;
    --ob-bear: #eb6834;
    --transfer: #4a3aa7;
    --crosshair: #52514e;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    color: var(--text-primary);
    background: var(--page);
  }
  @media (prefers-color-scheme: dark) {
    .viz-root {
      --surface-1: #1a1a19;
      --page: #0d0d0d;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted: #898781;
      --grid: #2c2c2a;
      --baseline: #383835;
      --border: rgba(255,255,255,0.10);
      --up: #0ca30c;
      --down: #e66767;
      --ob-bull: #3987e5;
      --ob-bear: #d95926;
      --transfer: #9085e9;
      --crosshair: #c3c2b7;
    }
  }
  :root[data-theme="dark"] .viz-root {
    --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff;
    --text-secondary: #c3c2b7; --text-muted: #898781; --grid: #2c2c2a;
    --baseline: #383835; --border: rgba(255,255,255,0.10); --up: #0ca30c;
    --down: #e66767; --ob-bull: #3987e5; --ob-bear: #d95926; --transfer: #9085e9;
    --crosshair: #c3c2b7;
  }
  :root[data-theme="light"] .viz-root {
    --surface-1: #fcfcfb; --page: #f9f9f7; --text-primary: #0b0b0b;
    --text-secondary: #52514e; --text-muted: #898781; --grid: #e1e0d9;
    --baseline: #c3c2b7; --border: rgba(11,11,11,0.10); --up: #0ca30c;
    --down: #d03b3b; --ob-bull: #2a78d6; --ob-bear: #eb6834; --transfer: #4a3aa7;
    --crosshair: #52514e;
  }

  * { box-sizing: border-box; }
  body { margin: 0; }
  .viz-root { min-height: 100vh; padding: 20px; }
  .toolbar {
    display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
    margin-bottom: 14px;
  }
  .toolbar label { font-size: 13px; color: var(--text-secondary); margin-right: 6px; }
  .toolbar select {
    font-size: 14px; padding: 6px 10px; border-radius: 6px;
    border: 1px solid var(--border); background: var(--surface-1);
    color: var(--text-primary);
  }
  .legend {
    display: flex; gap: 18px; flex-wrap: wrap; font-size: 12.5px;
    color: var(--text-secondary); margin-bottom: 10px;
  }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
  .chart-wrap {
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 10px; padding: 12px; overflow-x: auto;
  }
  canvas { display: block; cursor: crosshair; }
  #tooltip {
    position: fixed; pointer-events: none; background: var(--surface-1);
    border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px;
    font-size: 13px; line-height: 1.5; color: var(--text-primary);
    box-shadow: 0 4px 14px rgba(0,0,0,0.18); display: none; z-index: 10;
    font-variant-numeric: tabular-nums;
  }
  #tooltip .t-date { color: var(--text-secondary); font-size: 11.5px; margin-bottom: 3px; }
  #tooltip .t-row { display: flex; justify-content: space-between; gap: 14px; }
  #tooltip .t-label { color: var(--text-muted); }
  #tooltip .t-transfer { margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border); color: var(--transfer); font-weight: 600; }
  #empty-msg { color: var(--text-muted); font-size: 13px; padding: 40px; text-align: center; }
</style>

<div class="viz-root">
  <div class="toolbar">
    <div><label for="symbol-sel">Símbolo</label><select id="symbol-sel"></select></div>
    <div><label for="tf-sel">Temporalidad</label><select id="tf-sel"></select></div>
    <div id="trend-label" style="font-size:13px;color:var(--text-secondary)"></div>
  </div>
  <div class="legend">
    <span><span class="swatch" style="background:var(--up)"></span>vela alcista</span>
    <span><span class="swatch" style="background:var(--down)"></span>vela bajista</span>
    <span><span class="swatch" style="background:var(--text-primary)"></span>zigzag piernas</span>
    <span><span class="swatch" style="background:var(--ob-bull)"></span>OB alcista (soporte)</span>
    <span><span class="swatch" style="background:var(--ob-bear)"></span>OB bajista (resistencia)</span>
    <span><span class="swatch" style="background:var(--transfer)"></span>transferencia + su OB (BOS/CHoCH)</span>
  </div>
  <div class="chart-wrap">
    <canvas id="chart"></canvas>
    <div id="empty-msg" style="display:none">Sin datos para esta combinación.</div>
  </div>
</div>

<div id="tooltip"></div>

<script>
const DATA = __DATA__;

const symbolSel = document.getElementById('symbol-sel');
const tfSel = document.getElementById('tf-sel');
const trendLabel = document.getElementById('trend-label');
const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');
const emptyMsg = document.getElementById('empty-msg');

const TF_ORDER = ["1D", "4H", "1H", "M30", "M15", "M5", "M1"];
const symbols = Object.keys(DATA);
symbols.forEach(s => {
  const opt = document.createElement('option');
  opt.value = s; opt.textContent = s;
  symbolSel.appendChild(opt);
});
TF_ORDER.forEach(tf => {
  const opt = document.createElement('option');
  opt.value = tf; opt.textContent = tf;
  tfSel.appendChild(opt);
});
tfSel.value = "1H";

const CANDLE_W = 9;
const CANDLE_GAP = 3;
const PAD_L = 70, PAD_R = 20, PAD_T = 16, PAD_B = 30;
const CHART_H = 620;

function getStyle(varName) {
  return getComputedStyle(document.querySelector('.viz-root')).getPropertyValue(varName).trim();
}

let currentData = null;
let layout = null;

function render() {
  const symbol = symbolSel.value;
  const tf = tfSel.value;
  const d = (DATA[symbol] || {})[tf];
  if (!d || !d.candles || d.candles.length === 0) {
    emptyMsg.style.display = 'block';
    canvas.style.display = 'none';
    trendLabel.textContent = '';
    return;
  }
  emptyMsg.style.display = 'none';
  canvas.style.display = 'block';
  currentData = d;
  trendLabel.textContent = `Tendencia vigente: ${d.trend === 1 ? 'alcista' : 'bajista'} · ${d.candles.length} velas`;

  const n = d.candles.length;
  const width = PAD_L + PAD_R + n * (CANDLE_W + CANDLE_GAP);
  const height = CHART_H;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  let priceMin = Infinity, priceMax = -Infinity;
  d.candles.forEach(c => { priceMin = Math.min(priceMin, c.l); priceMax = Math.max(priceMax, c.h); });
  d.obs.forEach(ob => { priceMin = Math.min(priceMin, ob.bottom); priceMax = Math.max(priceMax, ob.top); });
  const pricePad = (priceMax - priceMin) * 0.06;
  priceMin -= pricePad; priceMax += pricePad;

  const plotH = height - PAD_T - PAD_B;
  const xForIndex = (i) => PAD_L + i * (CANDLE_W + CANDLE_GAP) + CANDLE_W / 2;
  const yForPrice = (p) => PAD_T + plotH - ((p - priceMin) / (priceMax - priceMin)) * plotH;

  layout = { xForIndex, yForPrice, n, priceMin, priceMax, width, height };

  const surface = getStyle('--surface-1');
  const grid = getStyle('--grid');
  const muted = getStyle('--text-muted');
  const primary = getStyle('--text-primary');
  const up = getStyle('--up');
  const down = getStyle('--down');
  const obBull = getStyle('--ob-bull');
  const obBear = getStyle('--ob-bear');
  const transfer = getStyle('--transfer');

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = surface;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = grid;
  ctx.fillStyle = muted;
  ctx.font = '11px system-ui, sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  const GRID_STEPS = 8;
  for (let i = 0; i <= GRID_STEPS; i++) {
    const p = priceMin + (priceMax - priceMin) * (i / GRID_STEPS);
    const y = yForPrice(p);
    ctx.beginPath();
    ctx.moveTo(PAD_L, y);
    ctx.lineTo(width - PAD_R, y);
    ctx.stroke();
    ctx.fillText(p.toFixed(5), PAD_L - 8, y);
  }

  const labelEvery = Math.max(1, Math.ceil(n / 14));
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  d.candles.forEach((c, i) => {
    if (i % labelEvery === 0) {
      ctx.fillText(c.t.slice(0, 10), xForIndex(i), height - PAD_B + 8);
    }
  });

  d.obs.forEach(ob => {
    const x0 = xForIndex(ob.x0) - CANDLE_W / 2 - CANDLE_GAP / 2;
    const x1 = xForIndex(ob.x1) + CANDLE_W / 2 + CANDLE_GAP / 2;
    const yTop = yForPrice(ob.top);
    const yBot = yForPrice(ob.bottom);
    ctx.fillStyle = (ob.trend === -1 ? obBear : obBull) + '33';
    ctx.strokeStyle = ob.trend === -1 ? obBear : obBull;
    ctx.lineWidth = 1;
    ctx.fillRect(x0, yTop, x1 - x0, yBot - yTop);
    ctx.strokeRect(x0, yTop, x1 - x0, yBot - yTop);
  });

  (d.transfer_obs || []).forEach(ob => {
    const x0 = xForIndex(ob.x0) - CANDLE_W / 2 - CANDLE_GAP / 2;
    const x1 = xForIndex(ob.x1) + CANDLE_W / 2 + CANDLE_GAP / 2;
    const yTop = yForPrice(ob.top);
    const yBot = yForPrice(ob.bottom);
    ctx.fillStyle = transfer + '33';
    ctx.strokeStyle = transfer;
    ctx.lineWidth = 1.4;
    ctx.fillRect(x0, yTop, x1 - x0, yBot - yTop);
    ctx.strokeRect(x0, yTop, x1 - x0, yBot - yTop);
  });

  d.candles.forEach((c, i) => {
    const x = xForIndex(i);
    const isUp = c.c >= c.o;
    ctx.strokeStyle = isUp ? up : down;
    ctx.fillStyle = isUp ? up : down;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, yForPrice(c.h));
    ctx.lineTo(x, yForPrice(c.l));
    ctx.stroke();
    const yO = yForPrice(c.o), yC = yForPrice(c.c);
    const bodyTop = Math.min(yO, yC);
    const bodyH = Math.max(Math.abs(yC - yO), 1);
    ctx.fillRect(x - CANDLE_W / 2, bodyTop, CANDLE_W, bodyH);
  });

  if (d.legs.length > 1) {
    ctx.strokeStyle = primary;
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    d.legs.forEach((pt, i) => {
      const x = xForIndex(pt.pos), y = yForPrice(pt.price);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    d.legs.forEach(pt => {
      const x = xForIndex(pt.pos), y = yForPrice(pt.price);
      ctx.fillStyle = pt.type === 1 ? down : up;
      ctx.beginPath();
      if (pt.type === 1) {
        ctx.moveTo(x, y - 8); ctx.lineTo(x - 6, y + 4); ctx.lineTo(x + 6, y + 4);
      } else {
        ctx.moveTo(x, y + 8); ctx.lineTo(x - 6, y - 4); ctx.lineTo(x + 6, y - 4);
      }
      ctx.closePath();
      ctx.fill();
    });
  }

  d.transferencias.forEach(t => {
    const x = xForIndex(t.pos), y = yForPrice(t.price);
    ctx.fillStyle = transfer;
    drawStar(x, y, 5, 9, 4);
    ctx.strokeStyle = transfer;
    ctx.setLineDash([3, 3]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    const touchC = currentData.candles[t.touch_pos];
    ctx.moveTo(xForIndex(t.touch_pos), yForPrice(touchC ? touchC.h : t.price));
    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.setLineDash([]);
  });
}

function drawStar(cx, cy, spikes, outerR, innerR) {
  let rot = Math.PI / 2 * 3;
  const step = Math.PI / spikes;
  ctx.beginPath();
  ctx.moveTo(cx, cy - outerR);
  for (let i = 0; i < spikes; i++) {
    let x = cx + Math.cos(rot) * outerR;
    let y = cy + Math.sin(rot) * outerR;
    ctx.lineTo(x, y);
    rot += step;
    x = cx + Math.cos(rot) * innerR;
    y = cy + Math.sin(rot) * innerR;
    ctx.lineTo(x, y);
    rot += step;
  }
  ctx.lineTo(cx, cy - outerR);
  ctx.closePath();
  ctx.fill();
}

canvas.addEventListener('mousemove', (e) => {
  if (!layout || !currentData) return;
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const idx = Math.round((mx - PAD_L - CANDLE_W / 2) / (CANDLE_W + CANDLE_GAP));
  if (idx < 0 || idx >= currentData.candles.length) {
    tooltip.style.display = 'none';
    return;
  }
  const c = currentData.candles[idx];
  let html = `
    <div class="t-date">${c.t}</div>
    <div class="t-row"><span class="t-label">Open</span><span>${c.o.toFixed(5)}</span></div>
    <div class="t-row"><span class="t-label">High</span><span>${c.h.toFixed(5)}</span></div>
    <div class="t-row"><span class="t-label">Low</span><span>${c.l.toFixed(5)}</span></div>
    <div class="t-row"><span class="t-label">Close</span><span>${c.c.toFixed(5)}</span></div>
  `;
  // si el mouse esta cerca de una estrella de transferencia, agregar detalle
  const near = currentData.transferencias.find(t => {
    const x = layout.xForIndex(t.pos), y = layout.yForPrice(t.price);
    return Math.abs(x - mx) < 10 && Math.abs(y - my) < 10;
  });
  if (near) {
    html += `<div class="t-transfer">Transferencia (${near.kind}) — precio ${near.price.toFixed(5)}<br>OB tocado (vela 1): [${near.ob.bottom.toFixed(5)}, ${near.ob.top.toFixed(5)}]</div>`;
  }
  tooltip.innerHTML = html;
  tooltip.style.display = 'block';
  tooltip.style.left = (e.clientX + 16) + 'px';
  tooltip.style.top = (e.clientY + 16) + 'px';
});
canvas.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });

symbolSel.addEventListener('change', render);
tfSel.addEventListener('change', render);
render();
</script>
"""


def main() -> None:
    data = build_data()
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Escrito {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
