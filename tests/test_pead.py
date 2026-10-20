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


def test_live_ledger_opens_and_closes_without_lookahead():
    import datetime as dt
    from pead import live
    earn, px = synthetic(n_firms=80, drift=0.5, seed=3)
    old = live.LIVE_START
    live.LIVE_START = pd.Timestamp("2026-01-01")
    try:
        ev = engine.build_events(earn, px)
        cut = pd.Timestamp("2026-06-30")
        px_cut = px[px.index <= cut]
        ev_cut = engine.build_events(earn[pd.to_datetime(earn["fecha"]) <= cut], px_cut)
        book = live.update(pd.DataFrame(columns=live.COLS), ev_cut, px_cut, fetch_headlines=lambda t, d: "")
        assert len(book) and (pd.to_datetime(book["entrada"]) <= cut).all()
        assert (pd.to_datetime(book["entrada"]) >= live.LIVE_START).all()
        # al avanzar el tiempo, las posiciones vencidas se cierran a 40 sesiones exactas
        book2 = live.update(book, ev, px, fetch_headlines=lambda t, d: "")
        closed = book2[book2["estado"] == "CERRADA"]
        assert len(closed)
        for r in closed.itertuples():
            assert px.index.get_loc(r.fecha_salida) - px.index.get_loc(r.entrada) == live.HOLD
        # ejecutar dos veces no duplica
        assert len(live.update(book2, ev, px, fetch_headlines=lambda t, d: "")) == len(book2)
        # con la bolsa abierta se descarta la fila intradía
        now = dt.datetime.combine(px.index[-1].date(), dt.time(15, 0), live.NY)
        assert len(live.drop_partial_session(px, now)) == len(px) - 1
    finally:
        live.LIVE_START = old


def test_compra_pendiente_el_mismo_dia():
    """Una reacción fuerte en la última sesión aparece como compra pendiente (antes no salía nunca)."""
    import numpy as np
    import pandas as pd
    from pead import engine, live
    days = pd.bdate_range("2025-01-01", "2026-10-20")
    rng = np.random.default_rng(0)
    tick = [f"T{i}" for i in range(40)]
    px = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (len(days), 41)), axis=0)),
                      index=days, columns=tick + ["SPY"])
    rows = [{"ticker": t, "fecha": str(d.date()), "hora": "07:00", "sorpresa_pct": 1.0}
            for k, t in enumerate(tick) for d in days[20 + k % 15::15]]  # ≥ 200 previos (MIN_PRIOR)
    px.loc[days[-1], "T0"] = px.loc[days[-2], "T0"] * 1.5          # +50% el último día
    rows.append({"ticker": "T0", "fecha": str(days[-1].date()), "hora": "07:00", "sorpresa_pct": 20.0})
    ev = engine.build_events(pd.DataFrame(rows), px)
    pend = live.pending(ev, px)
    assert "T0" in set(pend["ticker"])
    book = live.update(live.load().iloc[0:0], ev, px, fetch_headlines=lambda t, d: "")
    assert "T0" not in set(book["ticker"])                          # aún no se ha comprado
