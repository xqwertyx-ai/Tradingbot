"""Registro y evaluación automática de hipótesis (simulación).

Reglas (como en la bitácora del proyecto; todo con precios de cierre):
- Precio de referencia = último cierre al registrar.
- ACIERTO si un cierre posterior alcanza el objetivo (objetivo_pct) antes que el stop.
- FALLO si algún cierre posterior se mueve en contra >= invalidacion_pct.
- Al vencer el plazo sin lo anterior: EXPIRADA, puntuada por el signo del retorno.
- "operada" (desde v1.4) = valor esperado neto >= 1% y probabilidad >= 55; antes, confianza >= 60.
  El resto se registra igual para medir acierto y calibración.
- retorno es bruto; retorno neto = retorno − coste de ida y vuelta (coste_pct).
"""
from __future__ import annotations

import math
import os

import pandas as pd

from dashboard.universe import cost_pct

LEDGER = "data/dashboard/hipotesis.csv"
COLS = ["id", "fecha", "version", "ticker", "direccion", "horizonte_dias", "vence", "tesis",
        "disparador", "objetivo_pct", "invalidacion_pct", "confianza", "ev_pct", "coste_pct",
        "operada", "precio_ref",
        "estado", "acierto", "fecha_cierre", "precio_cierre", "retorno"]
VERSION = "v1.4"
OPERATE_THRESHOLD = 60


def load(path: str = LEDGER) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_csv(path, dtype={"fecha": str, "vence": str, "fecha_cierre": str})
    return pd.DataFrame(columns=COLS)


def save(df: pd.DataFrame, path: str = LEDGER) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.reindex(columns=COLS).to_csv(path, index=False)


def add(df: pd.DataFrame, hyps: list[dict], date: str, ref_prices: dict,
        version: str = VERSION) -> pd.DataFrame:
    rows = []
    for i, h in enumerate(hyps):
        price = ref_prices.get(h["ticker"])
        if price is None:
            continue
        vence = (pd.Timestamp(date) + pd.offsets.BDay(h["horizonte_dias"])).date().isoformat()
        rows.append({
            "id": f"{date}-{i + 1}", "fecha": date, "version": version,
            "ticker": h["ticker"], "direccion": h["direccion"],
            "horizonte_dias": h["horizonte_dias"], "vence": vence, "tesis": h.get("tesis", ""),
            "disparador": h.get("disparador", ""), "objetivo_pct": h.get("objetivo_pct"),
            "invalidacion_pct": h["invalidacion_pct"], "confianza": h["confianza"],
            "ev_pct": h.get("ev_pct"), "coste_pct": cost_pct(h["ticker"]),
            "operada": int(h["operable"]) if "operable" in h else int(h["confianza"] >= OPERATE_THRESHOLD),
            "precio_ref": price, "estado": "ABIERTA",
        })
    if not rows:
        return df
    new = pd.DataFrame(rows).reindex(columns=COLS)
    new = new[~new["id"].isin(df["id"])]  # idempotente si se reejecuta el mismo día
    return pd.concat([df, new], ignore_index=True) if len(df) else new


def evaluate(df: pd.DataFrame, series: dict[str, pd.DataFrame]) -> pd.DataFrame:
    # columnas vacías se leen como float; con pandas 2 no admiten texto después
    df = df.astype({"estado": object, "fecha_cierre": object, "acierto": object,
                    "precio_cierre": object, "retorno": object})
    for idx, h in df[df["estado"] == "ABIERTA"].iterrows():
        s = series.get(h["ticker"])
        if s is None:
            continue
        after = s[pd.to_datetime(s["date"]) > pd.Timestamp(h["fecha"])]
        sign = 1 if h["direccion"] == "alcista" else -1
        stop = float(h["invalidacion_pct"]) / 100
        target = h.get("objetivo_pct")
        target = float(target) / 100 if pd.notna(target) and target != "" else None
        for _, row in after.iterrows():
            ret = sign * (row["close"] / h["precio_ref"] - 1)
            d = str(row["date"])
            if target is not None and ret >= target:
                df.loc[idx, ["estado", "acierto"]] = ["ACIERTO", 1]
            elif ret <= -stop:
                df.loc[idx, ["estado", "acierto"]] = ["FALLO", 0]
            elif d >= h["vence"]:
                df.loc[idx, ["estado", "acierto"]] = ["EXPIRADA", int(ret > 0)]
            else:
                continue
            df.loc[idx, ["fecha_cierre", "precio_cierre", "retorno"]] = [d, row["close"], ret]
            break
    return df


def stats(df: pd.DataFrame) -> dict:
    closed = df[df["estado"].isin(["ACIERTO", "FALLO", "EXPIRADA"])]
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
            net = net_returns(sub)
            gains, losses = net[net > 0].sum(), -net[net < 0].sum()
            out[label] = {"n": n, "acierto": p, "lo": c - h, "hi": c + h,
                          "ret_medio": float(sub["retorno"].astype(float).mean()),
                          "ret_neto_medio": float(net.mean()),
                          "factor_beneficio": float(gains / losses) if losses > 0 else math.inf}
    return out


def net_returns(sub: pd.DataFrame) -> pd.Series:
    """Retorno neto por operación (fracción): bruto menos coste de ida y vuelta."""
    cost = sub["coste_pct"] if "coste_pct" in sub else pd.Series(index=sub.index, dtype=float)
    cost = cost.astype(float).fillna(sub["ticker"].map(cost_pct))
    return sub["retorno"].astype(float) - cost / 100
