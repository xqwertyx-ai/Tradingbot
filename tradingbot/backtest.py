"""Backtest de reglas simples sobre los mercados BTC 5 min de Polymarket.

Cada operación compra 1 acción del lado elegido al precio de referencia de
Polymarket en el momento de entrada, más deslizamiento y comisión taker.
Paga 1 USDC si acierta y 0 si falla.

Las estrategias están fijadas de antemano (ver STRATEGIES). Añadir variantes
tras mirar los resultados es sobreajuste: si se añade alguna, anotarlo en el informe.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from . import config as C


# ---------- Features ----------

def build_features(markets: pd.DataFrame, prices: pd.DataFrame, btc: pd.DataFrame) -> pd.DataFrame:
    """Una fila por mercado con señales de BTC y precio de Polymarket por minuto."""
    W = C.WINDOW_SECONDS
    # precio de BTC en el instante T = cierre de la vela que empieza en T-60
    px = pd.Series(btc["close"].values, index=btc["t"].values + 60).sort_index()

    df = markets[["start_ts", "up_won"]].copy().sort_values("start_ts").reset_index(drop=True)
    s = df["start_ts"].values

    def at(ts):
        return px.reindex(ts).values

    p0 = at(s)
    df["ret_prev5"] = p0 / at(s - W) - 1
    for k in (1, 2, 3):
        df[f"ret_intra{k}"] = at(s + 60 * k) / p0 - 1

    # precio de "Up" en Polymarket en cada minuto de entrada
    pr = prices.sort_values(["start_ts", "t"])
    groups = {k: g for k, g in pr.groupby("start_ts")}
    for k in (0, 1, 2, 3):
        vals = []
        for st in s:
            g = groups.get(st)
            te = st + 60 * k
            if g is None:
                vals.append(np.nan)
                continue
            g = g[(g["t"] <= te) & (g["t"] >= te - C.MAX_PRICE_AGE_SECONDS)]
            vals.append(g["p_up"].iloc[-1] if len(g) else np.nan)
        df[f"pm_up{k}"] = vals
    return df


# ---------- Estrategias ----------

def _sign(x: pd.Series) -> pd.Series:
    return np.sign(x).fillna(0).astype(int)


@dataclass
class Strategy:
    name: str
    description: str
    entry_minute: int
    side: Callable[[pd.DataFrame], pd.Series]  # +1 Up, -1 Down, 0 no operar


STRATEGIES = [
    Strategy("siempre_up", "Control: comprar siempre Up al inicio", 0,
             lambda d: pd.Series(1, index=d.index)),
    Strategy("momentum_prev5", "Lado del movimiento de BTC en los 5 min previos", 0,
             lambda d: _sign(d["ret_prev5"])),
    Strategy("reversion_prev5", "Lado contrario al movimiento de BTC en los 5 min previos", 0,
             lambda d: -_sign(d["ret_prev5"])),
    Strategy("continuacion_m1", "Lado del movimiento de BTC en el 1er minuto de la ventana", 1,
             lambda d: _sign(d["ret_intra1"])),
    Strategy("continuacion_m2", "Lado del movimiento de BTC en los 2 primeros minutos", 2,
             lambda d: _sign(d["ret_intra2"])),
    Strategy("continuacion_m3", "Lado del movimiento de BTC en los 3 primeros minutos", 3,
             lambda d: _sign(d["ret_intra3"])),
    Strategy("favorito_m2", "Lado que el mercado da como favorito en el minuto 2", 2,
             lambda d: _sign(d["pm_up2"] - 0.5)),
    Strategy("desfavorito_m2", "Lado que el mercado da como no favorito en el minuto 2", 2,
             lambda d: -_sign(d["pm_up2"] - 0.5)),
]


# ---------- Simulación ----------

def fee(q):
    return C.FEE_RATE * q * (1 - q)


def simulate(df: pd.DataFrame, strat: Strategy) -> pd.DataFrame:
    side = strat.side(df)
    p_up = df[f"pm_up{strat.entry_minute}"]
    q = np.where(side > 0, p_up, 1 - p_up)
    cost = q + C.SLIPPAGE + fee(q)
    won = np.where(side > 0, df["up_won"], 1 - df["up_won"])
    ok = (side != 0) & p_up.notna() & (q > 0.02) & (q < 0.98) & (cost < 1)
    out = pd.DataFrame({
        "start_ts": df["start_ts"], "q": q, "cost": cost, "won": won,
        "pnl": won - cost,
    })[ok.values]
    return out


# ---------- Estadística ----------

def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def summarize(trades: pd.DataFrame) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0}
    k = int(trades["won"].sum())
    lo, hi = wilson(k, n)
    m = trades["pnl"].mean()
    se = trades["pnl"].std(ddof=1) / math.sqrt(n) if n > 1 else math.nan
    return {
        "n": n,
        "hit": k / n, "hit_lo": lo, "hit_hi": hi,
        "breakeven": trades["cost"].mean(),
        "pnl_mean": m, "pnl_lo": m - 1.96 * se, "pnl_hi": m + 1.96 * se,
        "pnl_total": trades["pnl"].sum(),
    }


def split_time(df: pd.DataFrame):
    cut = df["start_ts"].quantile(C.TRAIN_FRACTION)
    return df[df["start_ts"] <= cut], df[df["start_ts"] > cut]


def run(df: pd.DataFrame) -> list[dict]:
    train, test = split_time(df)
    rows = []
    for st in STRATEGIES:
        a, b = summarize(simulate(train, st)), summarize(simulate(test, st))
        passed = (
            b.get("n", 0) >= C.MIN_TRADES_TEST and b["pnl_lo"] > 0
        )
        rows.append({"strategy": st, "train": a, "test": b, "passed": passed})
    return rows


def calibration(df: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    d = df.dropna(subset=[f"pm_up{k}"])
    bins = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0001]
    d = d.assign(bin=pd.cut(d[f"pm_up{k}"], bins, right=False))
    g = d.groupby("bin", observed=True).agg(
        n=("up_won", "size"), precio_medio=(f"pm_up{k}", "mean"), freq_up=("up_won", "mean"))
    return g.reset_index()
