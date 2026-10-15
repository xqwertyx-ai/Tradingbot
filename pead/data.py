"""Datos del experimento PEAD: universo, fechas de resultados y precios.

Todo se guarda en data/pead/raw (caché de GitHub Actions, no se sube al repo salvo
los eventos procesados). Las descargas son incrementales y toleran fallos parciales.
"""
from __future__ import annotations

import io
import json
import os
import time

import pandas as pd
import requests

RAW = "data/pead/raw"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}


def _wiki_table(url: str, col_options: list[str]) -> list[str]:
    html = requests.get(url, headers=UA, timeout=30).text
    for t in pd.read_html(io.StringIO(html)):
        for c in col_options:
            if c in t.columns:
                return [str(x).strip() for x in t[c].dropna()]
    return []


def universe() -> list[str]:
    """S&P 500 + Nasdaq 100 actuales, en formato de Yahoo (BRK.B -> BRK-B)."""
    path = f"{RAW}/universo.json"
    if os.path.exists(path):
        return json.load(open(path))
    tickers: set[str] = set()
    try:
        tickers |= set(_wiki_table("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", ["Symbol"]))
    except Exception as e:
        print(f"  Wikipedia S&P 500 falló: {e}")
    if len(tickers) < 400:
        try:
            csv = requests.get("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
                               headers=UA, timeout=30).text
            tickers |= set(pd.read_csv(io.StringIO(csv))["Symbol"].astype(str))
        except Exception as e:
            print(f"  Lista S&P 500 de respaldo falló: {e}")
    try:
        tickers |= set(_wiki_table("https://en.wikipedia.org/wiki/Nasdaq-100", ["Ticker", "Symbol"]))
    except Exception as e:
        print(f"  Wikipedia Nasdaq-100 falló: {e}")
    out = sorted({t.replace(".", "-") for t in tickers if t and t != "nan"})
    if len(out) < 300:
        raise SystemExit(f"Universo demasiado pequeño ({len(out)}): no se sigue.")
    os.makedirs(RAW, exist_ok=True)
    json.dump(out, open(path, "w"))
    return out


def earnings(tickers: list[str], limit: int = 60, pause: float = 0.6) -> pd.DataFrame:
    """Fechas de resultados con BPA estimado/real. Caché por empresa."""
    import yfinance as yf
    d = f"{RAW}/earnings"
    os.makedirs(d, exist_ok=True)
    frames, fails = [], 0
    for i, t in enumerate(tickers, 1):
        path = f"{d}/{t}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
        else:
            try:
                e = yf.Ticker(t).get_earnings_dates(limit=limit)
            except Exception as ex:
                fails += 1
                print(f"  {t}: {ex.__class__.__name__}: {str(ex)[:80]}")
                time.sleep(pause * 3)
                continue
            if e is None or e.empty:
                fails += 1
                continue
            e = e.reset_index()
            date_col = e.columns[0]
            ts = pd.to_datetime(e[date_col])
            ts = ts.dt.tz_convert("America/New_York") if ts.dt.tz is not None else ts.dt.tz_localize("America/New_York")
            df = pd.DataFrame({
                "ticker": t,
                "fecha": ts.dt.date.astype(str),
                "hora": ts.dt.strftime("%H:%M"),
                "bpa_est": pd.to_numeric(e.get("EPS Estimate"), errors="coerce"),
                "bpa_real": pd.to_numeric(e.get("Reported EPS"), errors="coerce"),
                "sorpresa_pct": pd.to_numeric(e.get("Surprise(%)"), errors="coerce"),
            })
            df.to_csv(path, index=False)
            time.sleep(pause)
        frames.append(df)
        if i % 50 == 0:
            print(f"  resultados: {i}/{len(tickers)} (fallos {fails})")
    print(f"  resultados: {len(frames)} empresas con datos, {fails} sin datos")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def prices(tickers: list[str], start: str = "2010-01-01", force: bool = False,
           path: str = f"{RAW}/precios.csv.gz") -> pd.DataFrame:
    """Cierres ajustados (columnas = tickers, índice = fecha). Incluye SPY."""
    import yfinance as yf
    if not force and os.path.exists(path) and time.time() - os.path.getmtime(path) < 20 * 3600:
        return pd.read_csv(path, index_col=0, parse_dates=True)
    allt = sorted(set(tickers) | {"SPY"})
    chunks = []
    for i in range(0, len(allt), 100):
        part = allt[i:i + 100]
        raw = yf.download(part, start=start, auto_adjust=True, progress=False, threads=True, group_by="column")
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].rename(columns={"Close": part[0]})
        chunks.append(close)
        print(f"  precios: {min(i + 100, len(allt))}/{len(allt)}")
        time.sleep(2)
    px = pd.concat(chunks, axis=1).sort_index()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    px = px.loc[:, px.notna().sum() > 250]
    os.makedirs(RAW, exist_ok=True)
    px.to_csv(path, compression="gzip")
    return px
