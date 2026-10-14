"""Backtest del agente con datos sintéticos y sin red: comprueba que no usa información futura."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from dashboard import analysis, prices  # noqa: E402
from dashboard.universe import ASSETS  # noqa: E402


def _series(seed):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-06-01", "2026-10-13").date
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(dates))))
    return pd.DataFrame({"date": dates, "close": c, "high": c, "low": c})


def test_agent_backtest_no_lookahead(tmp_path):
    import backtest_agente as bt
    cwd = os.getcwd()
    os.chdir(tmp_path)
    seen = []
    orig = (prices.prefetch_yfinance, bt.headlines, analysis.analyze)
    try:
        def fake_prefetch(tickers, period="1y"):
            for i, t in enumerate(tickers):
                prices._YF[t] = _series(i)
        prices.prefetch_yfinance = fake_prefetch
        bt.headlines = lambda day, prev: [{"title": f"t{i}", "link": "", "source": "x", "published":
                                           f"{day}T12:00:00+00:00", "category": "macro", "score": 1}
                                          for i in range(6)]

        def fake_analyze(date, mode, table, news, open_h):
            d = dt.date.fromisoformat(date)
            for r in table:  # ningún dato posterior a la fecha de decisión
                assert dt.date.fromisoformat(r["m"]["date"]) <= d
                if r["ticker"].endswith("-USD"):
                    assert dt.date.fromisoformat(r["m"]["date"]) < d
            seen.append(date)
            return {"hipotesis": [{"ticker": "^GSPC", "direccion": "alcista", "horizonte_dias": 3,
                                   "invalidacion_pct": 2, "confianza": 65, "tesis": "x"}],
                    "decision": "operar", "uso": {"coste_usd": 0.04}}
        analysis.analyze = fake_analyze
        bt.run(dt.date(2026, 8, 3), dt.date(2026, 8, 21), False)
        assert len(seen) == 15
        book = pd.read_csv(bt.LEDGER)
        assert len(book) == 15 and (book["estado"] != "ABIERTA").all()
        assert "Desde agosto" in open(bt.REPORT, encoding="utf-8").read()
        n_calls = len(seen)
        bt.run(dt.date(2026, 8, 3), dt.date(2026, 8, 21), False)  # caché: no repite llamadas
        assert len(seen) == n_calls and len(pd.read_csv(bt.LEDGER)) == 15
    finally:
        prices.prefetch_yfinance, bt.headlines, analysis.analyze = orig
        prices._YF.clear()
        os.chdir(cwd)
