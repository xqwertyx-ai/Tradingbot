from __future__ import annotations

import datetime as dt
import os

import pandas as pd

from . import config as C
from .backtest import calibration, run, split_time


def _pct(x):
    return "—" if pd.isna(x) else f"{100 * x:.1f}%"


def _c(x):
    return "—" if pd.isna(x) else f"{100 * x:+.2f}"


def _row(name, s):
    if s.get("n", 0) == 0:
        return f"| {name} | 0 | — | — | — | — |"
    return (
        f"| {name} | {s['n']} | {_pct(s['hit'])} ({_pct(s['hit_lo'])}–{_pct(s['hit_hi'])}) "
        f"| {_pct(s['breakeven'])} | {_c(s['pnl_mean'])} ({_c(s['pnl_lo'])} a {_c(s['pnl_hi'])}) "
        f"| {s['pnl_total']:+.1f} |"
    )


def _date(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%Y-%m-%d %H:%M")


def write_report(df: pd.DataFrame, path: str = C.REPORT_PATH) -> str:
    results = run(df)
    train, test = split_time(df)
    usable = df.dropna(subset=["pm_up0", "ret_prev5"])
    lines = [
        "# Informe: mercados BTC 5 min de Polymarket",
        "",
        f"Generado: {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC. "
        "Simulación con datos históricos públicos; no es asesoramiento financiero.",
        "",
        "## Datos",
        f"- Mercados resueltos: {len(df)} ({_date(df.start_ts.min())} → {_date(df.start_ts.max())} UTC)",
        f"- Con precio de Polymarket y de BTC al inicio: {len(usable)}",
        f"- Exploración: {len(train)} mercados hasta {_date(train.start_ts.max())}; "
        f"prueba: {len(test)} mercados posteriores",
        f"- Frecuencia histórica de 'Up': {_pct(df.up_won.mean())}",
        "",
        "## Supuestos de coste",
        f"- Comisión taker: {C.FEE_RATE} × p × (1 − p) por acción "
        f"(≈ {100 * C.FEE_RATE * .25:.2f} céntimos a p = 0,50).",
        f"- Deslizamiento: {C.SLIPPAGE * 100:.0f} céntimo por acción sobre el precio de referencia.",
        "- Cada operación: 1 acción; paga 1 USDC si acierta.",
        "- Ejecución: primer precio de Polymarket igual o posterior a la señal "
        f"(retraso medio: {df[['delay1', 'delay2', 'delay3']].stack().mean():.0f} s). "
        "Nunca se usa un precio anterior a la señal.",
        "",
        "## Criterio de aprobado (fijado antes de ver los datos)",
        f"Una estrategia pasa solo si en el periodo de prueba tiene ≥ {C.MIN_TRADES_TEST} "
        "operaciones y el límite inferior del IC 95% del P&L medio por operación es > 0. "
        f"Se prueban {len(results)} reglas, así que alguna puede salir bien por azar: "
        "un aprobado aislado y por poco no basta.",
        "",
    ]
    for label, key in (("Prueba (lo que cuenta)", "test"), ("Exploración", "train")):
        lines += [
            f"## Resultados — {label}",
            "",
            "Acierto con IC 95%; 'Necesario' = acierto mínimo para cubrir precio, comisión y "
            "deslizamiento; P&L en céntimos por operación (IC 95%); total en USDC.",
            "",
            "| Estrategia | n | Acierto | Necesario | P&L medio (¢) | Total |",
            "|---|---|---|---|---|---|",
        ]
        lines += [_row(r["strategy"].name, r[key]) for r in results]
        lines.append("")

    passed = [r["strategy"].name for r in results if r["passed"]]
    lines += [
        "## Veredicto",
        (f"Pasan el criterio: {', '.join(passed)}. Siguiente paso: confirmarlo en simulación "
         "en vivo (forward test) antes de sacar conclusiones." if passed else
         "Ninguna regla supera el criterio. Con estos costes, no hay ventaja demostrable."),
        "",
        "## Calibración del mercado (minuto 2)",
        "Si la frecuencia real de 'Up' coincide con el precio, el mercado está bien calibrado "
        "y es difícil ganarle con reglas simples.",
        "",
        "| Tramo de precio Up | n | Precio medio | Frecuencia real Up |",
        "|---|---|---|---|",
    ]
    for _, r in calibration(df).iterrows():
        lines.append(f"| {r['bin']} | {r['n']} | {_pct(r['precio_medio'])} | {_pct(r['freq_up'])} |")
    lines += [
        "",
        "## Estrategias",
        *[f"- `{r['strategy'].name}` (entrada minuto {r['strategy'].entry_minute}): "
          f"{r['strategy'].description}" for r in results],
        "",
        "## Limitaciones",
        "- El precio histórico de Polymarket es un precio de referencia, no el precio al que "
        "realmente se habría ejecutado; el deslizamiento lo aproxima.",
        "- El histórico tiene ~1 precio por minuto, así que la ejecución simulada llega "
        "~20 s después de la señal. Un bot más rápido vería otros precios; esa ventaja "
        "de velocidad es justo la que tienen los bots de alta frecuencia.",
        "- No se modela la profundidad del libro: con importes grandes el coste sería mayor.",
        "- Las señales usan BTC-USD de Coinbase; el mercado resuelve con Chainlink. "
        "El resultado sí es el oficial de Polymarket.",
        "- Mercados consecutivos no son del todo independientes; los IC pueden ser algo optimistas.",
        "",
    ]
    text = "\n".join(lines)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text
