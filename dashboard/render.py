"""Genera README.md: la portada del repo."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from dashboard.sesiones import agenda

MAD = ZoneInfo("Europe/Madrid")
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
TREND = {"alcista": "↗️ alcista", "bajista": "↘️ bajista", "lateral": "➡️ lateral", "sin datos": "—"}
CLIMA = {"risk-on": "🟢 risk-on (apetito por riesgo)", "risk-off": "🔴 risk-off (aversión al riesgo)",
         "mixto": "🟡 mixto"}


def _chg(x, level=False):
    if x is None:
        return "—"
    if level:
        return f"{'▲' if x >= 0 else '▼'} {100 * x:+.0f} pb"
    return f"{'🔵▲' if x >= 0 else '🔴▼'} {100 * x:+.1f}%"


def _price(x):
    if x is None:
        return "—"
    if x >= 1000:
        return f"{x:,.0f}".replace(",", ".")
    return f"{x:.4g}" if x < 10 else f"{x:,.2f}"


def _pic(name, alt):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.png">'
            f'<img alt="{alt}" src="assets/{name}-light.png" width="100%"></picture>')


def _hora(iso):
    if not iso:
        return ""
    d = dt.datetime.fromisoformat(iso).astimezone(MAD)
    return d.strftime("%d/%m %H:%M")


def render(ctx: dict) -> str:
    now = ctx["now"].astimezone(MAD)
    ai = ctx.get("ai") or {}
    rows = ctx["rows"]
    news = ctx["news"]
    L = [
        '<div align="center">',
        "",
        "# 📊 Radar de mercados",
        "",
        f"**{DIAS[now.weekday()]} {now.day} {MESES[now.month - 1]} {now.year} · "
        f"revisión de {ctx.get('etiqueta', ctx['mode'])} · {now:%H:%M} (Madrid)**",
        "",
        "<sub>Proyecto de I+D · simulación (paper trading) · no es asesoramiento financiero</sub>",
        "",
        "</div>",
        "",
    ]

    # --- Titular del día
    if ai and not ai.get("error"):
        L += [f"> **Clima:** {CLIMA.get(ai.get('clima'), ai.get('clima', '—'))}  ",
              f"> {ai.get('resumen', '')}  ",
              f"> **Decisión:** {ai.get('decision', '—')} — {ai.get('decision_motivo', '')}", ""]
    else:
        msg = ai.get("error") if ai else "Análisis con IA desactivado (falta el secret `ANTHROPIC_API_KEY`)."
        L += [f"> ⚙️ {msg} Se muestran solo datos y señales por reglas.", ""]

    # --- Fichas clave
    L += ["| Activo | Último | Día | 1 mes | Tendencia |", "|---|--:|--:|--:|---|"]
    for r in rows:
        if r["key"]:
            dud = " ⚠️" if r["calidad"] == "dudoso" else ""
            L.append(f"| **{r['name']}**{dud} | {_price(r['last'])} | {_chg(r['chg_1d'], r.get('level'))} "
                     f"| {_chg(r['chg_1m'], r.get('level'))} | {TREND.get(r['trend'], r['trend'])} |")
    L += ["", _pic("mapa", "Cambio del día por activo"), ""]

    # --- Hoy, sesión a sesión
    if ctx["now"].astimezone(MAD).weekday() < 5:
        L += dia_section(ctx.get("dia") or [], ctx["now"])

    # --- Noticias
    L += ["## 📰 Noticias clave", ""]
    if ai.get("noticias"):
        for n in sorted(ai["noticias"], key=lambda n: -int(n.get("importancia", 0) or 0)):
            it = news[n["id"]]
            stars = "●" * int(n.get("importancia", 1) or 1)
            rumor = " · ⚠️ rumor" if n.get("rumor") else ""
            L += [f"- **[{n.get('categoria', it['category'])}]** [{it['title']}]({it['link']}) "
                  f"<sub>{it['source']} · {_hora(it['published'])} · {stars}{rumor}</sub>  ",
                  f"  {n.get('novedad', '')} **Impacto:** {n.get('impacto', '')}"]
        if ai.get("divergencias"):
            L += ["", "**Divergencias precio-noticia:** " + " · ".join(ai["divergencias"])]
    else:
        for it in news[:8]:
            L.append(f"- **[{it['category']}]** [{it['title']}]({it['link']}) "
                     f"<sub>{it['source']} · {_hora(it['published'])}</sub>")
    if not news:
        L.append("_No se pudieron descargar titulares en esta ejecución._")
    L.append("")

    # --- Hipótesis
    L += ["## 🎯 Hipótesis de hoy", ""]
    hyps = ai.get("hipotesis") or []
    reg = ctx.get("registradas")
    if ctx["mode"] != "cierre":
        hyps = reg["hipotesis"] if reg else []
        L.append(f"_Revisión de {ctx.get('etiqueta', ctx['mode'])}: solo observación. Las hipótesis se registran "
                 "con precios de cierre de EE. UU."
                 + (f" Estas son las registradas en el cierre del {reg['fecha']}._" if hyps else "_"))
        if hyps:
            L.append("")
    elif not ai or ai.get("error"):
        L.append("_Sin análisis con IA no se generan hipótesis._")
    elif not hyps:
        L.append("_Ninguna oportunidad supera los filtros: **no operar hoy**._")
    if hyps and (ctx["mode"] != "cierre" or (ai and not ai.get("error"))):
        L += ["| Activo | Idea | Plazo | Objetivo / stop | Prob. | EV neto |", "|---|---|--:|--:|--:|--:|"]
        for h in hyps:
            arrow = "🔵▲" if h["direccion"] == "alcista" else "🔴▼"
            op = " ✅" if h.get("operable") else " 👀"
            obj = f"+{h['objetivo_pct']:.1f}% / −{h['invalidacion_pct']:.1f}%" if h.get("objetivo_pct") else f"— / −{h['invalidacion_pct']:.1f}%"
            ev = f"{h['ev_pct']:+.1f}%{op}" if h.get("ev_pct") is not None else op
            L.append(f"| {arrow} **{ctx['names'].get(h['ticker'], h['ticker'])}** | {h.get('tesis', '')} "
                     f"| {h['horizonte_dias']} ses. | {obj} | {h['confianza']}% | {ev} |")
        contra = [h for h in hyps if h.get("contra")]
        if contra:
            L += ["", "<details><summary>Argumentos en contra</summary>", ""]
            for h in contra:
                L += [f"- **{ctx['names'].get(h['ticker'], h['ticker'])}** · {h['contra']} Sesgos: {h.get('sesgos', '')}"]
            L += ["", "</details>"]
        L += ["", "<sub>Prob.: probabilidad de tocar el objetivo antes que el stop · EV: valor esperado "
              "neto de costes · ✅ se opera en simulación (EV ≥ 1% y prob. ≥ 55%) · 👀 solo se mide</sub>"]
    L.append("")

    # --- Vigilar
    L += ["## 👀 Valores a vigilar", ""]
    start = len(L)
    seen = set()
    for v in ai.get("vigilar") or []:
        seen.add(v["ticker"])
        L.append(f"- **{ctx['names'].get(v['ticker'], v['ticker'])}** — {v['motivo']}")
    for r in rows:
        if r["flags"] and r["ticker"] not in seen:
            L.append(f"- **{r['name']}** — {', '.join(r['flags'])}")
    if len(L) == start:
        L.append("_Nada destacable por reglas hoy._")
    L.append("")

    # --- Test en vivo PEAD
    L += pead_section(ctx.get("pead"))

    # --- Tendencias
    L += ["## 📈 Tendencias (6 meses)", "", _pic("tendencias", "Tendencias de activos clave"), "",
          "<details><summary>Todos los activos</summary>", "",
          "| Activo | Último | Día | Semana | 1 mes | 3 meses | RSI | Tendencia | Señales |",
          "|---|--:|--:|--:|--:|--:|--:|---|---|"]
    for r in rows:
        lv = r.get("level")
        rsi = "—" if r["rsi14"] is None else f"{r['rsi14']:.0f}"
        L.append(f"| {r['name']} | {_price(r['last'])} | {_chg(r['chg_1d'], lv)} | {_chg(r['chg_5d'], lv)} "
                 f"| {_chg(r['chg_1m'], lv)} | {_chg(r['chg_3m'], lv)} | {rsi} | {TREND.get(r['trend'], r['trend'])} "
                 f"| {', '.join(r['flags']) or '—'} |")
    L += ["", "</details>", ""]

    # --- Historial
    st = ctx["stats"]
    L += ["## ✅ Historial de hipótesis", ""]
    L.append(f"Registradas: **{st['registradas']}** · abiertas: **{st['abiertas']}** · cerradas: **{st['cerradas']}**")
    for label in ("todas", "operadas"):
        s = st.get(label)
        if s:
            L.append(f"- Acierto ({label}): **{100 * s['acierto']:.0f}%** "
                     f"(IC 95%: {100 * s['lo']:.0f}–{100 * s['hi']:.0f}%, n = {s['n']}) · "
                     f"retorno neto medio {100 * s.get('ret_neto_medio', s['ret_medio']):+.2f}%")
    if st["cerradas"] < 30:
        L.append("\n<sub>Fase 0 (rodaje): con menos de 30 hipótesis cerradas el acierto no es estadísticamente "
                 "informativo.</sub>")
    if ctx["charts"].get("historial"):
        L += ["", _pic("historial", "Acierto acumulado")]
    L += ["", "Registro completo: [`data/dashboard/hipotesis.csv`](data/dashboard/hipotesis.csv)", ""]

    # --- Pie
    q = ctx["quality"]
    L += ["---", "",
          "<details><summary>Fuentes y calidad de datos</summary>", "",
          f"- Precios: {q['ok']} contrastados, {q['sin_contraste']} sin segunda fuente, "
          f"{q['dudoso']} dudosos (⚠️, difieren > 0,5%), {q['sin_dato']} sin dato.",
          f"- Fuentes de precio usadas: {', '.join(f'{k} ({v})' for k, v in q['fuentes'].items())}.",
          "- Titulares: " + "; ".join(f"{k}: {v}" for k, v in ctx["feeds"].items()) + ".",
          f"- Análisis: {ai.get('modelo', 'desactivado') if ai else 'desactivado'}.",
          "- Reglas de tendencia: alcista si el precio está sobre sus medias de 50 y 200 sesiones y sube en el mes; "
          "bajista al revés; si no, lateral.",
          "", "</details>", "",
          "Más: [experimento Polymarket 5 min](docs/experimento-polymarket.md) · "
          "[informe del backtest](reports/informe.md)", ""]
    return "\n".join(L)


ICONO_CLIMA = {"risk-on": "🟢", "risk-off": "🔴", "mixto": "🟡"}


def dia_section(entradas: list[dict], now) -> list[str]:
    """Las seis revisiones del día en orden (apertura y cierre de Asia, Europa y EE. UU.) con su resumen."""
    L = ["## 🕒 Hoy, sesión a sesión", ""]
    final = next((e["resumen_dia"] for e in entradas if e.get("resumen_dia")), None)
    if final:
        L += [f"> **Resumen del día:** {final}", ""]
    for a in agenda(now, entradas):
        e = a["entrada"]
        if e:
            L.append(f"- **{e['hora_madrid']} · {a['etiqueta']}** {ICONO_CLIMA.get(e.get('clima'), '')} "
                     f"{e.get('resumen') or '_sin análisis con IA_'}")
        else:
            nota = "no se hizo" if a["estado"] == "perdida" else f"prevista ~{a['prevista']}"
            L.append(f"- <sub>{a['etiqueta']} · {nota}</sub>")
    L.append("")
    return L


def pead_section(st: dict | None) -> list[str]:
    """Test en vivo de la regla de deriva tras resultados (reports/pead.md)."""
    if not st:
        return []
    r = st.get("resumen", {})
    L = ["## 🧪 Test en vivo: deriva tras resultados", "",
         f"Regla congelada desde el {st['inicio']}: comprar al cierre del día siguiente a una reacción a resultados "
         "entre el 10% mejor y vender 40 sesiones después. Objetivo: ≥ 1% neto por operación. "
         "[Por qué esta regla](reports/pead.md)", ""]
    if r.get("cerradas"):
        L.append(f"**Cerradas: {r['cerradas']}** · neto medio {100 * r['neto_medio']:+.2f}% "
                 f"(±{100 * r['ic']:.2f}) · aciertos {100 * r['acierto']:.0f}% · frente a SPY {100 * r['frente_spy']:+.2f}%")
    else:
        L.append(f"Aún sin operaciones cerradas (cada una dura unos 2 meses). Abiertas: {r.get('abiertas', 0)}.")
    if st.get("pendientes"):
        L += ["", "**Se compran en la próxima sesión:** " + ", ".join(
            f"{p['ticker']} (reacción {100 * p['ra']:+.1f}%)" for p in st["pendientes"])]
    if st.get("abiertas"):
        L += ["", "| Empresa | Entrada | Sesiones | Resultado | SPY mismo periodo |", "|---|---|--:|--:|--:|"]
        for p in sorted(st["abiertas"], key=lambda p: p["entrada"], reverse=True):
            L.append(f"| {p['ticker']} | {p['entrada']} | {p['sesiones']}/40 | {100 * p['ret']:+.1f}% | {100 * p['spy']:+.1f}% |")
    L.append("")
    return L
