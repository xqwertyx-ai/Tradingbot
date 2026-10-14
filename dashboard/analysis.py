"""Análisis de la jornada con la API de Claude (opcional).

Necesita el secret ANTHROPIC_API_KEY en el repo. Sin él, la portada se genera
igual, con las señales de tendencia y los titulares ordenados por reglas.
El modelo solo recibe datos ya descargados: no puede citar noticias o precios
que no estén en la entrada (se valida al recibir la respuesta).
"""
from __future__ import annotations

import json
import math
import os
import re

from tradingbot.http import make_session

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
ALGO_VERSION = "v1.3"  # ver bitácora: R-1015-1 (registrar también hipótesis de confianza < 60)
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
5. HIPÓTESIS: falsables, con plazo e invalidación. Solo con activos de la tabla.
6. AUTOCRÍTICA: mejor argumento en contra, sesgos posibles, confianza 0-100 justificada.

Reglas: no inventes datos, precios ni noticias. Separa hecho, interpretación y predicción.
Nada de certezas. Considera liquidez, costes, horario de mercado y riesgo de gap.
Hipótesis con la misma idea de fondo cuentan como una. Solo se opera (en simulación) lo que tenga
confianza >= 60; si nada llega, la decisión es "no operar hoy", y es una respuesta válida.
Aun así, propón SIEMPRE entre 2 y 4 hipótesis, las mejores del día, con una confianza honesta
aunque sea baja: las de menos de 60 se registran solo para medir si tu confianza está bien calibrada.
No subas la confianza para que se operen. Escribe en español."""

SCHEMA = """Responde SOLO con un objeto JSON válido con esta forma:
{
 "resumen": "2-3 frases sobre la jornada",
 "clima": "risk-on" | "risk-off" | "mixto",
 "noticias": [ {"id": <id del titular>, "categoria": "...", "rumor": false,
               "novedad": "esperada/sorpresa y por qué, 1 frase",
               "impacto": "activos afectados, mecanismo y dirección, 1-2 frases",
               "importancia": 1-5} ],          // máximo 6, las más relevantes
 "divergencias": ["frase", ...],               // reacciones de precio que no cuadran con la noticia
 "hipotesis": [ {"ticker": "<ticker de la tabla>", "direccion": "alcista" | "bajista",
                 "horizonte_dias": 1-20, "tesis": "1 frase con el mecanismo",
                 "disparador": "condición con precio de cierre",
                 "invalidacion_pct": <movimiento adverso al cierre en %, p. ej. 3>,
                 "confianza": 0-100, "contra": "mejor argumento en contra",
                 "sesgos": "sesgos posibles"} ],  // entre 2 y 4 (vacío solo en apertura/intradía)
 "vigilar": [ {"ticker": "<ticker de la tabla>", "motivo": "1 frase"} ],  // máximo 5
 "decision": "operar" | "no operar hoy",
 "decision_motivo": "1 frase"
}"""


def _fmt(x, pct=True):
    if x is None:
        return "—"
    return f"{100 * x:+.1f}%" if pct else f"{x:.2f}"


def build_prompt(date: str, mode: str, table: list[dict], news: list[dict], open_hyps: list[dict]) -> str:
    lines = [f"Fecha: {date} · Revisión: {mode}",
             "Usa solo la información de este mensaje: no recurras a lo que sepas de fechas posteriores.", "",
             "PRECIOS (último cierre disponible; cambios 1d / 5d / 1m; tendencia; señales):"]
    for a in table:
        m = a["m"]
        lines.append(
            f"- {a['ticker']} ({a['name']}): {m['last']:.4g} [{m['date']}] "
            f"{_fmt(m['chg_1d'], not a.get('level'))} / {_fmt(m['chg_5d'], not a.get('level'))} / "
            f"{_fmt(m['chg_1m'], not a.get('level'))}; {m['trend']}; {', '.join(m['flags']) or '—'}")
    lines += ["", "TITULARES (últimas 24 h):"]
    for i, n in enumerate(news):
        lines.append(f"[{i}] {n['published'] or 'sin hora'} · {n['source']} · {n['title']}")
    if open_hyps:
        lines += ["", "HIPÓTESIS ABIERTAS (no dupliques la misma idea):"]
        lines += [f"- {h['ticker']} {h['direccion']} hasta {h['vence']}: {h['tesis']}" for h in open_hyps]
    if mode in ("apertura", "intradía"):
        lines += ["", f"Revisión de {mode.upper()}: solo observación. Devuelve \"hipotesis\": [] "
                  "(las decisiones se toman con precios de cierre)."]
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
            if h["ticker"] in tickers and h["direccion"] in ("alcista", "bajista"):
                h["horizonte_dias"] = int(min(max(int(h["horizonte_dias"]), 1), 20))
                h["confianza"] = int(min(max(int(h["confianza"]), 0), 100))
                h["invalidacion_pct"] = float(abs(float(h["invalidacion_pct"])))
                hyps.append(h)
        except (KeyError, TypeError, ValueError):
            continue
    out["hipotesis"] = hyps[:4]
    out["vigilar"] = [v for v in out.get("vigilar", []) if v.get("ticker") in tickers][:5]
    return out


def analyze(date, mode, table, news, open_hyps) -> dict | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    prompt = build_prompt(date, mode, table, news, open_hyps)
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
