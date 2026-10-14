import json

import numpy as np
import pandas as pd

from tradingbot import config as C
from tradingbot.backtest import STRATEGIES, build_features, run, simulate, wilson
from tradingbot.data import parse_event
from tradingbot.report import write_report

T0 = 1_791_979_200


def synthetic(n=3000, edge=0.0, seed=0):
    """BTC aleatorio. Con edge > 0, el resultado sigue el 1er minuto más a menudo,
    pero el mercado sigue cotizando 0,50 (ventaja plantada para continuacion_m1)."""
    rng = np.random.default_rng(seed)
    t0 = T0 - 600
    n_min = n * 5 + 20
    close = 80000 * np.exp(np.cumsum(rng.normal(0, 4e-4, n_min)))
    btc = pd.DataFrame({"t": t0 + 60 * np.arange(n_min), "close": close})
    btc["open"] = btc["high"] = btc["low"] = btc["close"]
    px = pd.Series(close, index=btc["t"] + 60)

    starts = T0 + 300 * np.arange(n)
    m1 = np.sign(px.reindex(starts + 60).values - px.reindex(starts).values)
    follow = rng.random(n) < 2 * edge  # acierto esperado de continuacion_m1 = 0,5 + edge
    up_won = np.where(follow, m1 > 0, rng.random(n) < 0.5).astype(int)
    markets = pd.DataFrame({"start_ts": starts, "up_won": up_won, "slug": "x", "up_token": "y"})
    prices = pd.DataFrame([
        {"start_ts": s, "t": s + 60 * k - 5, "p_up": 0.5} for s in starts for k in range(4)
    ])
    return markets, prices, btc


def test_wilson():
    lo, hi = wilson(50, 100)
    assert lo < 0.5 < hi and abs((lo + hi) / 2 - 0.5) < 1e-9


def test_costs_at_even_odds():
    m, p, b = synthetic(50)
    df = build_features(m, p, b)
    tr = simulate(df, STRATEGIES[0])  # siempre_up a 0,50
    assert np.allclose(tr["cost"], 0.5 + C.SLIPPAGE + C.FEE_RATE * 0.25)


def test_no_edge_fails_and_planted_edge_passes():
    df = build_features(*synthetic(4000, edge=0.0))
    assert not any(r["passed"] for r in run(df))

    df = build_features(*synthetic(4000, edge=0.1, seed=1))
    res = {r["strategy"].name: r for r in run(df)}
    assert res["continuacion_m1"]["passed"]
    assert not res["siempre_up"]["passed"]


def test_stale_price_is_skipped():
    m, p, b = synthetic(10)
    p["t"] = p["t"] - (C.MAX_PRICE_AGE_SECONDS + 60)
    df = build_features(m, p, b)
    assert df["pm_up2"].isna().all()


def test_parse_event():
    ev = {"slug": "btc-updown-5m-1", "markets": [{
        "outcomes": json.dumps(["Up", "Down"]), "outcomePrices": json.dumps(["0", "1"]),
        "clobTokenIds": json.dumps(["a", "b"]), "closed": True}]}
    assert parse_event(ev, 1) == {"start_ts": 1, "slug": "btc-updown-5m-1", "up_won": 0, "up_token": "a"}
    ev["markets"][0]["outcomePrices"] = json.dumps(["0.5", "0.5"])
    assert parse_event(ev, 1) is None


def test_report_writes(tmp_path):
    df = build_features(*synthetic(500))
    text = write_report(df, str(tmp_path / "r.md"))
    assert "Veredicto" in text
