"""Experimento PEAD con datos sintéticos (sin red)."""
import numpy as np
import pandas as pd

from pead import engine


def synthetic(n_firms=300, drift=0.0, seed=0):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2019-01-01", "2026-10-13")
    T = len(days)
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, T)))
    px = {"SPY": spy}
    rows = []
    for f in range(n_firms):
        t = f"F{f:03d}"
        ret = rng.normal(0, 0.015, T)
        start = rng.integers(0, 63)
        for i in range(start, T - 70, 63):  # un anuncio por trimestre
            jump = rng.normal(0, 0.06)
            ret[i] += jump                          # reacción el día i (antes de la apertura)
            ret[i + 2:i + 22] += drift * jump / 20  # deriva posterior proporcional a la sorpresa
            rows.append({"ticker": t, "fecha": str(days[i].date()), "hora": "07:00",
                         "bpa_est": 1.0, "bpa_real": 1.0 + jump, "sorpresa_pct": 100 * jump + rng.normal(0, 2)})
        px[t] = 50 * np.exp(np.cumsum(ret)) * spy / spy[0]
    return pd.DataFrame(rows), pd.DataFrame(px, index=days)


def test_timing_and_no_lookahead():
    earn, px = synthetic(n_firms=60)
    ev = engine.build_events(earn, px)
    assert (ev["entrada"] > ev["reaccion"]).all()
    assert (ev.loc[ev["hora"] == "antes_apertura", "reaccion"] == ev.loc[ev["hora"] == "antes_apertura", "anuncio"]).all()
    # cambiar eventos futuros no altera las señales de los pasados
    cut = pd.Timestamp("2024-01-01")
    ev2 = engine.build_events(earn[pd.to_datetime(earn["fecha"]) < cut], px)
    a = ev[ev["reaccion"] < cut - pd.Timedelta(days=10)].set_index(["ticker", "reaccion"])["sig_ra"]
    b = ev2.set_index(["ticker", "reaccion"])["sig_ra"].reindex(a.index)
    assert (a == b).all()


def test_after_close_timing():
    earn, px = synthetic(n_firms=5)
    earn = earn.assign(hora="16:30")
    ev = engine.build_events(earn, px)
    assert (ev["reaccion"] > ev["anuncio"]).all()


def test_planted_drift_is_found_and_noise_is_not():
    ev = engine.build_events(*synthetic(drift=1.0, seed=1))
    res = engine.evaluate(ev)
    ok = res[(res["senal"] == "sig_ra") & (res["version"] == "cubierta") & (res["plazo"] == 20)]
    assert ok["pasa"].any()
    ev0 = engine.build_events(*synthetic(drift=0.0, seed=2))
    res0 = engine.evaluate(ev0)
    assert res0["pasa"].sum() <= 1
