"""Calendario de revisiones del día: apertura y cierre de Asia, Europa y EE. UU.

El "día" es la fecha de Madrid: la apertura de Tokio (09:00 JST) cae a las 01:00-02:00 de Madrid y
el cierre de Wall Street (16:00 Nueva York) a las 21:00-22:00, así que las seis revisiones caen en
la misma fecha. Las horas se definen en la zona de cada bolsa, de modo que los cambios de horario
(Europa y EE. UU. no cambian el mismo día) se resuelven solos.

GitHub retrasa a veces los cron programados, así que en vez de fiar la revisión a la hora exacta
se elige la revisión más antigua ya vencida y aún no hecha hoy (dentro de una ventana).
"""
from __future__ import annotations

import datetime as dt
import json
import os
from zoneinfo import ZoneInfo

MAD = ZoneInfo("Europe/Madrid")
DIR = "data/dashboard/dias"

# id, etiqueta, zona de la bolsa, hora local del evento, ventana para hacer la revisión (horas)
EVENTOS = [
    ("asia-apertura", "apertura Asia", "Asia/Tokyo", dt.time(9, 0), 4),
    ("asia-cierre", "cierre Asia", "Asia/Hong_Kong", dt.time(16, 10), 4),
    ("europa-apertura", "apertura Europa", "Europe/Madrid", dt.time(9, 0), 4),
    ("europa-cierre", "cierre Europa", "Europe/Madrid", dt.time(17, 35), 4),
    ("usa-apertura", "apertura EE. UU.", "America/New_York", dt.time(9, 30), 4),
    ("usa-cierre", "cierre EE. UU.", "America/New_York", dt.time(16, 0), 7),
]
MARGEN = dt.timedelta(minutes=15)  # se espera un poco tras el evento para que haya precios
ETIQUETA = {e[0]: e[1] for e in EVENTOS}


def dia(now: dt.datetime) -> dt.date:
    return now.astimezone(MAD).date()


def instante(ev_id: str, d: dt.date) -> dt.datetime:
    _, _, zona, hora, _ = next(e for e in EVENTOS if e[0] == ev_id)
    return dt.datetime.combine(d, hora, tzinfo=ZoneInfo(zona))


def pendiente(now: dt.datetime, hechos: set[str]) -> str | None:
    """La revisión más antigua ya vencida, dentro de su ventana y no hecha hoy (o None)."""
    d = dia(now)
    if d.weekday() >= 5:
        return None
    for t, ev_id, ventana in sorted((instante(e[0], d), e[0], e[4]) for e in EVENTOS):
        if ev_id not in hechos and t + MARGEN <= now <= t + dt.timedelta(hours=ventana):
            return ev_id
    return None


def _path(d: dt.date) -> str:
    return os.path.join(DIR, f"{d.isoformat()}.json")


def cargar(d: dt.date) -> list[dict]:
    try:
        with open(_path(d), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def guardar(d: dt.date, entradas: list[dict]) -> None:
    os.makedirs(DIR, exist_ok=True)
    with open(_path(d), "w", encoding="utf-8") as f:
        json.dump(entradas, f, ensure_ascii=False, indent=1)


def registrar(d: dt.date, entrada: dict) -> list[dict]:
    """Añade (o sustituye, si se repite) la revisión del día y devuelve la lista ordenada."""
    entradas = [e for e in cargar(d) if e["id"] != entrada["id"]] + [entrada]
    entradas.sort(key=lambda e: e["hora"])
    guardar(d, entradas)
    return entradas


def agenda(now: dt.datetime, entradas: list[dict]) -> list[dict]:
    """Las seis revisiones del día en orden: hecha (con su entrada), perdida (pasó su ventana sin
    hacerse, p. ej. porque GitHub no lanzó el cron) o pendiente."""
    d, hechas = dia(now), {e["id"]: e for e in entradas}
    out = []
    for t, ev_id, ventana in sorted((instante(e[0], d), e[0], e[4]) for e in EVENTOS):
        estado = ("hecha" if ev_id in hechas else
                  "perdida" if now > t + dt.timedelta(hours=ventana) else "pendiente")
        out.append({"id": ev_id, "etiqueta": ETIQUETA[ev_id], "estado": estado, "entrada": hechas.get(ev_id),
                    "prevista": (t + MARGEN).astimezone(MAD).strftime("%H:%M")})
    return out
