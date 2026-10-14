"""Titulares de las últimas 24 h por RSS. Cada fuente es opcional: si falla, se anota."""
from __future__ import annotations

import datetime as dt
import email.utils
import re
import xml.etree.ElementTree as ET

from tradingbot.http import make_session

FEEDS = [
    ("Google News · mercados ES",
     "https://news.google.com/rss/search?q=bolsa+OR+ibex+OR+mercados+when:1d&hl=es&gl=ES&ceid=ES:es"),
    ("Google News · markets",
     "https://news.google.com/rss/search?q=stocks+OR+%22wall+street%22+OR+fed+OR+inflation+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("Google News · crypto",
     "https://news.google.com/rss/search?q=bitcoin+OR+crypto+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Expansión", "https://e00-expansion.uecdn.es/rss/mercados.xml"),
]

# Palabras clave -> categoría (solo para el modo sin IA y para ordenar).
CATEGORIES = [
    ("macro", r"\b(fed|bce|ecb|inflaci|inflation|ipc|cpi|ppi|empleo|payroll|jobs|tipos|rates?|pib|gdp|bono|treasur|yield|powell|lagarde)"),
    ("geopolítica", r"\b(guerra|war|sanci|tariff|arancel|china|rusia|russia|ucrania|ukraine|israel|iran|opec|opep)"),
    ("resultados", r"\b(resultados|earnings|beneficio|profit|revenue|ingresos|guidance|previsi)"),
    ("cripto", r"\b(bitcoin|btc|ether|crypto|cripto|etf|stablecoin|hack|binance|coinbase|solana)"),
    ("regulación", r"\b(sec\b|cnmv|regulat|regula|ley|law|antitrust|multa|fine)"),
]
IMPORTANT = r"\b(fed|bce|ecb|ipc|cpi|inflation|inflaci|tipos|rates|record|récord|crash|desplome|plunge|surge|dispara|hundi|tariff|arancel|guerra|war|earnings|resultados)"

_s = make_session()


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:
        try:
            return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None


def parse_feed(xml_text: str, feed_name: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src_el = it.find("source")
        source = src_el.text.strip() if src_el is not None and src_el.text else feed_name
        if feed_name.startswith("Google News") and " - " in title:
            title = title.rsplit(" - ", 1)[0]  # Google añade " - Medio" al final
        items.append({
            "title": title,
            "link": (it.findtext("link") or "").strip(),
            "source": source,
            "feed": feed_name,
            "published": _parse_date(it.findtext("pubDate")),
        })
    return items


def categorize(title: str) -> str:
    t = title.lower()
    for cat, rx in CATEGORIES:
        if re.search(rx, t):
            return cat
    return "otras"


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúñ ]", "", t.lower())[:70]


def fetch_news(hours: int = 24, limit: int = 60) -> tuple[list[dict], dict]:
    now = dt.datetime.now(dt.timezone.utc)
    status, out, seen = {}, [], set()
    for name, url in FEEDS:
        try:
            r = _s.get(url, timeout=20)
            r.raise_for_status()
            items = parse_feed(r.text, name)
            status[name] = f"ok ({len(items)})"
        except Exception as e:
            status[name] = f"falló ({e.__class__.__name__})"
            continue
        for it in items:
            p = it["published"]
            if not it["title"] or (p and now - p > dt.timedelta(hours=hours)):
                continue
            k = _norm(it["title"])
            if k in seen:
                continue
            seen.add(k)
            it["category"] = categorize(it["title"])
            it["score"] = (2 if re.search(IMPORTANT, it["title"].lower()) else 0) + (
                1 if it["category"] != "otras" else 0)
            out.append(it)
    out.sort(key=lambda x: (x["score"], x["published"] or now - dt.timedelta(days=1)), reverse=True)
    for it in out:
        it["published"] = it["published"].isoformat() if it["published"] else None
    return out[:limit], status
