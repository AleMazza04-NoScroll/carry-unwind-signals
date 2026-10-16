"""Construction of the variables: rate differentials, carry-to-risk, risk reversals, returns."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FFILL_LIMIT, FWD_SPEC, MAX_GAP_DAYS, PAIRS, TARGET, TAU


def fwd_implied_diff(points: pd.Series, spot: pd.Series, scale: float, usd_is_base: bool) -> pd.Series:
    """i_ccy - i_USD, per cent per year, from three-month forward points.

    Covered interest parity with simple interest gives
        USD/XXX quote:  F/S - 1 = (i_XXX - i_USD) * tau / (1 + i_USD * tau)
        XXX/USD quote:  F/S - 1 = (i_USD - i_XXX) * tau / (1 + i_XXX * tau)
    The denominator is dropped (relative error of about i * tau, below 1.5% of the
    differential for rates under 6%). The result includes the cross-currency basis.
    """
    rel = (points / scale) / spot
    sign = 1.0 if usd_is_base else -1.0
    return sign * rel / TAU * 100


def build_panel(S: dict) -> dict:
    spot = pd.concat({p: S[p] for p in PAIRS}, axis=1).dropna()
    idx = spot.index

    def aligned(code):
        return S[code].reindex(idx).ffill(limit=FFILL_LIMIT)

    # Spot legs against the US dollar, rebuilt from the JPY crosses (same BGN timestamp)
    leg = {
        "JPY": spot["USDJPY"],                     # USDJPY
        "AUD": spot["AUDJPY"] / spot["USDJPY"],    # AUDUSD
        "NZD": spot["NZDJPY"] / spot["USDJPY"],    # NZDUSD
        "GBP": spot["GBPJPY"] / spot["USDJPY"],    # GBPUSD
        "CAD": spot["USDJPY"] / spot["CADJPY"],    # USDCAD
    }
    d = pd.DataFrame(index=idx)
    d["USD"] = 0.0
    for ccy, (tick, scale, usd_base) in FWD_SPEC.items():
        d[ccy] = fwd_implied_diff(aligned(tick), leg[ccy], scale, usd_base)

    diff = pd.DataFrame({p: d[TARGET[p]] - d["JPY"] for p in PAIRS})   # i_target - i_JPY
    vol = pd.DataFrame({p: aligned(p + "V3M") for p in PAIRS})
    # Galati, Heath and McGuire (2007): positive = hedging yen appreciation costs more.
    # Bloomberg quotes call minus put on the first currency, hence the minus sign.
    rr = -pd.DataFrame({p: aligned(p + "25R3M") for p in PAIRS})
    ctr = diff / vol

    fed = S["FDTR"].reindex(idx).ffill()
    boj = S["BOJDTR"].reindex(idx).ffill()
    ctr_policy = (fed - boj) / vol["USDJPY"]

    # Daily excess return of long target / short JPY: spot return plus carry accrued
    # on the differential known the previous day (ACT/360).
    days = idx.to_series().diff().dt.days
    ret = spot.pct_change() + diff.shift(1).mul(days, axis=0) / 100 / 360
    logret = np.log(spot).diff()
    vix = S["VIX"].reindex(idx).ffill(limit=FFILL_LIMIT)

    return dict(spot=spot, d=d, diff=diff, vol=vol, rr=rr, ctr=ctr, fed=fed, boj=boj,
                ctr_policy=ctr_policy, ret=ret, logret=logret, vix=vix)


def build_basket(P: dict, pairs=None) -> pd.DataFrame:
    """Equal-weighted basket on a continuous sample.

    Rolling sums and differences require consecutive observations. The sample starts
    on the first day after the last gap longer than MAX_GAP_DAYS calendar days in any
    of the basket's signals, so no rolling window spans a missing period.
    """
    pairs = pairs or PAIRS
    B = pd.DataFrame({
        "ret": P["ret"][pairs].mean(axis=1, skipna=False),
        "ctr": P["ctr"][pairs].mean(axis=1, skipna=False),
        "rr": P["rr"][pairs].mean(axis=1, skipna=False),
        "vix": P["vix"],
    }).dropna()
    gaps = B.index.to_series().diff().dt.days
    big = gaps[gaps > MAX_GAP_DAYS]
    if len(big):
        B = B.loc[big.index[-1]:]
    return B
