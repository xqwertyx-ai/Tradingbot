"""Descarga incremental de datos. Uso: python scripts/descargar.py --dias 14"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingbot.data import update_btc, update_polymarket  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=14)
    a = ap.parse_args()
    update_btc(a.dias + 1)
    update_polymarket(a.dias)
