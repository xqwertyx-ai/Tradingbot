"""Gráficas PNG de la portada, en versión clara y oscura.

Paleta: referencia del skill de dataviz. Sube = azul, baja = rojo (par divergente,
legible con daltonismo); el signo va siempre en la etiqueta, nunca solo en el color.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
                  grid="#e1e0d9", base="#c3c2b7", up="#2a78d6", down="#e34948", line="#2a78d6"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781",
                 grid="#2c2c2a", base="#383835", up="#3987e5", down="#e66767", line="#3987e5"),
}
OUT = "assets"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _style(ax, t):
    ax.set_facecolor(t["surface"])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(t["base"])
    ax.tick_params(colors=t["muted"], labelsize=9, length=0)
    ax.grid(axis="x", color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def day_map(rows: list[dict], theme: str, path: str) -> None:
    """Barras horizontales del cambio diario por activo, agrupadas."""
    t = THEMES[theme]
    rows = [r for r in rows if r["chg_1d"] is not None and not r.get("level")]
    groups = list(dict.fromkeys(r["group"] for r in rows))
    labels, vals = [], []
    for g in groups:
        grp = sorted([r for r in rows if r["group"] == g], key=lambda r: r["chg_1d"])
        if labels:
            labels.append("")
            vals.append(None)
        labels.append(g.upper())
        vals.append(None)
        for r in grp:
            labels.append(r["name"])
            vals.append(r["chg_1d"] * 100)
    n = len(labels)
    fig, ax = plt.subplots(figsize=(8, 0.28 * n + 0.8), dpi=150)
    fig.patch.set_facecolor(t["surface"])
    _style(ax, t)
    y = list(range(n))[::-1]
    span = max(abs(v) for v in vals if v is not None) or 1
    for yi, lab, v in zip(y, labels, vals):
        if v is None:
            ax.text(-span * 1.02, yi, lab, ha="left", va="center", fontsize=8.5,
                    color=t["muted"], fontweight="bold")
            continue
        ax.barh(yi, v, height=0.62, color=t["up"] if v >= 0 else t["down"])
        ax.text(v + (span * 0.02 if v >= 0 else -span * 0.02), yi, f"{v:+.1f}%",
                ha="left" if v >= 0 else "right", va="center", fontsize=8.5, color=t["ink2"])
    ax.set_yticks([yi for yi, v in zip(y, vals) if v is not None])
    ax.set_yticklabels([lab for lab, v in zip(labels, vals) if v is not None], color=t["ink"], fontsize=9)
    ax.axvline(0, color=t["base"], linewidth=1)
    ax.set_xlim(-span * 1.3, span * 1.3)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:+.0f}%")
    ax.set_title("Cambio en la última sesión", loc="left", color=t["ink"], fontsize=12, pad=10)
    fig.tight_layout()
    fig.savefig(path, facecolor=t["surface"])
    plt.close(fig)


def trends(panels: list[dict], theme: str, path: str) -> None:
    """Pequeños múltiplos: 6 meses de precio + media de 50 sesiones."""
    t = THEMES[theme]
    cols = 3
    nrows = (len(panels) + cols - 1) // cols
    fig, axes = plt.subplots(nrows, cols, figsize=(9, 2.3 * nrows), dpi=150)
    fig.patch.set_facecolor(t["surface"])
    for ax in axes.flat[len(panels):]:
        ax.set_visible(False)
    for ax, p in zip(axes.flat, panels):
        df = p["df"].copy()
        df["ma50"] = df["close"].rolling(50).mean()
        df = df.tail(126)
        x = pd.to_datetime(df["date"])
        _style(ax, t)
        ax.grid(axis="y", color=t["grid"], linewidth=0.8)
        ax.grid(axis="x", visible=False)
        ax.plot(x, df["ma50"], color=t["muted"], linewidth=1.2, linestyle=(0, (3, 2)))
        ax.plot(x, df["close"], color=t["line"], linewidth=2)
        ax.scatter([x.iloc[-1]], [df["close"].iloc[-1]], s=22, color=t["line"],
                   edgecolors=t["surface"], linewidths=1.5, zorder=3)
        chg = p["chg_1m"]
        sub = "" if chg is None else (f"{chg:+.2f} pts 1m" if p.get("level") else f"{100 * chg:+.1f}% 1m")
        ax.set_title(f"{p['name']}", loc="left", color=t["ink"], fontsize=10, pad=14)
        ax.text(0, 1.02, f"{p['trend']} · {sub}", transform=ax.transAxes, fontsize=8, color=t["ink2"])
        ax.tick_params(axis="x", labelsize=7)
        ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
        ax.xaxis.set_major_formatter(lambda v, _: MESES[matplotlib.dates.num2date(v).month - 1])
        ax.tick_params(axis="y", labelsize=7)
    fig.text(0.01, 0.005, "Línea continua: precio de cierre · discontinua: media de 50 sesiones",
             fontsize=8, color=t["muted"])
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, facecolor=t["surface"])
    plt.close(fig)


def track_record(closed: pd.DataFrame, theme: str, path: str) -> None:
    """Tasa de acierto acumulada de hipótesis cerradas frente al 50%."""
    t = THEMES[theme]
    d = closed.sort_values("fecha_cierre").reset_index(drop=True)
    rate = d["acierto"].astype(float).expanding().mean() * 100
    fig, ax = plt.subplots(figsize=(8, 2.6), dpi=150)
    fig.patch.set_facecolor(t["surface"])
    _style(ax, t)
    ax.grid(axis="y", color=t["grid"], linewidth=0.8)
    ax.grid(axis="x", visible=False)
    ax.axhline(50, color=t["muted"], linewidth=1, linestyle=(0, (3, 2)))
    ax.text(len(d), 51.5, "50% (azar)", ha="right", fontsize=8, color=t["muted"])
    ax.plot(range(1, len(d) + 1), rate, color=t["line"], linewidth=2)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Hipótesis cerradas", color=t["muted"], fontsize=8)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title("Acierto acumulado", loc="left", color=t["ink"], fontsize=11)
    fig.tight_layout()
    fig.savefig(path, facecolor=t["surface"])
    plt.close(fig)


def render_all(rows, panels, closed) -> dict:
    os.makedirs(OUT, exist_ok=True)
    made = {}
    for th in THEMES:
        day_map(rows, th, f"{OUT}/mapa-{th}.png")
        trends(panels, th, f"{OUT}/tendencias-{th}.png")
        if len(closed) >= 5:
            track_record(closed, th, f"{OUT}/historial-{th}.png")
            made["historial"] = True
    made["mapa"] = made["tendencias"] = True
    return made
