"""Checks that the code reproduces the formulas in Greene, Econometric Analysis (5th ed.).

Run with:  python -m pytest -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from carry_unwind import econometrics as E          # noqa: E402
from carry_unwind.config import TAU                 # noqa: E402
from carry_unwind.variables import fwd_implied_diff  # noqa: E402


@pytest.fixture(scope="module")
def ar_data():
    """Regression with AR(1) disturbances and heteroscedasticity."""
    rng = np.random.default_rng(0)
    T = 2000
    x = rng.normal(size=T)
    u = np.zeros(T)
    for t in range(1, T):
        u[t] = 0.5 * u[t - 1] + rng.normal() * (1 + 0.5 * abs(x[t]))
    y = 0.3 + 0.8 * x + u
    X = sm.add_constant(x)
    return y, X


def test_nw_lag_rule():
    assert E.nw_lags(5342) == 9          # smallest integer >= 5342^(1/4) = 8.55
    assert E.nw_lags(5342, 21) == 21     # overlap of 21 days dominates
    assert E.nw_lags(254) == 4


def test_newey_west_equals_greene_12_17(ar_data):
    y, X = ar_data
    L = 7
    fit = E.fit_hac(y, X, L)
    e = fit.resid
    T = len(e)
    S = (X * e[:, None]).T @ (X * e[:, None]) / T                     # S0
    for j in range(1, L + 1):
        w = 1 - j / (L + 1)
        G = (X[j:] * e[j:, None]).T @ (X[:-j] * e[:-j, None]) / T      # (1/T) sum e_t e_{t-j} x_t x'_{t-j}
        S += w * (G + G.T)
    XX_inv = np.linalg.inv(X.T @ X / T)
    V_greene = XX_inv @ S @ XX_inv / T                                 # Est.Asy.Var[b]
    assert np.allclose(V_greene, fit.cov_params(), rtol=1e-10, atol=1e-14)


def test_breusch_godfrey_matches_statsmodels(ar_data):
    from statsmodels.stats.diagnostic import acorr_breusch_godfrey
    y, X = ar_data
    ols = sm.OLS(y, X).fit()
    mine = E.breusch_godfrey(ols.resid, X, 5)
    lm, lmp, _, _ = acorr_breusch_godfrey(ols, nlags=5)                # zero-filled lags, T R^2
    assert np.isclose(mine["BG_LM"], lm, rtol=1e-8)
    assert np.isclose(mine["BG_p"], lmp, rtol=1e-6)
    assert mine["BG_p"] < 0.01                                         # AR(1) disturbances detected


def test_ljung_box_matches_formula_and_statsmodels(ar_data):
    from statsmodels.stats.diagnostic import acorr_ljungbox
    y, X = ar_data
    e = sm.OLS(y, X).fit().resid
    mine = E.ljung_box(e, 10)
    sm_q = acorr_ljungbox(e, lags=[10], return_df=True)["lb_stat"].iloc[0]
    assert np.isclose(mine["LB_Q"], sm_q, rtol=1e-8)


def test_arch_lm_matches_statsmodels(ar_data):
    from statsmodels.stats.diagnostic import het_arch
    rng = np.random.default_rng(1)
    T, e = 3000, np.zeros(3000)
    h = np.ones(T)
    for t in range(1, T):                                              # GARCH-type data
        h[t] = 0.1 + 0.3 * e[t - 1] ** 2 + 0.6 * h[t - 1]
        e[t] = np.sqrt(h[t]) * rng.normal()
    mine = E.arch_lm(e, 5)
    lm, lmp, _, _ = het_arch(e, nlags=5)
    assert np.isclose(mine["ARCH_LM"], lm, rtol=1e-6)
    assert mine["ARCH_p"] < 0.01


def test_forward_implied_differential_signs():
    S, iu, ij, ia = 150.0, 0.05, 0.01, 0.04
    # USDJPY, USD base: F = S (1 + iJPY tau)/(1 + iUSD tau)
    F = S * (1 + ij * TAU) / (1 + iu * TAU)
    d = fwd_implied_diff(pd.Series([(F - S) * 100]), pd.Series([S]), 100.0, True).iloc[0]
    assert np.isclose(d, (ij - iu) * 100, rtol=0.02)                   # about -4 points
    # AUDUSD, USD quote currency: F = S (1 + iUSD tau)/(1 + iAUD tau)
    Sa = 0.66
    Fa = Sa * (1 + iu * TAU) / (1 + ia * TAU)
    da = fwd_implied_diff(pd.Series([(Fa - Sa) * 1e4]), pd.Series([Sa]), 1e4, False).iloc[0]
    assert np.isclose(da, (ia - iu) * 100, rtol=0.02)                  # about -1 point


def test_future_sum_alignment():
    r = pd.Series(np.arange(10, dtype=float))
    fs = E._future_sum(r, 3) / 100
    assert fs.iloc[0] == 1 + 2 + 3                                      # r_{t+1}+r_{t+2}+r_{t+3}
    assert np.isnan(fs.iloc[-1])


def test_rule_uses_only_past_information():
    rng = np.random.default_rng(2)
    idx = pd.bdate_range("2010-01-01", periods=600)
    B = pd.DataFrame({"ret": rng.normal(0, 0.01, 600), "rr": rng.normal(0, 1, 600)}, index=idx)
    _, _, ruled1 = E.risk_reversal_rule(B)
    B2 = B.copy()
    B2.iloc[-1, B2.columns.get_loc("rr")] = 1e6                         # shock on the last day only
    _, _, ruled2 = E.risk_reversal_rule(B2)
    assert np.allclose(ruled1.to_numpy(), ruled2.to_numpy())


def test_probit_fit_measures_follow_greene():
    rng = np.random.default_rng(3)
    n = 3000
    x = rng.normal(size=(n, 2))
    y = (0.5 * x[:, 0] - 0.3 * x[:, 1] + rng.normal(size=n) > 1.2).astype(int)
    X = sm.add_constant(x)
    res = sm.Probit(y, X).fit(disp=0)
    p = y.mean()
    lnL0 = n * (p * np.log(p) + (1 - p) * np.log(1 - p))               # (21-28)
    assert np.isclose(res.llnull, lnL0)
    assert np.isclose(1 - res.llf / lnL0, res.prsquared)               # McFadden LRI
    assert np.isclose(2 * (res.llf - lnL0), res.llr)                   # LR statistic
    b, V = res.params[1:], res.cov_params()[1:, 1:]
    W = b @ np.linalg.solve(V, b)                                      # (21-27)
    assert W > stats.chi2.ppf(0.99, 2)
