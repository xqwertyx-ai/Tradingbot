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

VER = analysis.ALGO_VERSION
OUT = f"data/agent_bt/{VER}"
LEDGER = f"{OUT}/hipotesis.csv"
REPORT = f"reports/agente-backtest-{VER}.md"
CLEAN_FROM = dt.date(2026, 8, 1)


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
                              version=f"bt-{VER}")
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


CLOSED = ["ACIERTO", "FALLO", "EXPIRADA"]
TARGET_NET = 0.01  # objetivo del proyecto: ≥ 1% neto por operación


def momentum_baseline(book, series):
    """Mismas fechas, activos, objetivos, stops y plazos; dirección = signo del último mes."""
    rows = []
    for _, h in book[book["estado"].isin(CLOSED)].iterrows():
        df = series[h["ticker"]]
        d = df[pd.to_datetime(df["date"]) <= pd.Timestamp(h["fecha"])]["close"]
        if len(d) < 22:
            continue
        fake = h.copy()
        fake["direccion"] = "alcista" if d.iloc[-1] >= d.iloc[-22] else "bajista"
        fake["estado"] = "ABIERTA"
        ev = ledger.evaluate(pd.DataFrame([fake]), {h["ticker"]: df})
        if ev.iloc[0]["estado"] != "ABIERTA":
            rows.append(ev.iloc[0])
    return pd.DataFrame(rows)


def line(label, sub):
    n = len(sub)
    if not n:
        return f"| {label} | 0 | — | — | — | — |"
    k = int(sub["acierto"].astype(int).sum())
    lo, hi = wilson(k, n)
    net = ledger.net_returns(sub)
    se = net.std(ddof=1) / math.sqrt(n) if n > 1 else math.nan
    gains, losses = net[net > 0].sum(), -net[net < 0].sum()
    pf = f"{gains / losses:.2f}" if losses > 0 else "∞"
    return (f"| {label} | {n} | {100 * k / n:.0f}% ({100 * lo:.0f}–{100 * hi:.0f}%) "
            f"| {100 * net.mean():+.2f}% (±{196 * se:.2f}) | {pf} | {100 * (sub['estado'] == 'ACIERTO').mean():.0f}% |")


def report(book, series, days, cost):
    closed = book[book["estado"].isin(CLOSED)].copy()
    closed["fecha_d"] = pd.to_datetime(closed["fecha"]).dt.date
    clean = closed[closed["fecha_d"] >= CLEAN_FROM]
    july = closed[closed["fecha_d"] < CLEAN_FROM]
    ops = clean[clean["operada"].astype(int) == 1]
    base = momentum_baseline(book[pd.to_datetime(book["fecha"]).dt.date >= CLEAN_FROM], series)
    base_ops = base[base["operada"].astype(int) == 1] if len(base) else base
    decisions = [json.load(open(f"{OUT}/ai/{d}.json", encoding="utf-8")).get("decision")
                 for d in days if os.path.exists(f"{OUT}/ai/{d}.json")]
    head = ("| Grupo | n | Acierto (IC 95%) | Retorno neto medio (±IC 95%) | Factor de beneficio | Objetivo tocado |\n"
            "|---|--:|--:|--:|--:|--:|")
    L = [f"# Backtest del agente de noticias ({VER})", "",
         f"Generado: {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC · modelo {analysis.MODEL} · "
         f"coste total de la API ≈ {cost:.2f} USD. Simulación; no es asesoramiento financiero.", "",
         "## Cómo se hizo",
         f"- {len(days)} sesiones, de {days[0]} a {days[-1]}. Cada día, el mismo análisis de cierre que la web, "
         "solo con titulares publicados antes del cierre de Wall Street y precios hasta ese día.",
         "- Cada hipótesis es un plan: objetivo, stop y plazo, todo con precios de cierre. ACIERTO si toca el "
         "objetivo antes que el stop; FALLO si toca el stop; al vencer, EXPIRADA puntuada por el signo.",
         f"- Se opera (en simulación) si el valor esperado neto ≥ {analysis.MIN_EV_PCT:.0f}% y la probabilidad "
         f"≥ {analysis.MIN_PROB}. El resto se registra para medir la calibración.",
         "- Retorno neto: menos el coste de ida y vuelta (0,10% acciones/índices, 0,06% futuros, "
         "0,04% divisas, 0,20% cripto). Factor de beneficio = ganancias netas / pérdidas netas.",
         f"- **Lo que cuenta es desde el {CLEAN_FROM:%d-%m-%Y}.** El conocimiento fiable del modelo llega a junio "
         "de 2026; julio se muestra aparte por si supiera algo de esas semanas.", "",
         f"## Resultado frente al objetivo (≥ {100 * TARGET_NET:.0f}% neto por operación)", ""]
    if len(ops):
        m = ledger.net_returns(ops).mean()
        verdict = "lo **cumple**" if m >= TARGET_NET else "**no** lo cumple"
        L.append(f"Operadas desde agosto: {len(ops)}, retorno neto medio {100 * m:+.2f}% → {verdict}"
                 + (" (con n < 30 no es concluyente)." if len(ops) < 30 else "."))
    else:
        L.append("Ninguna hipótesis pasó el filtro para operarse desde agosto.")
    L += ["", "## Resultados (hipótesis cerradas)", "", head,
          line("Desde agosto · operadas", ops),
          line("Desde agosto · todas", clean),
          line("Desde agosto · no operadas", clean[clean["operada"].astype(int) == 0]),
          line("Julio (posible contaminación) · todas", july), ""]
    if len(base):
        L += ["**Referencia ingenua** (mismas fechas, activos, objetivos, stops y plazos; dirección = tendencia del "
              "último mes). Si el agente no la supera, las noticias no aportan nada.", "", head,
              line("Referencia · mismas que las operadas", base_ops),
              line("Referencia · todas", base), ""]
    L += ["## Calibración (desde agosto)", "",
          "La probabilidad declarada debería parecerse a la frecuencia real con la que se toca el objetivo.", "",
          "| Probabilidad declarada | n | Media declarada | Objetivo tocado | Acierto (incl. expiradas) |",
          "|---|--:|--:|--:|--:|"]
    conf = clean["confianza"].astype(int)
    for lo_, hi_ in ((0, 45), (45, 55), (55, 65), (65, 101)):
        s_ = clean[(conf >= lo_) & (conf < hi_)]
        if len(s_):
            L.append(f"| {lo_}–{min(hi_ - 1, 100)} | {len(s_)} | {s_['confianza'].astype(int).mean():.0f}% "
                     f"| {100 * (s_['estado'] == 'ACIERTO').mean():.0f}% | {100 * s_['acierto'].astype(int).mean():.0f}% |")
        else:
            L.append(f"| {lo_}–{min(hi_ - 1, 100)} | 0 | — | — | — |")
    if "objetivo_pct" in clean and clean["objetivo_pct"].notna().any():
        L += ["", f"Objetivo medio {clean['objetivo_pct'].astype(float).mean():.1f}% · stop medio "
              f"{clean['invalidacion_pct'].astype(float).mean():.1f}% · EV previsto medio de las operadas "
              f"{ops['ev_pct'].astype(float).mean() if len(ops) else float('nan'):.2f}%."]
    by_t = clean.assign(net=ledger.net_returns(clean)).groupby("ticker").agg(
        n=("acierto", "size"), acierto=("acierto", lambda x: x.astype(int).mean()), net=("net", "mean"))
    L += ["", "## Por activo (desde agosto, n ≥ 3)", "", "| Activo | n | Acierto | Neto medio |", "|---|--:|--:|--:|"]
    for t, r in by_t[by_t["n"] >= 3].sort_values("n", ascending=False).iterrows():
        L.append(f"| {t} | {int(r['n'])} | {100 * r['acierto']:.0f}% | {100 * r['net']:+.2f}% |")
    st = ledger.stats(book)
    L += ["", "## Notas",
          f"- Registradas {st['registradas']}, cerradas {st['cerradas']}, aún abiertas {st['abiertas']}.",
          f"- Días con decisión \"operar\": {decisions.count('operar')} de {len(decisions)} analizados.",
          "- Cada análisis por día y todas las hipótesis: `data/agent_bt/`.",
          "- Fase de fiabilidad (bitácora): <30 cerradas, rodaje; 30-99, indicativa; 100-299, útil; ≥300 y dos regímenes, fiable.",
          "- Varias hipótesis del mismo día comparten contexto: el n efectivo es menor y los IC algo optimistas.",
          "- Este periodo ya se usó para evaluar versiones anteriores: una mejora aquí es una pista, no una prueba. "
          "La prueba es el test en vivo.", ""]
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
