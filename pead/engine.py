"""Motor del experimento PEAD. Sigue el pre-registro (docs/pead-preregistro.md).

Sin información futura:
- La reacción se mide hasta el cierre de la sesión de reacción; se entra en la sesión siguiente.
- Los umbrales de "sorpresa grande" usan solo eventos de los 365 días anteriores.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

HORIZONS = (5, 10, 20, 40)
COST = 0.0010        # ida y vuelta en la acción
COST_HEDGE = 0.0002  # ida y vuelta en SPY
TEST_FROM = pd.Timestamp("2025-10-01")
WINDOW_DAYS = 365
MIN_PRIOR = 200
LO_Q, HI_Q = 10, 90


def _timing(hora: str) -> str:
    if not isinstance(hora, str) or hora == "00:00":
        return "desconocida"
    if hora >= "16:00":
        return "tras_cierre"
    if hora < "09:30":
        return "antes_apertura"
    return "desconocida"


def build_events(earn: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    days = px.index
    pos = {d: i for i, d in enumerate(days)}
    arr = px.to_numpy(dtype=float)
    col = {c: j for j, c in enumerate(px.columns)}
    spy = col["SPY"]
    rows = []
    for e in earn.itertuples(index=False):
        if e.ticker not in col:
            continue
        a = pd.Timestamp(e.fecha)
        t = _timing(e.hora)
        i_after = days.searchsorted(a, side="right")   # primera sesión > a
        i_from = days.searchsorted(a, side="left")      # primera sesión >= a
        if t == "tras_cierre":
            i_pre, i_r = i_after - 1, i_after
        elif t == "antes_apertura":
            i_pre, i_r = i_from - 1, i_from
        else:  # dos sesiones: el día del anuncio y la siguiente
            i_pre, i_r = i_from - 1, i_after
        i_e = i_r + 1
        # Si la reacción es la última sesión, la entrada (sesión siguiente) aún no existe: el evento se
        # guarda igualmente (entrada vacía) para poder anunciar la compra pendiente.
        if i_pre < 0 or i_r >= len(days):
            continue
        futura = i_e >= len(days)
        j = col[e.ticker]
        p_pre, p_r = arr[i_pre, j], arr[i_r, j]
        p_e = np.nan if futura else arr[i_e, j]
        if not (np.isfinite(p_pre) and np.isfinite(p_r) and (futura or np.isfinite(p_e))) or p_pre <= 0:
            continue
        ra = (p_r / p_pre - 1) - (arr[i_r, spy] / arr[i_pre, spy] - 1)
        row = {"ticker": e.ticker, "anuncio": a, "hora": t, "reaccion": days[i_r],
               "entrada": pd.NaT if futura else days[i_e], "ra": ra, "sorpresa_pct": e.sorpresa_pct}
        for h in HORIZONS:
            i_x = i_e + h
            if i_x < len(days) and np.isfinite(arr[i_x, j]):
                row[f"ret{h}"] = arr[i_x, j] / p_e - 1
                row[f"spy{h}"] = arr[i_x, spy] / arr[i_e, spy] - 1
            else:
                row[f"ret{h}"] = row[f"spy{h}"] = np.nan
        rows.append(row)
    ev = pd.DataFrame(rows)
    if ev.empty:
        return ev
    ev = ev.drop_duplicates(["ticker", "reaccion"]).sort_values("reaccion").reset_index(drop=True)
    return add_signals(ev)


def _trailing(ev: pd.DataFrame, value: str) -> pd.DataFrame:
    """Percentiles 10/90 y rango percentil de `value` con eventos de los 365 días previos."""
    t = ev["reaccion"].to_numpy()
    v = ev[value].to_numpy(dtype=float)
    lo = np.full(len(ev), np.nan)
    hi = np.full(len(ev), np.nan)
    rank = np.full(len(ev), np.nan)
    for d in np.unique(t):
        idx = np.where(t == d)[0]
        a = np.searchsorted(t, d - np.timedelta64(WINDOW_DAYS, "D"), side="left")
        b = np.searchsorted(t, d, side="left")   # estrictamente anteriores
        prior = v[a:b]
        prior = prior[np.isfinite(prior)]
        if len(prior) < MIN_PRIOR:
            continue
        lo[idx], hi[idx] = np.percentile(prior, [LO_Q, HI_Q])
        srt = np.sort(prior)
        rank[idx] = np.searchsorted(srt, v[idx], side="right") / len(srt)
    return pd.DataFrame({"lo": lo, "hi": hi, "rank": rank}, index=ev.index)


def add_signals(ev: pd.DataFrame) -> pd.DataFrame:
    ra = _trailing(ev, "ra")
    su = _trailing(ev, "sorpresa_pct")
    ev["ra_rank"] = ra["rank"]
    ev["ra_hi"] = ra["hi"]
    ev["sig_ra"] = np.where(ev["ra"] >= ra["hi"], 1, np.where(ev["ra"] <= ra["lo"], -1, 0))
    ev.loc[ra["lo"].isna(), "sig_ra"] = 0
    s = ev["sorpresa_pct"]
    ev["sig_bpa"] = np.where(s >= su["hi"], 1, np.where(s <= su["lo"], -1, 0))
    ev.loc[su["lo"].isna() | s.isna(), "sig_bpa"] = 0
    ev["sig_ambas"] = np.where((ev["sig_ra"] == ev["sig_bpa"]) & (ev["sig_ra"] != 0), ev["sig_ra"], 0)
    ev["periodo"] = np.where(ev["reaccion"] >= TEST_FROM, "prueba", "exploracion")
    return ev


def net_returns(sub: pd.DataFrame, side: int, h: int, hedged: bool) -> pd.Series:
    r = sub[f"ret{h}"] - (sub[f"spy{h}"] if hedged else 0)
    return side * r - (COST + (COST_HEDGE if hedged else 0))


def stats(x: pd.Series) -> dict:
    x = x.dropna()
    n = len(x)
    if n == 0:
        return {"n": 0, "media": math.nan, "lo": math.nan, "hi": math.nan, "acierto": math.nan, "fb": math.nan}
    m = x.mean()
    se = x.std(ddof=1) / math.sqrt(n) if n > 1 else math.nan
    gains, losses = x[x > 0].sum(), -x[x < 0].sum()
    return {"n": n, "media": m, "lo": m - 1.96 * se, "hi": m + 1.96 * se, "acierto": (x > 0).mean(),
            "fb": gains / losses if losses > 0 else math.inf}


SIGNALS = {"sig_ra": "Reacción anormal", "sig_bpa": "Sorpresa de BPA", "sig_ambas": "Ambas"}


def evaluate(ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sig in SIGNALS:
        for side, side_name in ((1, "compra"), (-1, "venta")):
            for h in HORIZONS:
                for hedged in (False, True):
                    rec = {"senal": sig, "lado": side_name, "plazo": h, "version": "cubierta" if hedged else "sola"}
                    for per in ("exploracion", "prueba"):
                        base = ev[(ev["periodo"] == per) & ev[f"ret{h}"].notna()]
                        trades = base[base[sig] == side]
                        s = stats(net_returns(trades, side, h, hedged))
                        b = stats(net_returns(base, side, h, hedged))
                        for k, v in s.items():
                            rec[f"{per}_{k}"] = v
                        rec[f"{per}_ref"] = b.get("media", math.nan)
                    t_ok = (rec.get("prueba_n", 0) >= 50 and rec.get("prueba_media", -1) >= 0.01
                            and rec.get("prueba_lo", -1) > 0
                            and rec.get("prueba_media", -1) > rec.get("prueba_ref", math.inf)
                            and rec.get("exploracion_media", -1) > 0)
                    rec["pasa"] = bool(t_ok)
                    rows.append(rec)
    return pd.DataFrame(rows)


def deciles(ev: pd.DataFrame, h: int = 20) -> pd.DataFrame:
    d = ev.dropna(subset=["ra_rank", f"ret{h}"]).copy()
    d["decil"] = np.minimum((d["ra_rank"] * 10).astype(int), 9) + 1
    d["anormal"] = d[f"ret{h}"] - d[f"spy{h}"]
    return d.groupby(["periodo", "decil"])["anormal"].agg(["mean", "count"]).reset_index()
