"""Estimators and tests. Section and equation numbers refer to
W. H. Greene, Econometric Analysis, 5th edition (2003)."""
from __future__ import annotations

import warnings
from math import ceil

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.stattools import adfuller

from .config import (ARCH_LAGS, BG_LAGS, EVENT_WIN, LB_LAGS, PAIRS, RULE_HAIRCUT,
                     RULE_PCTL, RULE_WINDOW, UNWIND_GAP, UNWIND_PCTL, WEEK)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def nw_lags(T: int, h: int = 1) -> int:
    """Newey-West truncation lag.

    Greene (12.5.2, p. 267): L must be large enough that autocorrelations beyond L
    are negligible, and current practice is the smallest integer >= T^(1/4).
    A sum of h overlapping one-day returns has an MA(h-1) error by construction,
    so L is never set below h.
    """
    return max(h, int(ceil(T ** 0.25)))


def standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Z-scores. A pure rescaling, it leaves t-ratios and fit unchanged."""
    return (df - df.mean()) / df.std()


def fit_hac(y, X, L):
    """OLS with the Newey-West covariance of Greene eq. (12-17): Bartlett weights
    w_j = 1 - j/(L+1), no degrees-of-freedom correction, normal critical values."""
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": L, "use_correction": False})


def fit_white(y, X):
    """OLS with White's heteroscedasticity-consistent covariance (Greene 11.2.3)."""
    return sm.OLS(y, X).fit(cov_type="HC0")


# ----------------------------------------------------------------------------
# Residual diagnostics, written as in Greene
# ----------------------------------------------------------------------------
def breusch_godfrey(resid, exog, P: int = BG_LAGS) -> dict:
    """LM = T * e'X0(X0'X0)^-1 X0'e / e'e, eq. (12-20). X0 is X augmented with P
    lagged residuals; missing initial lags are filled with zeros (Greene p. 269 notes
    that software differs on this point: here the zero-fill convention is used).
    Valid also with lagged dependent variables (12.7.4)."""
    e = np.asarray(resid, dtype=float)
    X = np.asarray(exog, dtype=float)
    lags = np.column_stack([np.r_[np.zeros(j), e[:-j]] for j in range(1, P + 1)])
    Z = np.column_stack([X, lags])
    fitted = sm.OLS(e, Z).fit().fittedvalues
    lm = len(e) * (fitted @ fitted) / (e @ e)
    return {"BG_LM": lm, "BG_df": P, "BG_p": stats.chi2.sf(lm, P)}


def ljung_box(resid, P: int = LB_LAGS) -> dict:
    """Q' = T(T+2) sum_j r_j^2 / (T-j), eq. (12-22), with
    r_j = sum_t e_t e_{t-j} / sum_t e_t^2 as in (12-21)."""
    e = np.asarray(resid, dtype=float)
    T = len(e)
    den = e @ e
    r = np.array([(e[j:] @ e[:-j]) / den for j in range(1, P + 1)])
    q = T * (T + 2) * np.sum(r ** 2 / (T - np.arange(1, P + 1)))
    return {"LB_Q": q, "LB_df": P, "LB_p": stats.chi2.sf(q, P)}


def arch_lm(resid, q: int = ARCH_LAGS) -> dict:
    """ARCH(q) LM test, Greene 11.8.4 (p. 244): TR^2 from the regression of e_t^2 on a
    constant and q lags of e_t^2, chi-squared with q degrees of freedom."""
    e2 = np.asarray(resid, dtype=float) ** 2
    y = e2[q:]
    X = sm.add_constant(np.column_stack([e2[q - j:-j] for j in range(1, q + 1)]))
    aux = sm.OLS(y, X).fit()
    lm = len(y) * aux.rsquared
    return {"ARCH_LM": lm, "ARCH_df": q, "ARCH_p": stats.chi2.sf(lm, q)}


def diagnostics(fit) -> dict:
    out = {}
    out.update(breusch_godfrey(fit.resid, fit.model.exog))
    out.update(ljung_box(fit.resid))
    out.update(arch_lm(fit.resid))
    return out


# ----------------------------------------------------------------------------
# Stationarity (Greene 12.4: the ergodic theorem needs stationarity and ergodicity;
# 20.3.4: Dickey-Fuller tests)
# ----------------------------------------------------------------------------
def adf_table(series: dict) -> pd.DataFrame:
    rows = []
    for name, s in series.items():
        s = s.dropna()
        with warnings.catch_warnings():   # tuple return kept for compatibility with statsmodels 0.14
            warnings.simplefilter("ignore", FutureWarning)
            stat, p, lag, nobs, crit, _ = adfuller(s, regression="c", autolag="AIC")
        rows.append({"series": name, "ADF_stat": stat, "p_value": p, "lags_AIC": lag,
                     "N": nobs, "crit_5pct": crit["5%"],
                     "unit_root_rejected_5pct": bool(stat < crit["5%"])})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Predictive regressions
# ----------------------------------------------------------------------------
# Regressors are 5-day changes. The level of the carry-to-risk ratio fails the
# Dickey-Fuller test (see results), and Greene 12.4 requires stationary, ergodic
# regressors for the asymptotic results used here; differencing restores stationarity.
SIGNALS = ["dCTR_5d", "dRR_5d"]
MODELS = {"M1": ["dCTR_5d"], "M2": ["dRR_5d"], "M3": SIGNALS}


def signals(ctr: pd.Series, rr: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"dCTR_5d": ctr.diff(5), "dRR_5d": rr.diff(5)})


def _future_sum(ret: pd.Series, h: int) -> pd.Series:
    """r_{t+1} + ... + r_{t+h}, in per cent."""
    return ret.rolling(h).sum().shift(-h) * 100


def predictive_regressions(B: pd.DataFrame, horizons):
    """Main estimates use every day (overlapping sums) with Newey-West errors.
    Robustness: for h > 1, the h non-overlapping subsamples (one per starting day),
    each with Newey-West errors and L = ceil(N^(1/4)), because the residual tests
    show that non-overlapping residuals are not always free of autocorrelation."""
    reg = standardize(signals(B["ctr"], B["rr"]))
    rows, rob_rows, diag_rows = [], [], []
    for h in horizons:
        y = _future_sum(B["ret"], h).rename("y")
        for m, cols in MODELS.items():
            df = pd.concat([y, reg[cols]], axis=1).dropna()
            X = sm.add_constant(df[cols])
            L = nw_lags(len(df), h)
            f = fit_hac(df["y"], X, L)
            for c in cols:
                rows.append({"horizon": h, "model": m, "regressor": c, "L": L,
                             "coef": f.params[c], "se": f.bse[c], "z": f.tvalues[c],
                             "p_value": f.pvalues[c], "R2": f.rsquared, "N": int(f.nobs)})
            if h == 1:
                ols = sm.OLS(df["y"], X).fit()
            else:
                zs = {c: [] for c in cols}
                for off in range(h):
                    sub = df.iloc[off::h]
                    fs = fit_hac(sub["y"], sm.add_constant(sub[cols]), nw_lags(len(sub)))
                    for c in cols:
                        zs[c].append(fs.tvalues[c])
                for c in cols:
                    z = np.array(zs[c])
                    rob_rows.append({"horizon": h, "model": m, "regressor": c, "subsamples": h,
                                     "N_each": len(df.iloc[::h]), "z_min": z.min(), "z_median": np.median(z),
                                     "z_max": z.max(), "share_abs_z_above_1.96": float((np.abs(z) > 1.96).mean())})
                sub = df.iloc[::h]
                ols = sm.OLS(sub["y"], sm.add_constant(sub[cols])).fit()
            d = {"horizon": h, "model": m, "sample": "all days" if h == 1 else "non-overlapping, first grid",
                 "N": int(ols.nobs)}
            d.update(diagnostics(ols))
            diag_rows.append(d)
    return pd.DataFrame(rows), pd.DataFrame(rob_rows), pd.DataFrame(diag_rows)


def per_pair_regressions(P: dict, start, horizons=(5, 21)) -> pd.DataFrame:
    rows = []
    for p in PAIRS:
        reg = standardize(signals(P["ctr"][p], P["rr"][p]).loc[start:])
        ret = P["ret"][p].loc[start:]
        for h in horizons:
            df = pd.concat([_future_sum(ret, h).rename("y"), reg], axis=1).dropna()
            L = nw_lags(len(df), h)
            f = fit_hac(df["y"], sm.add_constant(df[SIGNALS]), L)
            for c in SIGNALS:
                rows.append({"pair": p, "horizon": h, "regressor": c, "coef": f.params[c],
                             "z_NW": f.tvalues[c], "p_value": f.pvalues[c], "L": L,
                             "R2": f.rsquared, "N": int(f.nobs)})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Granger causality (Greene 19.6.5): single-equation regressions, Wald test
# ----------------------------------------------------------------------------
def granger(y: pd.Series, x: pd.Series, p: int) -> dict:
    df = pd.concat({"y": y, "x": x}, axis=1).dropna()
    cols = {}
    for i in range(1, p + 1):
        cols[f"y_l{i}"] = df["y"].shift(i)
    for i in range(1, p + 1):
        cols[f"x_l{i}"] = df["x"].shift(i)
    D = pd.concat([df["y"].rename("dep"), pd.DataFrame(cols)], axis=1).dropna()
    X = sm.add_constant(D.drop(columns="dep"))
    xl = [f"x_l{i}" for i in range(1, p + 1)]
    L = nw_lags(len(D))
    hac = fit_hac(D["dep"], X, L)
    b = hac.params[xl].to_numpy()
    V = hac.cov_params().loc[xl, xl].to_numpy()
    wald = float(b @ np.linalg.solve(V, b))                  # Wald statistic, as in (21-27)
    ols = sm.OLS(D["dep"], X).fit()
    R = np.zeros((p, X.shape[1]))
    for k, name in enumerate(xl):
        R[k, list(X.columns).index(name)] = 1.0
    ft = ols.f_test(R)
    out = {"lags": p, "N": len(D), "L": L, "Wald_HAC": wald, "Wald_df": p,
           "Wald_p": stats.chi2.sf(wald, p), "F_classical": float(np.squeeze(ft.fvalue)),
           "F_p": float(np.squeeze(ft.pvalue)), "sum_coef_x_lags": float(b.sum())}
    out.update({k: v for k, v in breusch_godfrey(ols.resid, X).items() if k != "BG_df"})
    return out


def granger_table(B: pd.DataFrame, lags) -> pd.DataFrame:
    r = B["ret"] * 100
    pairs = {
        "dRR -> return": (r, B["rr"].diff()),
        "return -> dRR": (B["rr"].diff(), r),
        "dCTR -> return": (r, B["ctr"].diff()),
        "return -> dCTR": (B["ctr"].diff(), r),
    }
    rows = []
    for name, (y, x) in pairs.items():
        cause, effect = name.split(" -> ")
        block = []
        for p in lags:
            d = {"hypothesis_tested": f"{cause} does not Granger-cause {effect}"}
            d.update(granger(y, x, p))
            d["BG_not_rejected_5pct"] = bool(d["BG_p"] > 0.05)
            block.append(d)
        # Greene p. 266: with a lagged dependent variable, autocorrelated disturbances make
        # OLS inconsistent. Preferred order: the smallest p whose residuals pass the BG test.
        ok = [d["lags"] for d in block if d["BG_not_rejected_5pct"]]
        pref = min(ok) if ok else max(lags)
        for d in block:
            d["preferred"] = d["lags"] == pref
        rows += block
    return pd.DataFrame(rows)


def cross_correlation(B: pd.DataFrame, kmax: int = 10) -> pd.DataFrame:
    d_rr = B["rr"].diff()
    out = pd.DataFrame({"k": range(-kmax, kmax + 1)})
    out["corr"] = [B["ret"].corr(d_rr.shift(-k)) for k in out["k"]]
    out["naive_95pct_band"] = 1.96 / np.sqrt(len(B))
    return out


# ----------------------------------------------------------------------------
# Probit for tail weeks (Greene 21.3-21.4)
# ----------------------------------------------------------------------------
def probit_tail(B: pd.DataFrame, tail: float, controls: bool = False, offset: int = 0):
    """Weekly non-overlapping sample: at every WEEK-th day t the regressors are known
    at t and the outcome is 1 if the basket return over t+1..t+5 is in the worst
    `tail` share of weeks. Non-overlapping weeks keep the likelihood's independence
    assumption plausible."""
    nxt = _future_sum(B["ret"], WEEK).rename("next_week")
    reg = signals(B["ctr"], B["rr"])
    if controls:
        reg["dVIX_5d"] = B["vix"].diff(5)
    df = pd.concat([nxt, reg], axis=1).dropna().iloc[offset::WEEK]
    thr = df["next_week"].quantile(tail)
    yb = (df["next_week"] <= thr).astype(int)
    cols = list(reg.columns)
    X = sm.add_constant(standardize(df[cols]))
    res = sm.Probit(yb, X).fit(disp=0)                       # Hessian-based covariance
    rob = sm.Probit(yb, X).fit(disp=0, cov_type="HC0")       # sandwich, Greene 21.4.1
    me = res.get_margeff(at="mean", method="dydx")          # delta method, 21.4.2
    sig = SIGNALS
    b = res.params[sig].to_numpy()
    V = res.cov_params().loc[sig, sig].to_numpy()
    wald = float(b @ np.linalg.solve(V, b))                  # eq. (21-27)
    lr = 2 * (res.llf - res.llnull)
    summary = {"tail": tail, "controls": controls, "offset": offset, "N": int(res.nobs),
               "events": int(yb.sum()), "threshold_pct": thr, "lnL": res.llf, "lnL0": res.llnull,
               "LRI_McFadden": 1 - res.llf / res.llnull, "LR_all_slopes": lr,
               "LR_df": len(cols), "LR_p": stats.chi2.sf(lr, len(cols)),
               "Wald_signals": wald, "Wald_signals_p": stats.chi2.sf(wald, 2)}
    coef = pd.DataFrame({"coef": res.params, "z": res.tvalues, "p_value": res.pvalues,
                         "z_sandwich": rob.tvalues, "p_sandwich": rob.pvalues})
    mfx = pd.DataFrame({"marginal_effect_at_means": me.margeff, "se_delta": me.margeff_se,
                        "z": me.tvalues, "p_value": me.pvalues}, index=cols)
    fitted = pd.Series(res.predict(X), index=df.index)
    return summary, coef, mfx, fitted, yb


# ----------------------------------------------------------------------------
# Descriptive tools
# ----------------------------------------------------------------------------
def find_unwinds(ret: pd.Series):
    r5 = ret.rolling(5).sum()
    thr = r5.quantile(UNWIND_PCTL)
    cand = r5[r5 <= thr].index
    pos = {d: i for i, d in enumerate(ret.index)}
    clusters, cur = [], []
    for d in cand:
        if cur and pos[d] - pos[cur[-1]] > UNWIND_GAP:
            clusters.append(cur)
            cur = []
        cur.append(d)
    if cur:
        clusters.append(cur)
    rows = []
    for c in clusters:
        w = r5.loc[c].idxmin()
        rows.append({"first_breach": c[0].date(), "worst_5d_date": w.date(),
                     "worst_5d_return_pct": round(float(r5.loc[w]) * 100, 2),
                     "days_below_threshold": len(c)})
    return pd.DataFrame(rows), [c[0] for c in clusters], float(thr)


def event_paths(B: pd.DataFrame, events):
    lo, hi = EVENT_WIN
    pos = {d: i for i, d in enumerate(B.index)}
    paths, used = {"ret": [], "rr": [], "ctr": []}, []
    for e in events:
        i = pos[e]
        if i + lo < 0 or i + hi >= len(B):
            continue
        sl = slice(i + lo, i + hi + 1)
        cum = (1 + B["ret"].iloc[sl]).cumprod().to_numpy()
        paths["ret"].append((cum / cum[0] - 1) * 100)
        paths["rr"].append(B["rr"].iloc[sl].to_numpy() - B["rr"].iloc[i + lo])
        paths["ctr"].append(B["ctr"].iloc[sl].to_numpy() - B["ctr"].iloc[i + lo])
        used.append(e)
    return {k: np.vstack(v) for k, v in paths.items()} if used else None, used


def perf(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    return {"ann_return_pct": r.mean() * 252 * 100, "ann_vol_pct": r.std() * np.sqrt(252) * 100,
            "sharpe": r.mean() / r.std() * np.sqrt(252),
            "max_drawdown_pct": (eq / eq.cummax() - 1).min() * 100}


def risk_reversal_rule(B: pd.DataFrame):
    """Halve exposure when yesterday's risk reversal exceeds its trailing 90th
    percentile. Only information available at t-1 is used."""
    rr, ret = B["rr"], B["ret"]
    q = rr.rolling(RULE_WINDOW).quantile(RULE_PCTL)
    valid = q.shift(1).notna()
    flag = (rr.shift(1) > q.shift(1)) & valid
    expo = 1 - (1 - RULE_HAIRCUT) * flag.astype(float)
    base, ruled = ret[valid], (ret * expo)[valid]
    tab = pd.DataFrame({"passive_basket": perf(base), "rr_rule": perf(ruled)}).T
    tab["share_days_reduced_pct"] = [0.0, float(flag[valid].mean() * 100)]
    return tab, base, ruled
