"""Genera la portada diaria (README.md + gráficas + registro de hipótesis).

Uso: python scripts/portada.py --modo cierre|apertura
- cierre: decisiones con precios de cierre (registra hipótesis nuevas).
- apertura: solo observación.
"""
import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import analysis, charts, ledger, news, prices, site  # noqa: E402
from dashboard.indicators import crossed_ma, metrics, nan_to_none  # noqa: E402
from dashboard.render import render  # noqa: E402
from dashboard.universe import ASSETS  # noqa: E402


def effective_mode(mode: str, now: dt.datetime) -> str:
    """Regla R-1014-3: solo se decide con precios de cierre. Si se pide 'cierre'
    con Wall Street todavía abierto, la revisión pasa a ser de observación."""
    ny = now.astimezone(ZoneInfo("America/New_York"))
    if mode == "cierre" and ny.weekday() < 5 and dt.time(9, 30) <= ny.time() < dt.time(16, 15):
        return "intradía"
    return mode


def main(mode: str) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    mode = effective_mode(mode, now)
    series, rows, quality, fuentes = {}, [], Counter(), Counter()

    print("Precios...")
    prices.prefetch_yfinance([a["yahoo"] for a in ASSETS])
    for a in ASSETS:
        df, src = prices.fetch(a)
        if df is None:
            quality["sin_dato"] += 1
            continue
        fuentes[src] += 1
        q = prices.check_source(a, df, src)
        quality[q.replace(" ", "_")] += 1
        series[a["yahoo"]] = df
        m = metrics(df, level=a.get("level", False))
        cross = crossed_ma(df)
        if cross:
            m["flags"].append(cross)
        rows.append({"ticker": a["yahoo"], "name": a["name"], "group": a["group"], "key": a["key"],
                     "level": a.get("level", False), "fuente": src, "calidad": q,
                     **{k: nan_to_none(v) for k, v in m.items()}})
    print(f"  {len(rows)}/{len(ASSETS)} activos con datos")
    if not rows:
        sys.exit("Ninguna fuente de precios respondió.")

    print("Titulares...")
    items, feeds = news.fetch_news()
    print(f"  {len(items)} titulares; {feeds}")

    book = ledger.load()
    book = ledger.evaluate(book, series)
    open_h = book[book["estado"] == "ABIERTA"][["ticker", "direccion", "vence", "tesis"]].to_dict("records")

    print("Análisis...")
    table = [{"ticker": r["ticker"], "name": r["name"], "level": r["level"], "m": r} for r in rows]
    ai = analysis.analyze(now.date().isoformat(), mode, table, items, open_h)
    if ai and not ai.get("error") and mode == "cierre":
        refs = {r["ticker"]: r["last"] for r in rows}
        book = ledger.add(book, ai["hipotesis"], now.date().isoformat(), refs)
    ledger.save(book)

    panels = [{"name": r["name"], "df": series[r["ticker"]], "trend": r["trend"],
               "chg_1m": r["chg_1m"], "level": r["level"]} for r in rows if r["key"]]
    closed = book[book["estado"].isin(["FALLO", "EXPIRADA"])]
    made = charts.render_all(rows, panels, closed)

    ctx = {"now": now, "mode": mode, "rows": rows, "news": items, "feeds": feeds, "ai": ai,
           "names": {r["ticker"]: r["name"] for r in rows}, "stats": ledger.stats(book),
           "charts": made,
           "quality": {"ok": quality["ok"], "sin_contraste": quality["sin_contraste"],
                       "dudoso": quality["dudoso"], "sin_dato": quality["sin_dato"],
                       "fuentes": dict(fuentes)}}
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(render(ctx))
    site.build(ctx, series)

    os.makedirs("data/dashboard", exist_ok=True)
    snap = {"generado": now.isoformat(), "modo": mode, "activos": rows, "titulares": items,
            "analisis": ai, "calidad": ctx["quality"]}
    with open("data/dashboard/ultimo.json", "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1, default=str)
    print("Portada generada.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["cierre", "apertura"], default="cierre")
    main(ap.parse_args().modo)
