from __future__ import annotations

import datetime as dt
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .engine import HORIZONS, SIGNALS, TEST_FROM, deciles  # noqa: E402

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
                  base="#c3c2b7", s1="#2a78d6", s2="#eb6834"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a",
                 base="#383835", s1="#3987e5", s2="#d95926"),
}


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:+.{d}f}%"


def chart(dec: pd.DataFrame, path_base: str) -> None:
    for th, t in THEMES.items():
        fig, ax = plt.subplots(figsize=(8, 3.4), dpi=150)
        fig.patch.set_facecolor(t["surface"])
        ax.set_facecolor(t["surface"])
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(t["base"])
        ax.tick_params(colors=t["muted"], labelsize=8, length=0)
        ax.grid(axis="y", color=t["grid"], linewidth=0.8)
        ax.set_axisbelow(True)
        for k, (per, color, label) in enumerate((("exploracion", t["s1"], "Exploración"),
                                                  ("prueba", t["s2"], "Prueba"))):
            d = dec[dec["periodo"] == per]
            ax.bar(d["decil"] + (k - 0.5) * 0.38, d["mean"] * 100, width=0.36, color=color, label=label)
        ax.axhline(0, color=t["base"], linewidth=1)
        ax.set_xticks(range(1, 11))
        ax.set_xticklabels([f"D{i}" for i in range(1, 11)], color=t["ink2"])
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.1f}%")
        ax.set_xlabel("Decil de la reacción el día del anuncio (D1 = peor, D10 = mejor)", color=t["muted"], fontsize=8)
        ax.set_title("Retorno frente a SPY en las 20 sesiones siguientes a la entrada", loc="left",
                     color=t["ink"], fontsize=10)
        leg = ax.legend(frameon=False, fontsize=8, loc="upper left")
        for txt in leg.get_texts():
            txt.set_color(t["ink2"])
        fig.tight_layout()
        fig.savefig(f"{path_base}-{th}.png", facecolor=t["surface"])
        plt.close(fig)


def write(ev: pd.DataFrame, res: pd.DataFrame, path: str = "reports/pead.md") -> str:
    os.makedirs("reports", exist_ok=True)
    os.makedirs("assets", exist_ok=True)
    chart(deciles(ev), "assets/pead-deciles")
    test = ev[ev["periodo"] == "prueba"]
    passed = res[res["pasa"]]
    L = ["# Experimento 2: deriva tras resultados (PEAD)", "",
         f"Generado: {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC. Reglas fijadas antes de ver datos: "
         "[pre-registro](../docs/pead-preregistro.md). Simulación; no es asesoramiento financiero.", "",
         "## Veredicto", ""]
    if len(passed):
        L.append(f"**{len(passed)} combinación(es) pasan el criterio en la prueba** (≥ 1% neto, IC 95% > 0, "
                 "mejor que la referencia, n ≥ 50 y ya positiva en exploración). Con 48 combinaciones probadas, "
                 "es una pista que hay que confirmar en vivo:")
        for _, r in passed.iterrows():
            L.append(f"- {SIGNALS[r['senal']]} · {r['lado']} · {r['plazo']} sesiones · {r['version']}: "
                     f"{_p(r['prueba_media'])} neto por operación (n = {int(r['prueba_n'])}, IC {_p(r['prueba_lo'])} "
                     f"a {_p(r['prueba_hi'])}; referencia {_p(r['prueba_ref'])}).")
    else:
        L.append("**Ninguna combinación cumple el criterio en la prueba.** Con estas reglas y estos costes, "
                 "no hay ventaja demostrable de ≥ 1% neto por operación.")
    L += ["", "## Datos",
          f"- Eventos: {len(ev)} anuncios de {ev['ticker'].nunique()} empresas, "
          f"{ev['reaccion'].min():%Y-%m-%d} → {ev['reaccion'].max():%Y-%m-%d}.",
          f"- Prueba (desde {TEST_FROM:%d-%m-%Y}): {len(test)} anuncios.",
          f"- Hora del anuncio: " + ", ".join(f"{k} {v}" for k, v in ev['hora'].value_counts().items()) + ".",
          f"- Con sorpresa de BPA disponible: {100 * ev['sorpresa_pct'].notna().mean():.0f}%.",
          "- Sesgo de supervivencia: solo empresas que hoy están en los índices. Las comparaciones con la "
          "referencia (todos los anuncios del mismo universo) lo compensan en parte.", "",
          "## Gráfica de deciles",
          "Si la deriva existe, las barras deberían subir de izquierda a derecha.", "",
          '<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/pead-deciles-dark.png">'
          '<img alt="Retorno por decil de reacción" src="../assets/pead-deciles-light.png" width="100%"></picture>', ""]
    top = res[res["prueba_n"].fillna(0) >= 50].sort_values("prueba_media", ascending=False).head(10)
    head = ("| Señal | Lado | Plazo | Versión | n prueba | Neto medio prueba (IC 95%) | Acierto | Fact. benef. "
            "| Referencia | Neto exploración | Pasa |")
    sep = "|---|---|--:|---|--:|--:|--:|--:|--:|--:|:-:|"

    def row(r):
        return (f"| {SIGNALS[r['senal']]} | {r['lado']} | {r['plazo']} | {r['version']} | "
                f"{int(r.get('prueba_n') or 0)} | {_p(r.get('prueba_media'))} ({_p(r.get('prueba_lo'))} a "
                f"{_p(r.get('prueba_hi'))}) | {100 * (r.get('prueba_acierto') or 0):.0f}% | "
                f"{(r.get('prueba_fb') or 0):.2f} | {_p(r.get('prueba_ref'))} | {_p(r.get('exploracion_media'))} | "
                f"{'✅' if r['pasa'] else '—'} |")
    L += ["## Las 10 mejores en prueba (n ≥ 50)", "", head, sep] + [row(r) for _, r in top.iterrows()]
    L += ["", "<details><summary>Las 48 combinaciones</summary>", "", head, sep] + [row(r) for _, r in res.iterrows()]
    L += ["", "</details>", "", "## Cómo leerlo",
          "- Neto: tras 0,10% de comisión ida y vuelta (+0,02% si se cubre con SPY).",
          "- \"Sola\": solo la acción. \"Cubierta\": la acción menos SPY (aísla el efecto de la empresa).",
          "- Referencia: el mismo lado y plazo comprando (o vendiendo) en todos los anuncios, sin filtrar.",
          "- Los anuncios del mismo día se solapan: el n efectivo es menor y los IC algo optimistas.", ""]
    text = "\n".join(L)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text
