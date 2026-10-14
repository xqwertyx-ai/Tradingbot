"""Registro y evaluación automática de hipótesis (simulación).

Reglas (como en la bitácora del proyecto):
- Precio de referencia = último cierre al registrar.
- FALLO si algún cierre posterior se mueve en contra >= invalidacion_pct.
- Al vencer el plazo sin invalidación: EXPIRADA, puntuada por el signo del retorno.
- "operada" = confianza >= 60; el resto se registra igual para medir acierto.
"""
from __future__ import annotations

import math
import os

import pandas as pd

LEDGER = "data/dashboard/hipotesis.csv"
COLS = ["id", "fecha", "version", "ticker", "direccion", "horizonte_dias", "vence", "tesis",
        "disparador", "invalidacion_pct", "confianza", "operada", "precio_ref",
        "estado", "acierto", "fecha_cierre", "precio_cierre", "retorno"]
VERSION = "auto-1.0"
OPERATE_THRESHOLD = 60


def load(path: str = LEDGER) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_csv(path, dtype={"fecha": str, "vence": str, "fecha_cierre": str})
    return pd.DataFrame(columns=COLS)


def save(df: pd.DataFrame, path: str = LEDGER) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.reindex(columns=COLS).to_csv(path, index=False)


def add(df: pd.DataFrame, hyps: list[dict], date: str, ref_prices: dict) -> pd.DataFrame:
    rows = []
    for i, h in enumerate(hyps):
        price = ref_prices.get(h["ticker"])
        if price is None:
            continue
        vence = (pd.Timestamp(date) + pd.offsets.BDay(h["horizonte_dias"])).date().isoformat()
        rows.append({
            "id": f"{date}-{i + 1}", "fecha": date, "version": VERSION,
            "ticker": h["ticker"], "direccion": h["direccion"],
            "horizonte_dias": h["horizonte_dias"], "vence": vence, "tesis": h.get("tesis", ""),
            "disparador": h.get("disparador", ""), "invalidacion_pct": h["invalidacion_pct"],
            "confianza": h["confianza"], "operada": int(h["confianza"] >= OPERATE_THRESHOLD),
            "precio_ref": price, "estado": "ABIERTA",
        })
    if not rows:
        return df
    new = pd.DataFrame(rows).reindex(columns=COLS)
    new = new[~new["id"].isin(df["id"])]  # idempotente si se reejecuta el mismo día
    return pd.concat([df, new], ignore_index=True) if len(df) else new


def evaluate(df: pd.DataFrame, series: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = df.copy()
    for idx, h in df[df["estado"] == "ABIERTA"].iterrows():
        s = series.get(h["ticker"])
        if s is None:
            continue
        after = s[pd.to_datetime(s["date"]) > pd.Timestamp(h["fecha"])]
        sign = 1 if h["direccion"] == "alcista" else -1
        stop = float(h["invalidacion_pct"]) / 100
        for _, row in after.iterrows():
            ret = sign * (row["close"] / h["precio_ref"] - 1)
            d = str(row["date"])
            if ret <= -stop:
                df.loc[idx, ["estado", "acierto"]] = ["FALLO", 0]
            elif d >= h["vence"]:
                df.loc[idx, ["estado", "acierto"]] = ["EXPIRADA", int(ret > 0)]
            else:
                continue
            df.loc[idx, ["fecha_cierre", "precio_cierre", "retorno"]] = [d, row["close"], ret]
            break
    return df


def stats(df: pd.DataFrame) -> dict:
    closed = df[df["estado"].isin(["FALLO", "EXPIRADA"])]
    out = {"registradas": len(df), "abiertas": int((df["estado"] == "ABIERTA").sum()),
           "cerradas": len(closed)}
    for label, sub in (("todas", closed), ("operadas", closed[closed["operada"] == 1])):
        n = len(sub)
        if n:
            k = int(sub["acierto"].sum())
            p = k / n
            z = 1.96
            den = 1 + z * z / n
            c = (p + z * z / (2 * n)) / den
            h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
            out[label] = {"n": n, "acierto": p, "lo": c - h, "hi": c + h,
                          "ret_medio": float(sub["retorno"].astype(float).mean())}
    return out
