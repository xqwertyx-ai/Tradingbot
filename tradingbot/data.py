"""Descarga incremental de datos públicos (no requiere claves).

- Mercados BTC 5 min de Polymarket (Gamma API) y su resultado.
- Histórico de precio de la acción "Up" (CLOB prices-history, ~1 punto/min).
- Velas de 1 min de BTC-USD (Coinbase Exchange), solo para calcular señales.
  El resultado de cada mercado se toma de Polymarket, no de Coinbase.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from . import config as C
from .http import make_session

MARKETS_FILE = os.path.join(C.DATA_DIR, "markets.csv.gz")
PRICES_FILE = os.path.join(C.DATA_DIR, "prices.csv.gz")
BTC_FILE = os.path.join(C.DATA_DIR, "btc_1m.csv.gz")

_session = make_session()


def _load(path: str, cols: list[str]) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=cols)


def _save(df: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")


# ---------- Polymarket ----------

def parse_event(ev: dict, start_ts: int) -> dict | None:
    """Convierte un evento de Gamma en una fila. None si no está resuelto."""
    if not ev.get("markets"):
        return None
    m = ev["markets"][0]
    outcomes = json.loads(m.get("outcomes") or "[]")
    prices = json.loads(m.get("outcomePrices") or "[]")
    tokens = json.loads(m.get("clobTokenIds") or "[]")
    if outcomes != ["Up", "Down"] or len(prices) != 2 or len(tokens) != 2:
        return None
    try:
        p_up = float(prices[0])
    except ValueError:
        return None
    if not m.get("closed") or p_up not in (0.0, 1.0):
        return None  # sin resolver o resolución anómala
    return {
        "start_ts": start_ts,
        "slug": ev.get("slug"),
        "up_won": int(p_up == 1.0),
        "up_token": tokens[0],
    }


def fetch_market(start_ts: int) -> dict | None:
    slug = f"btc-updown-5m-{start_ts}"
    r = _session.get(C.GAMMA_URL, params={"slug": slug}, timeout=20)
    r.raise_for_status()
    events = r.json()
    if not events:
        return None
    return parse_event(events[0], start_ts)


def fetch_price_history(token: str, start_ts: int) -> list[dict]:
    params = {
        "market": token,
        "startTs": start_ts - C.WINDOW_SECONDS,
        "endTs": start_ts + C.WINDOW_SECONDS,
        "fidelity": 1,
    }
    r = _session.get(C.CLOB_HISTORY_URL, params=params, timeout=20)
    r.raise_for_status()
    return [
        {"start_ts": start_ts, "t": int(pt["t"]), "p_up": float(pt["p"])}
        for pt in r.json().get("history", [])
    ]


def _one_window(start_ts: int):
    try:
        mk = fetch_market(start_ts)
        if mk is None:
            return None, []
        return mk, fetch_price_history(mk["up_token"], start_ts)
    except Exception as e:  # se registra y se reintenta en la próxima ejecución
        print(f"  error en {start_ts}: {e}")
        return None, []


def update_polymarket(days: int, workers: int = 8) -> None:
    markets = _load(MARKETS_FILE, ["start_ts", "slug", "up_won", "up_token"])
    prices = _load(PRICES_FILE, ["start_ts", "t", "p_up"])
    done = set(markets["start_ts"].astype(int))

    now = int(time.time())
    last_closed = (now // C.WINDOW_SECONDS) * C.WINDOW_SECONDS - 2 * C.WINDOW_SECONDS
    first = last_closed - days * 86400
    todo = [t for t in range(first, last_closed + 1, C.WINDOW_SECONDS) if t not in done]
    print(f"Polymarket: {len(todo)} ventanas por descargar ({len(done)} ya guardadas)")

    new_m, new_p = [], []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (mk, hist) in enumerate(ex.map(_one_window, todo), 1):
            if mk:
                new_m.append(mk)
                new_p.extend(hist)
            if i % 500 == 0:
                print(f"  {i}/{len(todo)}")

    if new_m:
        markets = pd.concat([markets, pd.DataFrame(new_m)], ignore_index=True)
        markets = markets.drop_duplicates("start_ts").sort_values("start_ts")
        _save(markets, MARKETS_FILE)
    if new_p:
        prices = pd.concat([prices, pd.DataFrame(new_p)], ignore_index=True)
        prices = prices.drop_duplicates(["start_ts", "t"]).sort_values(["start_ts", "t"])
        _save(prices, PRICES_FILE)
    print(f"Polymarket: +{len(new_m)} mercados, +{len(new_p)} puntos de precio")


# ---------- Coinbase ----------

def fetch_candles(start: int, end: int) -> list[dict]:
    """Coinbase devuelve [time, low, high, open, close, volume], máx. 300 velas."""
    params = {
        "granularity": 60,
        "start": pd.Timestamp(start, unit="s", tz="UTC").isoformat(),
        "end": pd.Timestamp(end, unit="s", tz="UTC").isoformat(),
    }
    r = _session.get(C.COINBASE_CANDLES_URL, params=params, timeout=20)
    r.raise_for_status()
    return [
        {"t": int(row[0]), "open": row[3], "high": row[2], "low": row[1], "close": row[4]}
        for row in r.json()
    ]


def update_btc(days: int) -> None:
    btc = _load(BTC_FILE, ["t", "open", "high", "low", "close"])
    now = (int(time.time()) // 60) * 60
    start = now - days * 86400 - 600
    ranges = [(start, now)]
    if len(btc):
        lo, hi = int(btc["t"].min()), int(btc["t"].max())
        ranges = [(start, lo)] if start < lo else []
        ranges.append((hi + 60, now))
    rows = []
    step = 300 * 60
    for a, b in ranges:
        for s in range(a, b, step):
            e = min(s + step - 60, b - 60)
            if e < s:
                continue
            rows.extend(fetch_candles(s, e))
            time.sleep(0.15)  # límite público de Coinbase
    if rows:
        btc = pd.concat([btc, pd.DataFrame(rows)], ignore_index=True)
        btc = btc.drop_duplicates("t").sort_values("t")
        _save(btc, BTC_FILE)
    print(f"BTC: +{len(rows)} velas (total {len(btc)})")
