"""Métricas y señales de tendencia por activo. Reglas transparentes, sin IA."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _pct(a, b):
    return (a / b - 1) if b and not math.isnan(b) else math.nan


def rsi(close: pd.Series, n: int = 14) -> float:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up.iloc[-1] / dn.iloc[-1] if dn.iloc[-1] else math.inf
    return 100 - 100 / (1 + rs)


def metrics(df: pd.DataFrame, level: bool = False) -> dict:
    """level=True para series que son un nivel (rendimiento de bono): cambios en puntos."""
    c = df["close"].astype(float).reset_index(drop=True)
    last = c.iloc[-1]

    def chg(n):
        if len(c) <= n:
            return math.nan
        return (last - c.iloc[-1 - n]) if level else _pct(last, c.iloc[-1 - n])

    rets = c.pct_change().dropna()
    vol20 = rets.tail(20).std()
    ma50 = c.tail(50).mean() if len(c) >= 50 else math.nan
    ma200 = c.tail(200).mean() if len(c) >= 200 else math.nan
    hi52, lo52 = c.max(), c.min()
    ret1 = rets.iloc[-1] if len(rets) else math.nan
    z1 = ret1 / rets.iloc[:-1].tail(60).std() if len(rets) > 20 else math.nan

    m = {
        "last": float(last), "date": str(df["date"].iloc[-1]),
        "chg_1d": chg(1), "chg_5d": chg(5), "chg_1m": chg(21), "chg_3m": chg(63),
        "vol20_ann": vol20 * math.sqrt(252) if not level else math.nan,
        "ma50": ma50, "ma200": ma200,
        "dist_ma50": _pct(last, ma50), "dist_ma200": _pct(last, ma200),
        "rsi14": rsi(c) if len(c) > 15 else math.nan,
        "from_high": _pct(last, hi52), "from_low": _pct(last, lo52),
        "z_1d": z1,
    }
    m["trend"] = trend_label(m)
    m["flags"] = flags(m)
    return m


def trend_label(m: dict) -> str:
    a, b, r = m["dist_ma50"], m["dist_ma200"], m["chg_1m"]
    if any(isinstance(x, float) and math.isnan(x) for x in (a, r)):
        return "sin datos"
    if a > 0 and (math.isnan(b) or b > 0) and r > 0:
        return "alcista"
    if a < 0 and (math.isnan(b) or b < 0) and r < 0:
        return "bajista"
    return "lateral"


def flags(m: dict) -> list[str]:
    f = []
    if not math.isnan(m["z_1d"]) and abs(m["z_1d"]) >= 2:
        f.append(f"movimiento anómalo hoy ({m['z_1d']:+.1f}σ)")
    if not math.isnan(m["from_high"]) and m["from_high"] >= -0.01:
        f.append("en máximos de 52 semanas")
    if not math.isnan(m["from_low"]) and m["from_low"] <= 0.01:
        f.append("en mínimos de 52 semanas")
    if not math.isnan(m["rsi14"]):
        if m["rsi14"] >= 70:
            f.append(f"sobrecompra (RSI {m['rsi14']:.0f})")
        elif m["rsi14"] <= 30:
            f.append(f"sobreventa (RSI {m['rsi14']:.0f})")
    return f


def crossed_ma(df: pd.DataFrame, n: int = 50) -> str | None:
    """Cruce del precio con su media de n sesiones en la última sesión."""
    c = df["close"].astype(float).reset_index(drop=True)
    if len(c) < n + 2:
        return None
    ma = c.rolling(n).mean()
    prev, now = c.iloc[-2] - ma.iloc[-2], c.iloc[-1] - ma.iloc[-1]
    if prev <= 0 < now:
        return f"cruza al alza su media de {n} sesiones"
    if prev >= 0 > now:
        return f"cruza a la baja su media de {n} sesiones"
    return None


def nan_to_none(x):
    if isinstance(x, (float, np.floating)) and math.isnan(x):
        return None
    if isinstance(x, np.floating):
        return float(x)
    return x
