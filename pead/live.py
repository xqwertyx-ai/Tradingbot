"""Test en vivo de la única regla PEAD que pasó el pre-registro, sin tocarla.

Regla congelada (docs/pead-preregistro.md, resultado del 15-oct-2026):
- Señal: reacción anormal frente a SPY en el 10% más alto de los anuncios de los 365 días previos.
- Compra al cierre de la sesión siguiente a la de reacción; venta al cierre 40 sesiones después.
- Sin cubrir; coste 0,10% ida y vuelta. Se registra también el resultado frente a SPY.
Solo cuentan entradas desde LIVE_START: lo anterior ya era backtest.
"""
from __future__ import annotations

import datetime as dt
import math
import os
import urllib.parse
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import engine

LIVE_START = pd.Timestamp("2026-10-15")
HOLD = 40
LEDGER = "data/pead/vivo.csv"
COLS = ["ticker", "anuncio", "hora", "reaccion", "ra", "umbral_p90", "sorpresa_pct", "entrada", "vence",
        "precio_entrada", "spy_entrada", "estado", "fecha_salida", "precio_salida", "spy_salida",
        "ret", "ret_spy", "neto", "titulares"]
NY = ZoneInfo("America/New_York")


def drop_partial_session(px: pd.DataFrame, now: dt.datetime | None = None) -> pd.DataFrame:
    """Si se ejecuta con Wall Street abierto, la última fila es intradía: se quita."""
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(NY)
    if len(px) and px.index[-1].date() == now.date() and now.time() < dt.time(16, 15):
        return px.iloc[:-1]
    return px


def load() -> pd.DataFrame:
    if os.path.exists(LEDGER):
        return pd.read_csv(LEDGER, parse_dates=["anuncio", "reaccion", "entrada", "vence", "fecha_salida"])
    return pd.DataFrame(columns=COLS)


def headlines(ticker: str, day: pd.Timestamp, n: int = 5) -> str:
    """Titulares del anuncio (para la fase 2: filtro con IA). Solo se guardan; no deciden nada."""
    try:
        import requests
        q = urllib.parse.quote(f"{ticker} earnings after:{(day - pd.Timedelta(days=2)).date()} "
                               f"before:{(day + pd.Timedelta(days=1)).date()}")
        r = requests.get(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en", timeout=15)
        titles = [(i.findtext("title") or "").strip() for i in ET.fromstring(r.text).iter("item")][:n]
        return " || ".join(t for t in titles if t)
    except Exception:
        return ""


def update(book: pd.DataFrame, ev: pd.DataFrame, px: pd.DataFrame, fetch_headlines=headlines) -> pd.DataFrame:
    """Abre las posiciones cuya entrada ya ocurrió y cierra las que vencen. Idempotente."""
    days = px.index
    last = days[-1]
    have = set(zip(book["ticker"], pd.to_datetime(book["reaccion"])))
    new = []
    sig = ev[(ev["sig_ra"] == 1) & (ev["entrada"] >= LIVE_START) & (ev["entrada"] <= last)]
    for e in sig.itertuples(index=False):
        if (e.ticker, pd.Timestamp(e.reaccion)) in have or e.ticker not in px:
            continue
        i_e = days.get_loc(e.entrada)
        new.append({
            "ticker": e.ticker, "anuncio": e.anuncio, "hora": e.hora, "reaccion": e.reaccion, "ra": e.ra,
            "umbral_p90": getattr(e, "ra_hi", np.nan), "sorpresa_pct": e.sorpresa_pct, "entrada": e.entrada,
            "vence": days[i_e + HOLD] if i_e + HOLD < len(days) else pd.NaT,
            "precio_entrada": px.at[e.entrada, e.ticker], "spy_entrada": px.at[e.entrada, "SPY"],
            "estado": "ABIERTA", "titulares": fetch_headlines(e.ticker, pd.Timestamp(e.anuncio)),
        })
    if new:
        book = pd.concat([book, pd.DataFrame(new)], ignore_index=True) if len(book) else pd.DataFrame(new)
    book = book.reindex(columns=COLS)
    book = book.astype({"estado": object, "fecha_salida": object, "titulares": object})
    for idx, p in book[book["estado"] == "ABIERTA"].iterrows():
        i_e = days.get_loc(pd.Timestamp(p["entrada"]))
        if i_e + HOLD < len(days):  # vence: se vende al cierre de la sesión 40
            d = days[i_e + HOLD]
            ps, ss = px.at[d, p["ticker"]], px.at[d, "SPY"]
            ret = ps / p["precio_entrada"] - 1
            book.loc[idx, ["estado", "fecha_salida", "precio_salida", "spy_salida", "vence"]] = ["CERRADA", d, ps, ss, d]
            book.loc[idx, ["ret", "ret_spy", "neto"]] = [ret, ss / p["spy_entrada"] - 1, ret - engine.COST]
    return book.sort_values(["entrada", "ticker"]).reset_index(drop=True)


def pending(ev: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    """Señales del último día de reacción cuya compra será en la próxima sesión."""
    last = px.index[-1]
    return ev[(ev["sig_ra"] == 1) & (ev["reaccion"] == last)][["ticker", "anuncio", "ra"]]


def mark_to_market(book: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    op = book[book["estado"] == "ABIERTA"].copy()
    if op.empty:
        return op
    last = px.index[-1]
    op["precio_actual"] = [px.at[last, t] if t in px else np.nan for t in op["ticker"]]
    op["ret_actual"] = op["precio_actual"] / op["precio_entrada"] - 1
    op["spy_actual"] = px.at[last, "SPY"] / op["spy_entrada"] - 1
    op["sesiones"] = [px.index.get_loc(last) - px.index.get_loc(pd.Timestamp(e)) for e in op["entrada"]]
    return op


def summary(book: pd.DataFrame) -> dict:
    c = book[book["estado"] == "CERRADA"]
    out = {"abiertas": int((book["estado"] == "ABIERTA").sum()), "cerradas": len(c)}
    if len(c):
        net = c["neto"].astype(float)
        ex = c["ret"].astype(float) - c["ret_spy"].astype(float)
        se = net.std(ddof=1) / math.sqrt(len(c)) if len(c) > 1 else math.nan
        out.update({"neto_medio": net.mean(), "ic": 1.96 * se, "acierto": (net > 0).mean(),
                    "frente_spy": ex.mean()})
    return out
