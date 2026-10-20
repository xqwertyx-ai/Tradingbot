"""Test en vivo diario de la regla PEAD congelada. Uso: python scripts/pead_vivo.py

Ejecutar tras el cierre de Wall Street. Actualiza data/pead/vivo.csv (posiciones simuladas)
y data/pead/vivo-estado.json (lo que muestra la web).
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from pead import data, engine, live  # noqa: E402

if __name__ == "__main__":
    today = pd.Timestamp(dt.date.today())
    tickers = data.universe()
    # Refrescar las empresas con resultados recientes o inminentes (hora y sorpresa definitivas).
    d = f"{data.RAW}/earnings"
    os.makedirs(d, exist_ok=True)
    stale = []
    for t in tickers:
        p = f"{d}/{t}.csv"
        if not os.path.exists(p):
            continue
        e = pd.read_csv(p)
        dates = pd.to_datetime(e["fecha"])
        old = (dt.datetime.now().timestamp() - os.path.getmtime(p)) > 30 * 86400
        if old or ((dates >= today - pd.Timedelta(days=7)) & (dates <= today + pd.Timedelta(days=2))).any():
            stale.append(t)
            os.remove(p)
    print(f"Resultados: refrescando {len(stale)} empresas")
    earn = data.earnings(tickers, limit=12)
    earn = earn[pd.to_datetime(earn["fecha"]) >= today - pd.Timedelta(days=800)]
    print("Precios...")
    px = data.prices(tickers, start=str((today - pd.Timedelta(days=900)).date()), force=True,
                     path=f"{data.RAW}/precios-vivo.csv.gz")
    px = live.drop_partial_session(px)
    print(f"  última sesión: {px.index[-1]:%Y-%m-%d}")
    ev = engine.build_events(earn, px)
    # Diagnóstico: anuncios recientes, su reacción anormal y el umbral del 10% mejor
    rec_e = earn[pd.to_datetime(earn["fecha"]) >= live.LIVE_START - pd.Timedelta(days=3)]
    print(f"Anuncios desde {live.LIVE_START - pd.Timedelta(days=3):%Y-%m-%d} en los datos: {len(rec_e)} "
          f"(con fecha pasada: {(pd.to_datetime(rec_e['fecha']) <= px.index[-1]).sum()})")
    rec = ev[ev["reaccion"] >= live.LIVE_START - pd.Timedelta(days=3)] if not ev.empty else ev
    print(f"Eventos con reacción reciente: {len(rec)}; señales de compra: {int((rec['sig_ra'] == 1).sum()) if len(rec) else 0}")
    if len(rec):
        print(rec.sort_values("ra", ascending=False)[["ticker", "anuncio", "hora", "reaccion", "entrada", "ra", "ra_hi", "sig_ra"]]
              .head(15).to_string(index=False))
    na_last = px.iloc[-1].isna().sum()
    print(f"Precios: {na_last} de {px.shape[1]} sin dato en la última sesión")
    book = live.update(live.load(), ev, px)
    os.makedirs("data/pead", exist_ok=True)
    book.to_csv(live.LEDGER, index=False)
    mtm = live.mark_to_market(book, px)
    pend = live.pending(ev, px)
    state = {
        "generado": dt.datetime.now(dt.timezone.utc).isoformat(), "sesion": str(px.index[-1].date()),
        "inicio": str(live.LIVE_START.date()), "resumen": live.summary(book),
        "pendientes": pend.assign(anuncio=pend["anuncio"].astype(str)).to_dict("records"),
        "abiertas": [{"ticker": r.ticker, "entrada": str(pd.Timestamp(r.entrada).date()),
                      "sesiones": int(r.sesiones), "ret": float(r.ret_actual), "spy": float(r.spy_actual),
                      "ra": float(r.ra)} for r in mtm.itertuples()],
        "cerradas_recientes": [{"ticker": r.ticker, "salida": str(pd.Timestamp(r.fecha_salida).date()),
                                "neto": float(r.neto), "spy": float(r.ret_spy)}
                               for r in book[book["estado"] == "CERRADA"].tail(10).itertuples()],
    }
    json.dump(state, open("data/pead/vivo-estado.json", "w"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(state["resumen"], default=str), f"pendientes: {len(pend)}, abiertas: {len(mtm)}")
