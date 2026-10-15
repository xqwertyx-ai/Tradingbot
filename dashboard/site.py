"""Web de la portada (GitHub Pages): site/index.html, un único archivo autocontenido.

Diseño: un "termómetro del día" (todos los activos como puntos sobre el eje del
cambio diario) como pieza central; el resto, sobrio y legible en móvil.
Sube = azul, baja = rojo; el signo va siempre escrito, nunca solo en color.
"""
from __future__ import annotations

import html
import json
import os
from zoneinfo import ZoneInfo

from .render import DIAS, MESES, _hora, _price

MAD = ZoneInfo("Europe/Madrid")
E = html.escape


def _pct(x, level=False, digits=1):
    if x is None:
        return "—"
    return f"{100 * x:+.0f} pb" if level else f"{100 * x:+.{digits}f}%".replace(".", ",")


def _cls(x):
    return "" if x is None else ("up" if x >= 0 else "down")


def _num(x):
    return _price(x).replace(".", "§").replace(",", ".").replace("§", ",") if x is not None else "—"


def sparkline(closes: list[float], w=160, h=44, ma: list | None = None) -> str:
    if len(closes) < 2:
        return ""
    lo, hi = min(closes), max(closes)
    span = (hi - lo) or 1
    pts = [(i * w / (len(closes) - 1), h - 3 - (c - lo) / span * (h - 6)) for i, c in enumerate(closes)]
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    ma_path = ""
    if ma:
        mp = [(i * w / (len(ma) - 1), h - 3 - (c - lo) / span * (h - 6)) for i, c in enumerate(ma) if c is not None]
        if len(mp) > 1:
            ma_path = f'<path class="ma" d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in mp)}"/>'
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">'
            f'{ma_path}<path class="ln" d="{d}"/></svg>')


def thermometer(rows: list[dict]) -> str:
    """Beeswarm horizontal del cambio diario. Posiciones calculadas aquí, sin JS."""
    pts = [r for r in rows if r["chg_1d"] is not None and not r.get("level")]
    if not pts:
        return ""
    lim = max(0.01, min(0.06, max(abs(r["chg_1d"]) for r in pts) * 1.1))
    W, R = 1000, 9
    placed = []
    for r in sorted(pts, key=lambda r: abs(r["chg_1d"])):
        x = 40 + (max(-lim, min(lim, r["chg_1d"])) + lim) / (2 * lim) * (W - 80)
        lane = 0
        while any(abs(px - x) < 2 * R + 2 and pl == lane for px, pl, _ in placed):
            lane = -lane + (1 if lane <= 0 else 0)  # 0, 1, -1, 2, -2...
        placed.append((x, lane, r))
    lanes = [pl for _, pl, _ in placed]
    top, bot = max(lanes), min(lanes)
    H = (top - bot + 1) * (2 * R + 2) + 70
    mid = 30 + top * (2 * R + 2) + R
    out = [f'<svg class="thermo" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Cambio del día de {len(pts)} activos">',
           f'<line class="axis" x1="40" x2="{W - 40}" y1="{H - 26}" y2="{H - 26}"/>']
    for v in (-lim, -lim / 2, 0, lim / 2, lim):
        x = 40 + (v + lim) / (2 * lim) * (W - 80)
        out.append(f'<line class="{"zero" if v == 0 else "tick"}" x1="{x:.0f}" x2="{x:.0f}" y1="14" y2="{H - 26}"/>'
                   f'<text class="tl" x="{x:.0f}" y="{H - 8}">{_pct(v, digits=1)}</text>')
    for x, lane, r in placed:
        y = mid - lane * (2 * R + 2)
        tip = f"{r['name']}: {_pct(r['chg_1d'])}"
        out.append(f'<g class="dot {_cls(r["chg_1d"])}" tabindex="0"><title>{E(tip)}</title>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R}"/>')
        out.append("</g>")
    out.append("</svg>")
    return "".join(out)


def movers(rows: list[dict]) -> str:
    pts = sorted([r for r in rows if r["chg_1d"] is not None and not r.get("level")], key=lambda r: r["chg_1d"])
    if len(pts) < 4:
        return ""
    def fmt(rs):
        return ", ".join(f'{E(r["name"])} <span class="{_cls(r["chg_1d"])}">{_pct(r["chg_1d"])}</span>'
                         for r in rs)
    return (f'<p class="movers"><b>Más suben:</b> {fmt(pts[::-1][:3])}<br>'
            f'<b>Más bajan:</b> {fmt(pts[:3])}</p>')


def pead_html(st) -> str:
    if not st:
        return ""
    r = st.get("resumen", {})
    if r.get("cerradas"):
        head = (f'<div class="stats"><div><b>{100 * r["neto_medio"]:+.2f}%</b><span>neto medio por operación '
                f'(±{100 * r["ic"]:.2f}, n={r["cerradas"]})</span></div><div><b>{100 * r["acierto"]:.0f}%</b>'
                f'<span>aciertos</span></div><div><b>{100 * r["frente_spy"]:+.2f}%</b><span>frente a SPY</span></div>'
                f'<div><b>{r.get("abiertas", 0)}</b><span>abiertas</span></div></div>')
    else:
        head = (f'<p class="empty">Aún sin operaciones cerradas: cada una dura unos 2 meses. '
                f'Abiertas: {r.get("abiertas", 0)}.</p>')
    pend = ""
    if st.get("pendientes"):
        pend = ('<p><b>Se compran en la próxima sesión:</b> ' + ", ".join(
            f'{E(p["ticker"])} ({_pct(p["ra"])})' for p in st["pendientes"]) + "</p>")
    rows = "".join(
        f'<tr><td>{E(p["ticker"])}</td><td>{p["entrada"]}</td><td>{p["sesiones"]}/40</td>'
        f'<td class="{_cls(p["ret"])}">{_pct(p["ret"], digits=1)}</td><td class="{_cls(p["spy"])}">{_pct(p["spy"], digits=1)}</td></tr>'
        for p in sorted(st.get("abiertas", []), key=lambda p: p["entrada"], reverse=True))
    table = ('<div class="scroll"><table><thead><tr><th>Empresa</th><th>Entrada</th><th>Sesiones</th>'
             f'<th>Resultado</th><th>SPY</th></tr></thead><tbody>{rows}</tbody></table></div>') if rows else ""
    return (f'<h2>Test en vivo: deriva tras resultados</h2>'
            f'<p class="note">Regla congelada desde el {st["inicio"]}: comprar al cierre del día siguiente a una reacción '
            'a resultados entre el 10% mejor y vender 40 sesiones después. Objetivo: ≥ 1% neto por operación. '
            '<a href="https://github.com/xqwertyx-ai/Tradingbot/blob/main/reports/pead.md">Por qué esta regla</a>.</p>'
            f'{head}{pend}{table}')


CSS = """
:root{--bg:#eef1ef;--paper:#f8faf8;--ink:#17202b;--ink2:#4d5965;--muted:#7d8791;--rule:#d5dbd8;
--up:#2a78d6;--down:#d63f3e;--upbg:#e3eefb;--downbg:#fbe6e5;--hl:#17202b}
@media (prefers-color-scheme:dark){:root{--bg:#10151b;--paper:#161d25;--ink:#e9eef2;--ink2:#b3bec8;
--muted:#7f8b96;--rule:#2a333d;--up:#4b93ea;--down:#ec6a69;--upbg:#16263a;--downbg:#3a1c1e;--hl:#e9eef2}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 "IBM Plex Sans",system-ui,sans-serif;
font-variant-numeric:tabular-nums}
a{color:inherit;text-decoration-color:var(--muted);text-underline-offset:3px}
a:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--up);outline-offset:2px}
.wrap{max-width:980px;margin:0 auto;padding:20px 16px 48px}
header{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
.brand{font:700 1.05rem/1 "Bricolage Grotesque",sans-serif;letter-spacing:-.01em}
.when{color:var(--ink2);font-size:.9rem}
.hero{margin:28px 0 8px}
.clima{font:800 clamp(2.4rem,9vw,4.6rem)/.95 "Bricolage Grotesque",sans-serif;letter-spacing:-.035em;margin:0}
.clima small{display:block;font:500 1rem/1.4 "IBM Plex Sans",sans-serif;letter-spacing:0;color:var(--ink2);margin-top:10px}
.summary{max-width:62ch;font-size:1.08rem;margin:14px 0 0}
.thermo{width:100%;height:auto;margin:22px 0 4px;overflow:visible}
.thermo .axis{stroke:var(--rule);stroke-width:2}.thermo .tick{stroke:var(--rule);stroke-dasharray:2 4}
.thermo .zero{stroke:var(--muted);stroke-width:1.5}
.thermo .tl{fill:var(--muted);font-size:20px;text-anchor:middle}
.thermo .dot circle{stroke:var(--paper);stroke-width:2}
.thermo .up circle{fill:var(--up)}.thermo .down circle{fill:var(--down)}
.thermo .dot:hover circle,.thermo .dot:focus circle{stroke:var(--ink);stroke-width:3}
.thermo .lab{fill:var(--ink);font-size:21px;font-weight:600}
.caption{color:var(--muted);font-size:.85rem;margin:0}
.movers{margin:10px 0 0;font-size:.95rem}.movers span{font-weight:600}
.decision{margin:26px 0 0;padding:14px 18px;border-left:4px solid var(--hl);background:var(--paper)}
.decision b{font-family:"Bricolage Grotesque",sans-serif;font-size:1.15rem}
h2{font:700 1.45rem/1.2 "Bricolage Grotesque",sans-serif;letter-spacing:-.015em;margin:44px 0 14px}
.tiles{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--rule);border:1px solid var(--rule)}
@media (min-width:720px){.tiles{grid-template-columns:repeat(4,1fr)}}
.tile{background:var(--paper);padding:12px 14px 10px;min-width:0}
.tile .n{font-size:.85rem;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile .p{font:700 1.35rem/1.2 "Bricolage Grotesque",sans-serif;letter-spacing:-.01em}
.tile .c{font-size:.9rem;font-weight:600}
.up{color:var(--up)}.down{color:var(--down)}
.spark{width:100%;height:40px;display:block;margin-top:6px}
.spark .ln{fill:none;stroke:var(--ink2);stroke-width:2;vector-effect:non-scaling-stroke}
.spark .ma{fill:none;stroke:var(--muted);stroke-width:1;stroke-dasharray:3 3;vector-effect:non-scaling-stroke}
.spark circle{fill:var(--ink)}
.tile .t{font-size:.78rem;color:var(--muted);margin-top:2px}
ol.news,ul.plain{list-style:none;margin:0;padding:0}
.news li{padding:14px 0;border-top:1px solid var(--rule)}
.news .meta{font-size:.82rem;color:var(--muted)}
.news .h{font-weight:600;font-size:1.02rem}
.news p{margin:4px 0 0;color:var(--ink2);max-width:70ch}
.cat{display:inline-block;font-size:.75rem;font-weight:600;padding:1px 8px;border-radius:999px;
background:var(--paper);border:1px solid var(--rule);margin-right:6px;color:var(--ink2)}
.imp{letter-spacing:2px;color:var(--ink)}
.hyp{display:grid;gap:12px}
.h-card{background:var(--paper);padding:14px 16px;border-top:3px solid var(--rule)}
.h-card.alcista{border-top-color:var(--up)}.h-card.bajista{border-top-color:var(--down)}
.h-top{display:flex;justify-content:space-between;gap:10px;align-items:baseline;flex-wrap:wrap}
.h-top b{font-family:"Bricolage Grotesque",sans-serif;font-size:1.15rem}
.conf{font-weight:700}.conf small{font-weight:400;color:var(--muted)}
.h-card p{margin:6px 0 0;max-width:70ch}.h-card .against{color:var(--ink2);font-size:.92rem}
.empty{color:var(--ink2);font-style:italic}
.watch li{padding:8px 0;border-top:1px solid var(--rule)}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{font-weight:600;color:var(--ink2);text-align:right;padding:8px 6px;border-bottom:2px solid var(--rule)}
td{text-align:right;padding:7px 6px;border-bottom:1px solid var(--rule);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
td.flags{text-align:left;white-space:normal;color:var(--ink2);font-size:.82rem;min-width:180px}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.stats{display:flex;gap:28px;flex-wrap:wrap}
.stats div b{display:block;font:800 1.9rem/1.1 "Bricolage Grotesque",sans-serif}
.stats div span{color:var(--ink2);font-size:.88rem}
.note{color:var(--muted);font-size:.85rem;max-width:70ch}
footer{margin-top:48px;padding-top:16px;border-top:1px solid var(--rule);color:var(--muted);font-size:.82rem}
footer p{margin:4px 0;max-width:80ch}
@media (prefers-reduced-motion:no-preference){.thermo .dot circle{transition:stroke-width .15s}}
"""


def build(ctx: dict, series: dict, out_dir: str = "site") -> str:
    now = ctx["now"].astimezone(MAD)
    ai = ctx.get("ai") or {}
    ok_ai = ai and not ai.get("error")
    rows, news, names = ctx["rows"], ctx["news"], ctx["names"]
    clima = ai.get("clima") if ok_ai else None
    clima_txt = {"risk-on": "Apetito por riesgo", "risk-off": "Aversión al riesgo", "mixto": "Día mixto"}

    if clima:
        hero = (f'<h1 class="clima">{clima_txt.get(clima, E(clima))}</h1>'
                f'<p class="summary">{E(ai.get("resumen", ""))}</p>')
    else:
        ups = sum(1 for r in rows if (r["chg_1d"] or 0) > 0 and not r.get("level"))
        tot = sum(1 for r in rows if r["chg_1d"] is not None and not r.get("level"))
        hero = (f'<h1 class="clima">{ups} de {tot} activos suben'
                f'<small>{E(ai.get("error") or "Análisis con IA desactivado: solo datos y reglas.")}</small></h1>')

    decision = ""
    if ok_ai:
        decision = (f'<div class="decision"><b>{E(ai.get("decision", "").capitalize())}</b> · '
                    f'{E(ai.get("decision_motivo", ""))}</div>')

    tiles = []
    for r in rows:
        if not r["key"]:
            continue
        df = series.get(r["ticker"])
        closes = list(df["close"].tail(63)) if df is not None else []
        ma = list(df["close"].rolling(50).mean().tail(63)) if df is not None else None
        ma = [None if v != v else v for v in ma] if ma else None
        warn = ' <span title="Las fuentes difieren más de 0,5%">⚠</span>' if r["calidad"] == "dudoso" else ""
        tiles.append(
            f'<div class="tile"><div class="n">{E(r["name"])}{warn}</div>'
            f'<div class="p">{_num(r["last"])}</div>'
            f'<div class="c {_cls(r["chg_1d"])}">{_pct(r["chg_1d"], r.get("level"))} hoy</div>'
            f'{sparkline(closes, ma=ma)}'
            f'<div class="t">{r["trend"]} · {_pct(r["chg_1m"], r.get("level"))} en el mes</div></div>')

    news_html = []
    if ok_ai and ai.get("noticias"):
        for n in sorted(ai["noticias"], key=lambda n: -int(n.get("importancia", 0) or 0)):
            it = news[n["id"]]
            imp = int(n.get("importancia", 1) or 1)
            rumor = ' · <b>rumor</b>' if n.get("rumor") else ""
            news_html.append(
                f'<li><div class="meta"><span class="cat">{E(n.get("categoria", it["category"]))}</span>'
                f'{E(it["source"])} · {_hora(it["published"])} · '
                f'<span class="imp" title="Importancia {imp} de 5">{"●" * imp}{"○" * (5 - imp)}</span>{rumor}</div>'
                f'<div class="h"><a href="{E(it["link"])}" rel="noopener">{E(it["title"])}</a></div>'
                f'<p>{E(n.get("novedad", ""))} <b>Impacto:</b> {E(n.get("impacto", ""))}</p></li>')
    else:
        for it in news[:8]:
            news_html.append(
                f'<li><div class="meta"><span class="cat">{E(it["category"])}</span>{E(it["source"])} · '
                f'{_hora(it["published"])}</div><div class="h"><a href="{E(it["link"])}" rel="noopener">'
                f'{E(it["title"])}</a></div></li>')
    div = ""
    if ok_ai and ai.get("divergencias"):
        div = ('<p class="note"><b>Divergencias precio-noticia:</b> '
               + E(" · ".join(ai["divergencias"])) + "</p>")

    hyps = ai.get("hipotesis") or [] if ok_ai else []
    if ctx["mode"] in ("apertura", "intradía"):
        hyp_html = f'<p class="empty">Revisión de {ctx["mode"]}: solo observación. Las hipótesis se registran con precios de cierre.</p>'
    elif not ok_ai:
        hyp_html = '<p class="empty">Sin análisis con IA no se generan hipótesis.</p>'
    elif not hyps:
        hyp_html = '<p class="empty">Ninguna oportunidad supera los filtros: no operar hoy.</p>'
    else:
        cards = []
        for h in hyps:
            arrow = "▲ al alza" if h["direccion"] == "alcista" else "▼ a la baja"
            op = "se opera en simulación" if h.get("operable") else "solo se mide"
            cards.append(
                f'<div class="h-card {h["direccion"]}"><div class="h-top"><b>{E(names.get(h["ticker"], h["ticker"]))} '
                f'<span class="{"up" if h["direccion"] == "alcista" else "down"}">{arrow}</span></b>'
                f'<span class="conf">{h["confianza"]}%<small> prob. · {op}</small></span></div>'
                f'<p>{E(h.get("tesis", ""))}</p>'
                f'<p class="against">Objetivo +{h.get("objetivo_pct") or 0:.1f}% · stop −{h["invalidacion_pct"]:.1f}% · '
                f'plazo {h["horizonte_dias"]} sesiones · valor esperado neto {h.get("ev_pct") or 0:+.1f}%</p>'
                f'<p class="against">Disparador: {E(h.get("disparador", ""))}</p>'
                f'<p class="against">En contra: {E(h.get("contra", ""))}</p></div>')
        hyp_html = f'<div class="hyp">{"".join(cards)}</div>'

    watch, seen = [], set()
    for v in (ai.get("vigilar") or []) if ok_ai else []:
        seen.add(v["ticker"])
        watch.append(f'<li><b>{E(names.get(v["ticker"], v["ticker"]))}</b> · {E(v["motivo"])}</li>')
    for r in rows:
        if r["flags"] and r["ticker"] not in seen:
            watch.append(f'<li><b>{E(r["name"])}</b> · {E(", ".join(r["flags"]))}</li>')
    watch_html = f'<ul class="plain watch">{"".join(watch)}</ul>' if watch else '<p class="empty">Nada destacable hoy.</p>'

    trs = []
    for r in rows:
        lv = r.get("level")
        trs.append(
            f'<tr><td>{E(r["name"])}</td><td>{_num(r["last"])}</td>'
            + "".join(f'<td class="{_cls(r[k])}">{_pct(r[k], lv)}</td>' for k in ("chg_1d", "chg_5d", "chg_1m", "chg_3m"))
            + f'<td>{"—" if r["rsi14"] is None else round(r["rsi14"])}</td><td>{r["trend"]}</td>'
            f'<td class="flags">{E(", ".join(r["flags"])) or "—"}</td></tr>')

    st = ctx["stats"]
    stat_items = [f'<div><b>{st["registradas"]}</b><span>registradas</span></div>',
                  f'<div><b>{st["abiertas"]}</b><span>abiertas</span></div>',
                  f'<div><b>{st["cerradas"]}</b><span>cerradas</span></div>']
    for label in ("todas", "operadas"):
        s = st.get(label)
        if s:
            stat_items.append(f'<div><b>{100 * s["acierto"]:.0f}%</b><span>acierto {label} '
                              f'(IC 95% {100 * s["lo"]:.0f}–{100 * s["hi"]:.0f}%, n={s["n"]}) · '
                              f'neto medio {100 * s.get("ret_neto_medio", s["ret_medio"]):+.2f}% por operación</span></div>')
    phase = ('<p class="note">Fase de rodaje: con menos de 30 hipótesis cerradas el acierto todavía no dice nada.</p>'
             if st["cerradas"] < 30 else "")

    q = ctx["quality"]
    page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Radar de mercados</title>
<meta name="description" content="Resumen diario de mercados: precios, noticias e hipótesis simuladas.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">
<header><span class="brand">Radar de mercados</span>
<span class="when">{DIAS[now.weekday()]} {now.day} {MESES[now.month - 1]} · revisión de {ctx["mode"]} · {now:%H:%M}</span></header>
<section class="hero">{hero}
{thermometer(rows)}
{movers(rows)}
<p class="caption" id="pick" aria-live="polite">Cada punto es un activo, colocado según cuánto ha subido o bajado en su última sesión. Toca un punto para ver cuál es.</p>
{decision}</section>
<h2>Lo esencial</h2><div class="tiles">{"".join(tiles)}</div>
<p class="note">Línea: últimos 3 meses · discontinua: media de 50 sesiones.</p>
<h2>Noticias clave</h2><ol class="news">{"".join(news_html) or '<li class="empty">No se pudieron descargar titulares.</li>'}</ol>{div}
<h2>Hipótesis de hoy</h2>{hyp_html}
<h2>A vigilar</h2>{watch_html}
{pead_html(ctx.get("pead"))}
<h2>Todos los activos</h2><div class="scroll"><table>
<thead><tr><th>Activo</th><th>Último</th><th>Día</th><th>Semana</th><th>Mes</th><th>3 meses</th><th>RSI</th><th>Tendencia</th><th>Señales</th></tr></thead>
<tbody>{"".join(trs)}</tbody></table></div>
<h2>Cómo van las hipótesis</h2><div class="stats">{"".join(stat_items)}</div>{phase}
<footer>
<p>Proyecto de I+D. Todo es simulación (paper trading); nada de esto es asesoramiento financiero.</p>
<p>Precios: {q["ok"]} contrastados con dos fuentes, {q["sin_contraste"]} con una sola, {q["dudoso"]} dudosos, {q["sin_dato"]} sin dato
({E(", ".join(f"{k} {v}" for k, v in q["fuentes"].items()))}). Análisis: {E(ai.get("modelo", "desactivado") if ok_ai else "desactivado")}{f' (coste ~{ai["uso"]["coste_usd"]:.3f} USD)' if ok_ai and ai.get("uso") else ""}.</p>
<p>Tendencia alcista: precio sobre sus medias de 50 y 200 sesiones y subiendo en el mes; bajista, al revés; si no, lateral.</p>
<p><a href="https://github.com/xqwertyx-ai/Tradingbot">Código y datos en GitHub</a></p>
</footer></div>
<script>document.querySelectorAll('.thermo .dot').forEach(function(g){{var t=g.querySelector('title').textContent,
p=document.getElementById('pick');['click','focus','mouseenter'].forEach(function(e){{g.addEventListener(e,function(){{p.textContent=t}})}})}});</script>
</body></html>"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    with open(os.path.join(out_dir, "datos.json"), "w", encoding="utf-8") as f:
        json.dump({"generado": ctx["now"].isoformat(), "activos": rows}, f, ensure_ascii=False, default=str)
    return path
