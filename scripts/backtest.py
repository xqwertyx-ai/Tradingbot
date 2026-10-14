"""Calcula señales, simula y escribe reports/informe.md. Uso: python scripts/backtest.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from tradingbot.backtest import build_features  # noqa: E402
from tradingbot.data import BTC_FILE, MARKETS_FILE, PRICES_FILE  # noqa: E402
from tradingbot.report import write_report  # noqa: E402

if __name__ == "__main__":
    for f in (MARKETS_FILE, PRICES_FILE, BTC_FILE):
        if not os.path.exists(f):
            sys.exit(f"Falta {f}: ejecuta antes scripts/descargar.py")
    df = build_features(pd.read_csv(MARKETS_FILE), pd.read_csv(PRICES_FILE), pd.read_csv(BTC_FILE))
    print(write_report(df))
