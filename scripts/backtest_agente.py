"""Backtest del agente: reproduce la revisión de cierre de cada sesión con lo que se sabía ese día.

Uso: python scripts/backtest_agente.py --desde 2026-07-01 --hasta 2026-10-13 [--solo-noticias]

Sin información futura:
- Titulares: solo los publicados antes del cierre de Wall Street de ese día.
- Precios: series cortadas en ese día. Cripto (cotiza 24 h y su vela diaria cierra a medianoche
  UTC, después de la decisión) se muestra hasta el día anterior y se entra al cierre del día.
- Modelo: su conocimiento fiable llega a junio de 2026. Julio se informa aparte por si el
  modelo supiera algo de esas semanas; el resultado que cuenta es de agosto en adelante.
Cada análisis se guarda en caché (data/agent_bt/ai/), así que relanzar no vuelve a pagar.
"""
import argparse
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from agentbt.news_hist import headlines  # noqa: E402
from dashboard import analysis, ledger, prices  # noqa: E402
from dashboard.indicators import metrics, nan_to_none  # noqa: E402
from dashboard.universe import ASSETS  # noqa: E402

OUT = "data/agent_bt"
LEDGER = f"{OUT}/hipotesis.csv"
REPORT = "reports/agente-backtest.md"
CLEAN_FROM = dt.date(2026, 8, 1)
COST = {"Cripto": 0.002, "Macro": 0.0004}  # ida y vuelta; resto 0,1%


def is_crypto(t):
    return t.endswith("-USD")


def table_for(day, series):
    rows = []
    for a in ASSETS:
        df = series.get(a["yahoo"])
        if df is None:
            continue
        cut = day - dt.timedelta(days=1) if is_crypto(a["yahoo"]) else day
        d = df[pd.to_datetime(df["date"]).dt.date <= cut]
        if len(d) < 30:
            continue
        m = metrics(d, level=a.get("level", False))
        rows.append({"ticker": a["yahoo"], "name": a["name"], "level": a.get("level", False),
                     "m": {k: nan_to_none(v) for k, v in m.items()}})
    return rows


def ref_prices(day, series):
    out = {}
    for t, df in series.items():
        d = df[pd.to_datetime(df["date"]).dt.date == day]
        if len(d):
            out[t] = float(d["close"].iloc[-1])
    return out


def truncate(series, day):
    return {t: df[pd.to_datetime(df["date"]).dt.date <= day] for t, df in series.items()}


def run(desde, hasta, solo_noticias):
    prices.prefetch_yfinance([a["yahoo"] for a in ASSETS], period="2y")
    series = dict(prices._YF)
    if "^GSPC" not in series:
        sys.exit("Sin precios del S&P 500: no se pueden fijar las sesiones.")
    days = [d for d in pd.to_datetime(series["^GSPC"]["date"]).dt.date if desde <= d <= hasta]
    allp = list(pd.to_datetime(series["^GSPC"]["date"]).dt.date)
    print(f"{len(days)} sesiones de {days[0]} a {days[-1]}")

    os.makedirs(f"{OUT}/ai", exist_ok=True)
    book = ledger.load(LEDGER)
    cost = 0.0
    for day in days:
        prev = allp[allp.index(day) - 1]
        news = headlines(day, prev)
        if solo_noticias:
            continue
        cache = f"{OUT}/ai/{day.isoformat()}.json"
        if os.path.exists(cache):
            with open(cache, encoding="utf-8") as f:
                ai = json.load(f)
        else:
            if len(news) < 5:
                print(f"  {day}: pocos titulares, se salta")
                continue
            book = ledger.evaluate(book, truncate(series, day))
            open_h = book[book["estado"] == "ABIERTA"][["ticker", "direccion", "vence", "tesis"]].to_dict("records")
            ai = analysis.analyze(day.isoformat(), "cierre", table_for(day, series), news, open_h)
            if not ai or ai.get("error"):
                print(f"  {day}: análisis fallido ({ai and ai.get('error')})")
                continue
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(ai, f, ensure_ascii=False)
        cost += (ai.get("uso") or {}).get("coste_usd", 0)
        if not (book["fecha"] == day.isoformat()).any():
            book = ledger.add(book, ai.get("hipotesis", []), day.isoformat(), ref_prices(day, series),
                              version="bt-1.0")
            ledger.save(book, LEDGER)  # permite reanudar si se corta
        print(f"  {day}: {len(ai.get('hipotesis', []))} hipótesis · decisión: {ai.get('decision')}")
    if solo_noticias:
        return
    book = ledger.evaluate(book, series)
    ledger.save(book, LEDGER)
    report(book, series, days, cost)


# ---------- Informe ----------

def wilson(k, n, z=1.96):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def momentum_baseline(book, series):
    """Misma fecha, activo, plazo e invalidación, pero dirección = signo del último mes."""
    hits = []
    for _, h in book[book["estado"].isin(["FALLO", "EXPIRADA"])].iterrows():
        df = series[h["ticker"]]
        d = df[pd.to_datetime(df["date"]) <= pd.Timestamp(h["fecha"])]["close"]
        if len(d) < 22:
            continue
        mom = "alcista" if d.iloc[-1] >= d.iloc[-22] else "bajista"
        fake = h.copy()
        fake["direccion"], fake["estado"] = mom, "ABIERTA"
        ev = ledger.evaluate(pd.DataFrame([fake]), {h["ticker"]: df})
        if ev.iloc[0]["estado"] != "ABIERTA":
            hits.append(int(ev.iloc[0]["acierto"]))
    return hits


def line(label, sub):
    n = len(sub)
    if not n:
        return f"| {label} | 0 | — | — | — |"
    k = int(sub["acierto"].astype(int).sum())
    lo, hi = wilson(k, n)
    net = (sub["retorno"].astype(float) - sub["coste"]).mean()
    return f"| {label} | {n} | {100 * k / n:.0f}% | {100 * lo:.0f}–{100 * hi:.0f}% | {100 * net:+.2f}% |"


def report(book, series, days, cost):
    group = {a["yahoo"]: a["group"] for a in ASSETS}
    closed = book[book["estado"].isin(["FALLO", "EXPIRADA"])].copy()
    closed["coste"] = [COST.get(group.get(t, ""), 0.001) for t in closed["ticker"]]
    closed["fecha_d"] = pd.to_datetime(closed["fecha"]).dt.date
    clean = closed[closed["fecha_d"] >= CLEAN_FROM]
    july = closed[closed["fecha_d"] < CLEAN_FROM]
    base = momentum_baseline(book[pd.to_datetime(book["fecha"]).dt.date >= CLEAN_FROM], series)
    no_trade = sum(1 for d in days if os.path.exists(f"{OUT}/ai/{d}.json")
                   and json.load(open(f"{OUT}/ai/{d}.json", encoding="utf-8")).get("decision") == "no operar hoy")
    L = ["# Backtest del agente de noticias", "",
         f"Generado: {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC · modelo {analysis.MODEL} · "
         f"coste total de la API ≈ {cost:.2f} USD. Simulación; no es asesoramiento financiero.", "",
         "## Cómo se hizo",
         f"- {len(days)} sesiones, de {days[0]} a {days[-1]}. Cada día, el mismo análisis de cierre que la web, "
         "solo con titulares publicados antes del cierre de Wall Street y precios hasta ese día.",
         "- Hipótesis evaluadas con las reglas de la bitácora: FALLO si un cierre toca la invalidación; "
         "al vencer, se puntúa por el signo del retorno.",
         "- Retorno neto: descontando costes simulados (0,1% ida y vuelta en acciones, 0,04% divisas, 0,2% cripto).",
         f"- **Lo que cuenta es desde el {CLEAN_FROM:%d-%m-%Y}.** El conocimiento fiable del modelo llega a junio de 2026; "
         "julio se muestra aparte por si supiera algo de esas semanas.", "",
         "## Resultados (hipótesis cerradas)", "",
         "| Grupo | n | Acierto | IC 95% | Retorno neto medio |", "|---|--:|--:|--:|--:|",
         line("Desde agosto · todas", clean),
         line("Desde agosto · operadas (confianza ≥ 60)", clean[clean["operada"] == 1]),
         line("Desde agosto · solo vigilancia (< 60)", clean[clean["operada"] == 0]),
         line("Julio (posible contaminación)", july), ""]
    if base:
        lo, hi = wilson(sum(base), len(base))
        L += [f"**Referencia ingenua** (mismas fechas, activos y plazos, dirección = tendencia del último mes): "
              f"{100 * sum(base) / len(base):.0f}% de acierto (IC 95% {100 * lo:.0f}–{100 * hi:.0f}%, n = {len(base)}). "
              "Si el agente no la supera, las noticias no están aportando nada.", ""]
    L += ["## Calibración (desde agosto)", "",
          "Si la confianza significa algo, el acierto debería subir con ella.", "",
          "| Confianza | n | Acierto |", "|---|--:|--:|"]
    for lo_, hi_ in ((0, 50), (50, 60), (60, 70), (70, 101)):
        s = clean[(clean["confianza"].astype(int) >= lo_) & (clean["confianza"].astype(int) < hi_)]
        acc = f"{100 * s['acierto'].astype(int).mean():.0f}%" if len(s) else "—"
        L.append(f"| {lo_}–{min(hi_, 100) - (0 if hi_ > 100 else 1)} | {len(s)} | {acc} |")
    by_t = clean.groupby("ticker").agg(n=("acierto", "size"), acierto=("acierto", lambda x: x.astype(int).mean()))
    L += ["", "## Por activo (desde agosto, n ≥ 3)", "", "| Activo | n | Acierto |", "|---|--:|--:|"]
    for t, r in by_t[by_t["n"] >= 3].sort_values("n", ascending=False).iterrows():
        L.append(f"| {t} | {int(r['n'])} | {100 * r['acierto']:.0f}% |")
    st = ledger.stats(book)
    L += ["", "## Notas",
          f"- Registradas {st['registradas']}, cerradas {st['cerradas']}, aún abiertas {st['abiertas']}.",
          f"- Días con decisión \"no operar hoy\": {no_trade} de {len(days)}.",
          "- Cada análisis por día y todas las hipótesis: `data/agent_bt/`.",
          "- Fase de fiabilidad (bitácora): <30 cerradas, rodaje; 30-99, indicativa; 100-299, útil; ≥300 y dos regímenes, fiable.",
          "- Varias hipótesis del mismo día comparten contexto: el n efectivo es menor y los IC algo optimistas.", ""]
    os.makedirs("reports", exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default="2026-07-01")
    ap.add_argument("--hasta", default=None)
    ap.add_argument("--solo-noticias", action="store_true")
    a = ap.parse_args()
    hasta = dt.date.fromisoformat(a.hasta) if a.hasta else dt.date.today() - dt.timedelta(days=1)
    run(dt.date.fromisoformat(a.desde), hasta, a.solo_noticias)
