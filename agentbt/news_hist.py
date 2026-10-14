"""Titulares históricos de un día, solo los publicados ANTES del cierre de Wall Street.

Ventana: desde el cierre de la sesión anterior hasta el cierre del día (16:00 Nueva York).
Fuente principal: Google News RSS con operadores de fecha (after:/before:).
Respaldo: GDELT DOC API (gratuita, con hora de publicación).
Se guardan en caché por día para no repetir descargas.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
import urllib.parse
from zoneinfo import ZoneInfo

from dashboard.news import _norm, categorize, parse_feed
from tradingbot.http import make_session

NY = ZoneInfo("America/New_York")
CACHE = "data/agent_bt/news"
_s = make_session(retries=3, backoff=1.0)

GOOGLE_QUERIES = [
    ("es", "ES", "bolsa OR ibex OR mercados"),
    ("en-US", "US", 'stocks OR "wall street" OR fed OR inflation'),
    ("en-US", "US", "bitcoin OR crypto"),
    ("en-US", "US", "oil OR gold OR dollar OR treasury"),
]
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"


def close_utc(day: dt.date) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(16, 0), NY).astimezone(dt.timezone.utc)


def _google(day: dt.date, prev: dt.date) -> list[dict]:
    out = []
    for hl, gl, q in GOOGLE_QUERIES:
        query = f"{q} after:{prev.isoformat()} before:{(day + dt.timedelta(days=1)).isoformat()}"
        url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query)
               + f"&hl={hl}&gl={gl}&ceid={gl}:{hl.split('-')[0]}")
        try:
            r = _s.get(url, timeout=20)
            r.raise_for_status()
            out += parse_feed(r.text, "Google News")
        except Exception as e:
            print(f"  Google News {day}: {e.__class__.__name__}")
    return out


GDELT_QUERIES = [
    '(stocks OR "wall street" OR inflation OR "federal reserve" OR treasury OR earnings) sourcelang:english',
    "(bitcoin OR crypto OR oil OR gold OR dollar) sourcelang:english",
    "(bolsa OR ibex OR mercados OR inflación OR BCE) sourcelang:spanish",
]


def _gdelt(start: dt.datetime, end: dt.datetime) -> list[dict]:
    """GDELT da la hora exacta en que vio cada artículo: permite cortar en el cierre."""
    out = []
    for q in GDELT_QUERIES:
        params = {"query": q, "mode": "artlist", "format": "json", "maxrecords": 100, "sort": "hybridrel",
                  "startdatetime": start.strftime("%Y%m%d%H%M%S"),
                  "enddatetime": end.strftime("%Y%m%d%H%M%S")}
        try:
            r = _s.get(GDELT, params=params, timeout=30)
            r.raise_for_status()
            arts = r.json().get("articles", []) if r.text.strip().startswith("{") else []
        except Exception as e:
            print(f"  GDELT: {e.__class__.__name__}")
            arts = []
        for a in arts:
            try:
                pub = dt.datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
            except (KeyError, ValueError):
                continue
            out.append({"title": a.get("title", "").strip(), "link": a.get("url", ""),
                        "source": a.get("domain", "GDELT"), "feed": "GDELT", "published": pub})
        time.sleep(5)  # GDELT pide no más de una petición cada 5 s
    return out


def headlines(day: dt.date, prev: dt.date, limit: int = 60) -> list[dict]:
    """Titulares publicados en [cierre de prev, cierre de day). Con caché."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{day.isoformat()}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    start, end = close_utc(prev), close_utc(day)
    items = _gdelt(start, end)
    src = "gdelt"
    if len(items) < 15:
        # Google News con fechas solo da el día, no la hora: un titular "del día" puede ser
        # posterior al cierre. Por prudencia, de Google solo se usa lo fechado el día anterior.
        g = [i for i in _google(prev, prev) if i["published"] and i["published"].date() <= prev]
        for i in g:
            i["published"] = max(i["published"], start)
        items += g
        src = "gdelt+google(día anterior)"
    seen, out = set(), []
    for it in items:
        p = it["published"]
        if not it["title"] or p is None or not (start <= p < end):
            continue  # sin hora fiable o fuera de ventana: fuera (evita información futura)
        k = _norm(it["title"])
        if k in seen:
            continue
        seen.add(k)
        it["category"] = categorize(it["title"])
        it["score"] = 1 if it["category"] != "otras" else 0
        out.append(it)
    out.sort(key=lambda x: (x["score"], x["published"]), reverse=True)
    out = out[:limit]
    out.sort(key=lambda x: x["published"])
    for it in out:
        it["published"] = it["published"].isoformat()
    print(f"  {day}: {len(out)} titulares ({src})")
    if len(out) >= 5:  # no guardar en caché una descarga fallida
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
    return out


def clean_title(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()
