"""Análisis de la jornada con la API de Claude (opcional).

Necesita el secret ANTHROPIC_API_KEY en el repo. Sin él, la portada se genera
igual, con las señales de tendencia y los titulares ordenados por reglas.
El modelo solo recibe datos ya descargados: no puede citar noticias o precios
que no estén en la entrada (se valida al recibir la respuesta).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re

from dashboard.universe import LEVEL_TICKERS, cost_pct
from tradingbot.http import make_session

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
ALGO_VERSION = "v1.4"  # ver bitácora: R-1015-2 (confianza = probabilidad) y R-1015-3 (planes con objetivo y EV)
# Se opera (en simulación) solo si el valor esperado neto y la probabilidad superan estos mínimos.
MIN_EV_PCT = 1.0
MIN_PROB = 55
API_URL = "https://api.anthropic.com/v1/messages"
# USD por millón de tokens (entrada, salida). Fuente: platform.claude.com/docs/en/models/overview (14-oct-2026)
PRICES = {"claude-sonnet-5-5": (2.0, 10.0), "claude-opus-5-5": (4.0, 20.0)}

SYSTEM = """Eres un agente de análisis de mercados en un proyecto de I+D. Lees las noticias de la jornada,
estimas su impacto probable en activos cotizados y propones hipótesis evaluables en simulación
(paper trading). No es asesoramiento financiero.

Proceso obligatorio:
1. RECOGIDA: elige solo titulares de la lista recibida (cítalos por su id). Clasifícalos: macro,
   política/regulación, geopolítica, resultados, sectorial, cripto, ruido. Marca rumores.
2. NOVEDAD Y DESCUENTO: ¿era esperada? ¿el precio ya se movió? Solo hay oportunidad si hay
   diferencia entre lo que el mercado descuenta y lo que la noticia implica.
3. MAPA DE IMPACTO: activos afectados directa e indirectamente, mecanismo causal en una frase,
   dirección, magnitud y horizonte.
4. CONTRASTE CON PRECIOS: compara la reacción observada (tabla de precios) con la esperada.
   Señala divergencias. Ten en cuenta la correlación de fondo (días risk-on/risk-off).
   Sin mecanismo plausible, una correlación no es señal.
5. HIPÓTESIS: cada una es un plan de operación falsable, solo con activos de la tabla
   (no con niveles como el rendimiento del bono):
   - objetivo_pct: ganancia buscada al cierre; invalidacion_pct: pérdida máxima al cierre (stop).
   - confianza: PROBABILIDAD (0-100) de que un cierre toque el objetivo antes que el stop dentro del
     plazo. 50 = moneda al aire; 65 = casi 2 de cada 3. Usa toda la escala: se mide si estás calibrado.
6. AUTOCRÍTICA: mejor argumento en contra, sesgos posibles y por qué esa probabilidad.

Reglas: no inventes datos, precios ni noticias. Separa hecho, interpretación y predicción.
Nada de certezas. Considera liquidez, costes, horario de mercado y riesgo de gap.
Hipótesis con la misma idea de fondo cuentan como una.

Cómo se decide operar (lo calcula el código, no tú): valor esperado neto
EV = p·objetivo − (1−p)·stop − coste (coste de ida y vuelta de la tabla). Se opera si EV >= 1% y p >= 55.
Para encontrar operaciones así, sé osado donde haya ventaja, no en todas partes:
- Busca asimetría: objetivo de al menos 1,5 veces el stop.
- Pide movimientos posibles: en h sesiones un activo suele moverse alrededor de su volatilidad diaria
  por la raíz de h. Un objetivo muy por encima de eso es improbable; muy por debajo no cubre costes.
  Divisas y activos tranquilos rara vez dan un 1% neto; prefiere plazos de 3 a 10 sesiones.
- Exige confluencia: al menos dos señales independientes (noticia nueva no descontada + tendencia;
  divergencia precio-noticia + sobreventa/sobrecompra; sorpresa macro + sector más sensible).
- No persigas lo que ya se movió más de 2σ sin una razón nueva: suele estar descontado.
Propón SIEMPRE entre 2 y 4 hipótesis, las mejores del día: se registran todas para medir la
calibración. No infles la probabilidad para que se operen: un día sin operaciones es válido.
Escribe en español."""

SCHEMA = """Responde SOLO con un objeto JSON válido con esta forma:
{
 "resumen": "2-3 frases: qué ha cambiado en esta revisión (región que abre/cierra) frente a la anterior",
 "resumen_dia": "solo si se pide: 3-5 frases sobre la jornada completa (Asia, Europa, EE. UU.)",
 "clima": "risk-on" | "risk-off" | "mixto",
 "noticias": [ {"id": <id del titular>, "categoria": "...", "rumor": false,
               "novedad": "esperada/sorpresa y por qué, 1 frase",
               "impacto": "activos afectados, mecanismo y dirección, 1-2 frases",
               "importancia": 1-5} ],          // máximo 6, las más relevantes
 "divergencias": ["frase", ...],               // reacciones de precio que no cuadran con la noticia
 "hipotesis": [ {"ticker": "<ticker de la tabla>", "direccion": "alcista" | "bajista",
                 "horizonte_dias": 1-20, "tesis": "1 frase con el mecanismo",
                 "disparador": "condición con precio de cierre",
                 "objetivo_pct": <ganancia buscada al cierre en %, p. ej. 4>,
                 "invalidacion_pct": <pérdida máxima al cierre en %, p. ej. 2>,
                 "confianza": <probabilidad 0-100 de tocar el objetivo antes que el stop>,
                 "confluencia": ["señal 1", "señal 2"], "contra": "mejor argumento en contra",
                 "sesgos": "sesgos posibles"} ],  // entre 2 y 4 (vacío si la revisión no es el cierre)
 "vigilar": [ {"ticker": "<ticker de la tabla>", "motivo": "1 frase"} ],  // máximo 5
 "decision": "operar" | "no operar hoy",
 "decision_motivo": "1 frase"
}"""


def _fmt(x, pct=True):
    if x is None:
        return "—"
    return f"{100 * x:+.1f}%" if pct else f"{x:.2f}"


def _vol(m):
    v = m.get("vol20_ann")
    return "—" if v is None else f"{100 * v / math.sqrt(252):.1f}%/día"


def expected_value(h: dict) -> float:
    """EV neto en % por operación: p·objetivo − (1−p)·stop − coste."""
    p = h["confianza"] / 100
    return p * h["objetivo_pct"] - (1 - p) * h["invalidacion_pct"] - cost_pct(h["ticker"])


def build_prompt(date: str, mode: str, table: list[dict], news: list[dict], open_hyps: list[dict],
                 previos: list[dict] | None = None, final: bool = False) -> str:
    previos = previos or []
    lines = [f"Fecha: {date} · Revisión: {mode}",
             "Hay seis revisiones al día (apertura y cierre de Asia, Europa y EE. UU.). Céntrate en lo que ha "
             "cambiado desde la anterior y en la región que acaba de abrir o cerrar. Con una bolsa abierta, su "
             "último dato es el precio del momento (con retraso), no un cierre.",
             "Usa solo la información de este mensaje: no recurras a lo que sepas de fechas posteriores.", "",
             "PRECIOS (último cierre; cambios 1d / 5d / 1m; volatilidad diaria; coste ida y vuelta; tendencia; señales):"]
    for a in table:
        m = a["m"]
        lines.append(
            f"- {a['ticker']} ({a['name']}): {m['last']:.4g} [{m['date']}] "
            f"{_fmt(m['chg_1d'], not a.get('level'))} / {_fmt(m['chg_5d'], not a.get('level'))} / "
            f"{_fmt(m['chg_1m'], not a.get('level'))}; "
            + ("no operable (nivel)" if a.get("level") else
               f"vol {_vol(m)} · coste {cost_pct(a['ticker']):.2f}%")
            + f"; {m['trend']}; {', '.join(m['flags']) or '—'}")
    desde = max((dt.datetime.fromisoformat(p["hora"]) for p in previos), default=None)
    lines += ["", "TITULARES (últimas 24 h; [NUEVO] = publicado tras la revisión anterior):"]
    for i, n in enumerate(news):
        nuevo = " [NUEVO]" if desde and n["published"] and dt.datetime.fromisoformat(n["published"]) > desde else ""
        lines.append(f"[{i}]{nuevo} {n['published'] or 'sin hora'} · {n['source']} · {n['title']}")
    if previos:
        lines += ["", "REVISIONES ANTERIORES HOY:"]
        lines += [f"- {p['hora_madrid']} · {p['etiqueta']} ({p.get('clima') or '—'}): {p.get('resumen') or '—'}" for p in previos]
    if open_hyps:
        lines += ["", "HIPÓTESIS ABIERTAS (no dupliques la misma idea):"]
        lines += [f"- {h['ticker']} {h['direccion']} hasta {h['vence']}: {h['tesis']}" for h in open_hyps]
    if mode != "cierre":
        lines += ["", f"Revisión de {mode.upper()}: solo observación. Devuelve \"hipotesis\": [] "
                  "(las decisiones se toman con precios de cierre de EE. UU.)."]
    if final:
        lines += ["", "Es la última revisión del día: rellena \"resumen_dia\" con 3-5 frases sobre la jornada "
                  "completa usando las revisiones anteriores y esta."]
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("la respuesta no contiene JSON")
    return json.loads(m.group(0))


def validate(out: dict, tickers: set[str], n_news: int, mode: str) -> dict:
    """Descarta lo que no se apoye en la entrada (tickers o titulares inexistentes)."""
    out["noticias"] = [n for n in out.get("noticias", [])
                       if isinstance(n.get("id"), int) and 0 <= n["id"] < n_news][:6]
    hyps = []
    for h in out.get("hipotesis", []) if mode == "cierre" else []:
        try:
            if (h["ticker"] in tickers and h["ticker"] not in LEVEL_TICKERS
                    and h["direccion"] in ("alcista", "bajista")):
                h["horizonte_dias"] = int(min(max(int(h["horizonte_dias"]), 1), 20))
                h["confianza"] = int(min(max(int(h["confianza"]), 0), 100))
                h["invalidacion_pct"] = float(abs(float(h["invalidacion_pct"])))
                h["objetivo_pct"] = float(abs(float(h["objetivo_pct"])))
                if h["invalidacion_pct"] <= 0 or h["objetivo_pct"] <= 0:
                    continue
                h["ev_pct"] = round(expected_value(h), 2)
                h["operable"] = h["ev_pct"] >= MIN_EV_PCT and h["confianza"] >= MIN_PROB
                hyps.append(h)
        except (KeyError, TypeError, ValueError):
            continue
    out["hipotesis"] = hyps[:4]
    ops = [h for h in out["hipotesis"] if h["operable"]]
    if mode == "cierre" and ops:
        out["decision"] = "operar"
        out["decision_motivo"] = (f"{len(ops)} plan(es) con valor esperado neto ≥ {MIN_EV_PCT:.0f}% "
                                  f"y probabilidad ≥ {MIN_PROB}: " + ", ".join(h["ticker"] for h in ops) + ".")
    elif mode == "cierre":
        out["decision"] = "no operar hoy"
    out["vigilar"] = [v for v in out.get("vigilar", []) if v.get("ticker") in tickers][:5]
    return out


def analyze(date, mode, table, news, open_hyps, previos=None, final=False) -> dict | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    prompt = build_prompt(date, mode, table, news, open_hyps, previos, final)
    s = make_session()
    r = s.post(API_URL, timeout=180, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={
        "model": MODEL, "max_tokens": 8000, "system": SYSTEM,
        "messages": [{"role": "user", "content": prompt + "\n\n" + SCHEMA}],
    })
    if r.status_code != 200:
        print(f"API de Claude: error {r.status_code}: {r.text[:300]}")
        return {"error": f"La API de Claude respondió {r.status_code}."}
    text = "".join(b.get("text", "") for b in r.json().get("content", []))
    try:
        out = _extract_json(text)
    except Exception as e:
        print(f"Respuesta no válida: {e}\n{text[:500]}")
        return {"error": "La respuesta del modelo no era JSON válido."}
    out = validate(out, {a["ticker"] for a in table}, len(news), mode)
    out["modelo"] = MODEL
    u = r.json().get("usage", {})
    pin, pout = PRICES.get(MODEL, (math.nan, math.nan))
    tin, tout = u.get("input_tokens", 0), u.get("output_tokens", 0)
    out["uso"] = {"tokens_entrada": tin, "tokens_salida": tout,
                  "coste_usd": round(tin / 1e6 * pin + tout / 1e6 * pout, 4)}
    print(f"Uso de la API: {tin} tokens de entrada, {tout} de salida, ~{out['uso']['coste_usd']} USD")
    return out
