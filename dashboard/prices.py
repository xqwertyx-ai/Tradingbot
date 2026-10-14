"""Precios diarios (1 año). Yahoo como principal; Stooq/Coinbase de respaldo.

Cada serie lleva la fuente usada y la fecha de la última sesión, para que la
portada muestre de dónde sale cada dato (política de fuentes del proyecto).
"""
from __future__ import annotations

import io
import time

import pandas as pd

from tradingbot.http import make_session

_s = make_session(retries=2, backoff=0.5)
_s.headers["User-Agent"] = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


def _yahoo(ticker: str) -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    r = _s.get(url, params={"range": "1y", "interval": "1d"}, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({
        "date": pd.to_datetime(res["timestamp"], unit="s", utc=True)
                  .tz_convert(res["meta"].get("exchangeTimezoneName", "UTC")).date,
        "close": q["close"], "high": q["high"], "low": q["low"],
    })
    return df.dropna(subset=["close"]).drop_duplicates("date", keep="last")


def _stooq(sym: str) -> pd.DataFrame:
    r = _s.get("https://stooq.com/q/d/l/", params={"s": sym, "i": "d"}, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df = df.rename(columns=str.lower)[["date", "close", "high", "low"]].tail(260)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def _coinbase(pair: str) -> pd.DataFrame:
    r = _s.get(f"https://api.exchange.coinbase.com/products/{pair}/candles",
               params={"granularity": 86400}, timeout=20)
    r.raise_for_status()
    rows = [{"date": pd.Timestamp(x[0], unit="s").date(), "low": x[1], "high": x[2], "close": x[4]}
            for x in r.json()]
    return pd.DataFrame(rows).sort_values("date")


def fetch(asset: dict) -> tuple[pd.DataFrame | None, str]:
    """Devuelve (serie, fuente). Serie None si ninguna fuente funciona."""
    attempts = [("Yahoo", lambda: _yahoo(asset["yahoo"]))]
    if asset.get("coinbase"):
        attempts.append(("Coinbase", lambda: _coinbase(asset["coinbase"])))
    if asset.get("stooq"):
        attempts.append(("Stooq", lambda: _stooq(asset["stooq"])))
    for name, fn in attempts:
        try:
            df = fn()
            if len(df) >= 30:
                return df.reset_index(drop=True), name
        except Exception as e:
            print(f"  {asset['yahoo']}: {name} falló ({e.__class__.__name__}: {str(e)[:80]})")
        time.sleep(0.3)
    return None, "sin dato"


def check_source(asset: dict, df: pd.DataFrame, source: str) -> str:
    """Contraste con una segunda fuente cuando la hay: 'ok', 'dudoso' o 'sin contraste'."""
    try:
        if source == "Yahoo" and asset.get("coinbase"):
            alt = _coinbase(asset["coinbase"])
        elif source == "Yahoo" and asset.get("stooq"):
            alt = _stooq(asset["stooq"])
        else:
            return "sin contraste"
        m = df.merge(alt, on="date", suffixes=("", "_alt")).tail(1)
        if m.empty:
            return "sin contraste"
        diff = abs(m["close"].iloc[0] / m["close_alt"].iloc[0] - 1)
        return "dudoso" if diff > 0.005 else "ok"
    except Exception:
        return "sin contraste"
