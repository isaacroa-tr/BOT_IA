"""CLI: descarga 2-3 años de histórico MT5 para todos los símbolos/timeframes configurados.

Requiere que el terminal MT5 esté abierto y logueado en Windows.

Uso:
    .venv\\Scripts\\python.exe scripts\\run_ingest.py --years 3
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from trading_ai.data.ingest import ingest_all


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=3, help="Años de histórico a descargar")
    args = parser.parse_args()

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365 * args.years)
    ingest_all(start, end)


if __name__ == "__main__":
    main()
