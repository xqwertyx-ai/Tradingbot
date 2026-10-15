"""Prueba de extremo a extremo de la portada con datos sintéticos (sin red)."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from dashboard import analysis, ledger, news, prices  # noqa: E402
from dashboard.news import parse_feed  # noqa: E402


def fake_series(seed):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=dt.date.today(), periods=260).date
    close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.012, len(dates))))
    return pd.DataFrame({"date": dates, "close": close, "high": close * 1.01, "low": close * 0.99})


def fake_ai(date, mode, table, items, open_h):
    t = [a["ticker"] for a in table]
    return analysis.validate({
        "resumen": "Jornada de prueba.", "clima": "mixto",
        "noticias": [{"id": 0, "categoria": "macro", "novedad": "Sorpresa.", "impacto": "Sube X.",
                      "importancia": 4}, {"id": 999}],
        "divergencias": ["Ejemplo de divergencia."],
        "hipotesis": [{"ticker": t[0], "direccion": "alcista", "horizonte_dias": 5, "tesis": "Prueba",
                       "disparador": "cierre > X", "objetivo_pct": 6, "invalidacion_pct": 3, "confianza": 65,
                       "contra": "Ninguno.", "sesgos": "Confirmación."},
                      {"ticker": "INVENTADO", "direccion": "alcista", "horizonte_dias": 5,
                       "objetivo_pct": 4, "invalidacion_pct": 2, "confianza": 90},
                      {"ticker": "^TNX", "direccion": "alcista", "horizonte_dias": 5,
                       "objetivo_pct": 4, "invalidacion_pct": 2, "confianza": 90}],
        "vigilar": [{"ticker": t[1], "motivo": "Prueba."}],
        "decision": "operar", "decision_motivo": "Prueba.", "modelo": "fake",
    }, set(t), len(items), mode)


def test_end_to_end(tmp_path, monkeypatch=None):
    import portada
    cwd = os.getcwd()
    os.chdir(tmp_path)
    orig = (prices.fetch, prices.check_source, news.fetch_news, analysis.analyze, prices.prefetch_yfinance)
    try:
        counter = iter(range(100))
        prices.prefetch_yfinance = lambda tickers: None
        real_mode, portada.effective_mode = portada.effective_mode, (lambda m, now: m)  # sin depender de la hora
        prices.fetch = lambda a: (fake_series(next(counter)), "Yahoo")
        prices.check_source = lambda a, df, s: "ok"
        news.fetch_news = lambda: ([{"title": "La Fed sube tipos", "link": "https://x", "source": "Test",
                                     "feed": "t", "published": "2026-10-14T18:00:00+00:00",
                                     "category": "macro", "score": 3}], {"Test": "ok (1)"})
        analysis.analyze = fake_ai
        portada.main("cierre")
        readme = open("README.md", encoding="utf-8").read()
        assert "Radar de mercados" in readme and "La Fed sube tipos" in readme
        assert "INVENTADO" not in readme
        assert "+6.0% / −3.0%" in readme and "✅" in readme  # EV = 0,65·6 − 0,35·3 − 0,1 = 2,75%
        page = open("site/index.html", encoding="utf-8").read()
        assert "La Fed sube tipos" in page and 'class="thermo"' in page and "Más suben" in page
        book = ledger.load()
        assert len(book) == 1 and book.iloc[0]["operada"] == 1
        for f in ("mapa-light.png", "mapa-dark.png", "tendencias-light.png"):
            assert os.path.getsize(os.path.join("assets", f)) > 5000
        portada.main("cierre")  # reejecutar el mismo día no duplica hipótesis
        assert len(ledger.load()) == 1
    finally:
        prices.fetch, prices.check_source, news.fetch_news, analysis.analyze, prices.prefetch_yfinance = orig
        portada.effective_mode = real_mode
        os.chdir(cwd)


def test_intraday_mode():
    import portada
    utc = dt.timezone.utc
    assert portada.effective_mode("cierre", dt.datetime(2026, 10, 14, 19, 10, tzinfo=utc)) == "intradía"
    assert portada.effective_mode("cierre", dt.datetime(2026, 10, 14, 20, 35, tzinfo=utc)) == "cierre"
    assert portada.effective_mode("cierre", dt.datetime(2026, 10, 17, 19, 0, tzinfo=utc)) == "cierre"  # sábado


def test_expected_value_and_gating():
    h = {"ticker": "^GSPC", "confianza": 55, "objetivo_pct": 3, "invalidacion_pct": 2}
    assert abs(analysis.expected_value(h) - (0.55 * 3 - 0.45 * 2 - 0.10)) < 1e-9  # 0,65%: no llega a 1%
    out = analysis.validate({"hipotesis": [dict(h, direccion="alcista", horizonte_dias=5),
                                           dict(h, direccion="alcista", horizonte_dias=5, objetivo_pct=4.5)]},
                            {"^GSPC"}, 0, "cierre")
    assert [x["operable"] for x in out["hipotesis"]] == [False, True] and out["decision"] == "operar"


def test_target_hit_is_acierto():
    s = pd.DataFrame({"date": pd.bdate_range("2026-01-01", periods=6).date,
                      "close": [100, 101, 103.5, 99, 98, 97], "high": 0, "low": 0})
    book = ledger.add(ledger.load("/nonexistent"), [
        {"ticker": "X", "direccion": "alcista", "horizonte_dias": 5, "objetivo_pct": 3,
         "invalidacion_pct": 2, "confianza": 60, "operable": True}], str(s["date"].iloc[0]), {"X": 100.0})
    book = ledger.evaluate(book, {"X": s})
    assert book.iloc[0]["estado"] == "ACIERTO" and abs(float(book.iloc[0]["retorno"]) - 0.035) < 1e-9
    st = ledger.stats(book)
    assert abs(st["operadas"]["ret_neto_medio"] - (0.035 - 0.001)) < 1e-9  # coste 0,10% (no cripto/FX)


def test_ledger_evaluation():
    s = fake_series(1)
    d0 = str(s["date"].iloc[-30])
    book = ledger.add(ledger.load("/nonexistent"), [
        {"ticker": "X", "direccion": "alcista", "horizonte_dias": 5, "invalidacion_pct": 50, "confianza": 50},
        {"ticker": "X", "direccion": "bajista", "horizonte_dias": 20, "invalidacion_pct": 0.01, "confianza": 70},
    ], d0, {"X": float(s["close"].iloc[-30])})
    book = ledger.evaluate(book, {"X": s})
    assert book.iloc[0]["estado"] == "EXPIRADA"
    assert book.iloc[1]["estado"] in ("FALLO", "EXPIRADA")
    st = ledger.stats(book)
    assert st["cerradas"] == 2


def test_parse_google_news():
    xml = """<rss><channel><item><title>Wall Street cae - Reuters</title><link>https://n</link>
    <pubDate>Wed, 14 Oct 2026 18:00:00 GMT</pubDate><source url="https://r">Reuters</source></item>
    </channel></rss>"""
    it = parse_feed(xml, "Google News · markets")[0]
    assert it["title"] == "Wall Street cae" and it["source"] == "Reuters" and it["published"].year == 2026
