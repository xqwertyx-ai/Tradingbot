"""Genera la portada (README.md + web + gráficas + registro de hipótesis).

Uso: python scripts/portada.py --evento auto|manual|<id>
Seis revisiones al día (dashboard/sesiones.py): apertura y cierre de Asia, Europa y EE. UU.
- usa-cierre: decisiones con precios de cierre (registra hipótesis) + resumen del día.
- el resto: solo observación, con un resumen de lo que ha cambiado.
- auto: la revisión pendiente según la hora (si no hay ninguna, no hace nada).
- manual: regenera la portada sin añadir una revisión al día.
"""
import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import analysis, charts, ledger, news, prices, sesiones, site  # noqa: E402
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


def resolve(evento: str, now: dt.datetime) -> str | None:
    if evento == "auto":
        hechos = {e["id"] for e in sesiones.cargar(sesiones.dia(now))}
        return sesiones.pendiente(now, hechos)
    return evento


def main(evento: str) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    evento = resolve(evento, now)
    if evento is None:
        print("No hay ninguna revisión pendiente a esta hora.")
        return
    mode = effective_mode("cierre", now) if evento == "usa-cierre" else sesiones.ETIQUETA.get(evento, "actualización")
    if mode == "intradía":  # cierre pedido con Wall Street abierto: no cuenta como revisión del día
        evento = "manual"
    final = evento == "usa-cierre"
    hoy = sesiones.dia(now)
    previos = [e for e in sesiones.cargar(hoy) if e["id"] != evento]
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
    # Fecha de la sesión de referencia = último cierre del S&P 500 (no la del reloj): una revisión
    # lanzada de madrugada decide sobre el cierre de ayer y así se evalúa desde el día siguiente.
    session = next((r["date"] for r in rows if r["ticker"] == "^GSPC"), now.date().isoformat())
    ai = analysis.analyze(session, mode, table, items, open_h, previos, final)
    if ai and not ai.get("error") and mode == "cierre":
        refs = {r["ticker"]: r["last"] for r in rows}
        book = ledger.add(book, ai["hipotesis"], session, refs)
    ledger.save(book)
    registradas = None
    if mode != "cierre" and len(book):
        ult = book["fecha"].max()
        registradas = {"fecha": ult, "hipotesis": [
            {"ticker": h.ticker, "direccion": h.direccion, "tesis": h.tesis,
             "horizonte_dias": int(h.horizonte_dias), "objetivo_pct": float(h.objetivo_pct),
             "invalidacion_pct": float(h.invalidacion_pct), "confianza": int(h.confianza),
             "ev_pct": float(h.ev_pct), "operable": bool(h.operada), "contra": "", "sesgos": ""}
            for h in book[book["fecha"] == ult].itertuples()]}

    panels = [{"name": r["name"], "df": series[r["ticker"]], "trend": r["trend"],
               "chg_1m": r["chg_1m"], "level": r["level"]} for r in rows if r["key"]]
    closed = book[book["estado"].isin(["ACIERTO", "FALLO", "EXPIRADA"])]
    made = charts.render_all(rows, panels, closed)

    entradas = previos
    if evento in sesiones.ETIQUETA:
        ok = ai and not ai.get("error")
        entrada = {"id": evento, "etiqueta": sesiones.ETIQUETA[evento], "hora": now.isoformat(timespec="seconds"),
                   "hora_madrid": now.astimezone(sesiones.MAD).strftime("%H:%M"),
                   "clima": ai.get("clima") if ok else None,
                   "resumen": ai.get("resumen") if ok else None,
                   "titulares": [items[n["id"]]["title"] for n in (ai.get("noticias") or [])[:3]] if ok else [],
                   "coste_usd": (ai.get("uso") or {}).get("coste_usd") if ok else None}
        if final and ok and ai.get("resumen_dia"):
            entrada["resumen_dia"] = ai["resumen_dia"]
        entradas = sesiones.registrar(hoy, entrada)

    pead_state = None
    if os.path.exists("data/pead/vivo-estado.json"):
        with open("data/pead/vivo-estado.json", encoding="utf-8") as f:
            pead_state = json.load(f)
    etiqueta = "cierre EE. UU." if mode == "cierre" else mode
    ctx = {"now": now, "mode": mode, "etiqueta": etiqueta, "dia": entradas, "registradas": registradas, "pead": pead_state, "rows": rows, "news": items, "feeds": feeds, "ai": ai,
           "names": {r["ticker"]: r["name"] for r in rows}, "stats": ledger.stats(book),
           "charts": made,
           "quality": {"ok": quality["ok"], "sin_contraste": quality["sin_contraste"],
                       "dudoso": quality["dudoso"], "sin_dato": quality["sin_dato"],
                       "fuentes": dict(fuentes)}}
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(render(ctx))
    site.build(ctx, series)

    os.makedirs("data/dashboard", exist_ok=True)
    snap = {"generado": now.isoformat(), "modo": mode, "evento": evento, "activos": rows, "titulares": items,
            "analisis": ai, "calidad": ctx["quality"]}
    with open("data/dashboard/ultimo.json", "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1, default=str)
    print("Portada generada.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--evento", default="auto", choices=["auto", "manual", *sesiones.ETIQUETA])
    ap.add_argument("--modo", choices=["cierre", "apertura"], help="compatibilidad: cierre = usa-cierre, apertura = manual")
    a = ap.parse_args()
    main({"cierre": "usa-cierre", "apertura": "manual"}.get(a.modo, a.evento))
