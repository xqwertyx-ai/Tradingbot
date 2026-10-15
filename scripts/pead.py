"""Experimento 2 (PEAD). Uso: python scripts/pead.py [--max-empresas N]

Descarga (con caché) universo, fechas de resultados y precios; construye eventos y
escribe reports/pead.md y data/pead/eventos.csv.gz. Reglas: docs/pead-preregistro.md.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pead import data, engine, report  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-empresas", type=int, default=0, help="0 = todas (para pruebas rápidas)")
    a = ap.parse_args()
    print("Universo...")
    tickers = data.universe()
    if a.max_empresas:
        tickers = tickers[:a.max_empresas]
    print(f"  {len(tickers)} empresas")
    print("Fechas de resultados...")
    earn = data.earnings(tickers)
    if earn.empty:
        sys.exit("No se obtuvo ninguna fecha de resultados.")
    print("Precios...")
    px = data.prices(tickers)
    print(f"  {px.shape[1]} series, {px.index.min():%Y-%m-%d} → {px.index.max():%Y-%m-%d}")
    print("Eventos y señales...")
    ev = engine.build_events(earn, px)
    print(f"  {len(ev)} eventos")
    os.makedirs("data/pead", exist_ok=True)
    ev.to_csv("data/pead/eventos.csv.gz", index=False, compression="gzip")
    res = engine.evaluate(ev)
    res.to_csv("data/pead/resultados.csv", index=False)
    print(report.write(ev, res))
