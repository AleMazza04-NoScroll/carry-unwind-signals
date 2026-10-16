#!/usr/bin/env python3
"""Run the full study.

    python run_analysis.py --data-dir "path/to/bloomberg exports" --results-dir results

The data folder must contain the Bloomberg history exports listed in data/tickers.csv.
Raw data are never written to the results folder.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from carry_unwind import econometrics as E          # noqa: E402
from carry_unwind import figures as F               # noqa: E402
from carry_unwind.config import (GRANGER_LAGS, HORIZONS, LONG_SAMPLE_PAIRS,  # noqa: E402
                                 PROBIT_TAILS, WEEK)
from carry_unwind.io import load_all                # noqa: E402
from carry_unwind.variables import build_basket, build_panel  # noqa: E402


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    def fmt(v):
        if isinstance(v, (bool, np.bool_)):
            return "yes" if v else "no"
        if isinstance(v, (float, np.floating)):
            return f"{v:.{digits}f}"
        return str(v)
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    out += ["| " + " | ".join(fmt(r[c]) for c in cols) + " |" for _, r in df.iterrows()]
    return "\n".join(out)


def default_data_dir() -> Path:
    home = Path.home()
    for c in [home / "Desktop" / "carry trade", home / "OneDrive" / "Desktop" / "carry trade"]:
        if c.exists():
            return c
    return home / "Desktop" / "carry trade"


def probit_block(B):
    summaries, coefs, mfxs, main_fit = [], [], [], None
    for tail in PROBIT_TAILS:
        for controls in (False, True):
            for off in range(WEEK):
                s, c, m, fitted, yb = E.probit_tail(B, tail, controls, off)
                summaries.append(s)
                if off == 0:
                    tag = f"tail={tail:.0%}, controls={'VIX' if controls else 'none'}"
                    coefs.append(c.assign(spec=tag).reset_index(names="variable"))
                    mfxs.append(m.assign(spec=tag).reset_index(names="variable"))
                    if tail == PROBIT_TAILS[0] and not controls:
                        main_fit = (fitted, yb)
    psum = pd.DataFrame(summaries)
    rob = (psum.groupby(["tail", "controls"])
           .agg(LR_p_min=("LR_p", "min"), LR_p_median=("LR_p", "median"), LR_p_max=("LR_p", "max"),
                grids_with_LR_p_below_5pct=("LR_p", lambda x: int((x < 0.05).sum())),
                LRI_mean=("LRI_McFadden", "mean")).reset_index())
    return psum, pd.concat(coefs), pd.concat(mfxs), rob, main_fit


def granger_summary(gr):
    pref = gr[gr["preferred"]]
    rng = (gr.groupby("hypothesis_tested", sort=False)
           .agg(Wald_p_min=("Wald_p", "min"), Wald_p_max=("Wald_p", "max")).reset_index())
    return pref, rng


def lead_lag_line(cc):
    k0 = cc.loc[cc["k"] == 0, "corr"].iloc[0]
    k1 = cc.loc[cc["k"] == 1, "corr"].iloc[0]
    kneg = cc.loc[cc["k"] < 0, "corr"].abs().max()
    return (f"k = 0: {k0:.3f}; k = 1: {k1:.3f}; largest absolute value for k < 0: {kneg:.3f}; "
            f"approximate 95% band: +/- {cc['naive_95pct_band'].iloc[0]:.3f}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=default_data_dir())
    ap.add_argument("--results-dir", type=Path, default=Path(__file__).resolve().parent / "results")
    a = ap.parse_args()
    if not a.data_dir.exists():
        sys.exit(f"Data folder not found: {a.data_dir}. Use --data-dir.")
    figs, tabs = a.results_dir / "figures", a.results_dir / "tables"
    figs.mkdir(parents=True, exist_ok=True)
    tabs.mkdir(parents=True, exist_ok=True)

    print(f"Reading {a.data_dir}")
    S, meta = load_all(a.data_dir)
    meta.to_csv(tabs / "00_data_coverage.csv", index=False)
    P = build_panel(S)
    B = build_basket(P)
    BL = build_basket(P, LONG_SAMPLE_PAIRS)
    print(f"Main basket {B.index[0].date()} to {B.index[-1].date()} ({len(B)} days); "
          f"long basket {BL.index[0].date()} to {BL.index[-1].date()} ({len(BL)} days)")

    # 1. Stationarity
    adf = E.adf_table({
        "basket return": B["ret"], "basket carry-to-risk (level)": B["ctr"],
        "change in basket carry-to-risk (5d)": B["ctr"].diff(5),
        "daily change in basket carry-to-risk": B["ctr"].diff(),
        "basket risk reversal (level)": B["rr"], "change in basket risk reversal (5d)": B["rr"].diff(5),
        "daily change in basket risk reversal": B["rr"].diff(),
        "VIX (level)": B["vix"], "change in VIX (5d)": B["vix"].diff(5),
        **{f"carry-to-risk {p} (level)": P["ctr"][p].loc[B.index[0]:] for p in P["ctr"].columns},
    })
    adf.to_csv(tabs / "01_adf_tests.csv", index=False)

    # 2. Predictive regressions
    reg, reg_rob, diag = E.predictive_regressions(B, HORIZONS)
    reg.to_csv(tabs / "02_predictive_regressions.csv", index=False)
    reg_rob.to_csv(tabs / "02b_nonoverlapping_robustness.csv", index=False)
    diag.to_csv(tabs / "03_residual_diagnostics.csv", index=False)
    pp = E.per_pair_regressions(P, B.index[0])
    pp.to_csv(tabs / "04_per_pair_regressions.csv", index=False)

    # 3. Lead-lag and Granger causality
    cc = E.cross_correlation(B)
    cc.to_csv(tabs / "05_lead_lag_correlations.csv", index=False)
    gr = E.granger_table(B, GRANGER_LAGS)
    gr.to_csv(tabs / "06_granger_causality.csv", index=False)
    gr_pref, gr_rng = granger_summary(gr)

    # 4. Probit
    psum, pcoef, pmfx, prob_rob, main_fit = probit_block(B)
    psum.to_csv(tabs / "07_probit_summary.csv", index=False)
    pcoef.to_csv(tabs / "08_probit_coefficients.csv", index=False)
    pmfx.to_csv(tabs / "09_probit_marginal_effects.csv", index=False)

    # 5. Descriptive
    ev_tab, events, thr = E.find_unwinds(B["ret"])
    ev_tab.to_csv(tabs / "10_unwind_episodes.csv", index=False)
    paths, used = E.event_paths(B, events)
    rule_tab, base, ruled = E.risk_reversal_rule(B)
    rule_tab.to_csv(tabs / "11_risk_reversal_rule.csv")

    # 6. Robustness: two-pair basket with a longer continuous sample
    regL, regL_rob, _ = E.predictive_regressions(BL, HORIZONS)
    regL.to_csv(tabs / "12_long_sample_predictive_regressions.csv", index=False)
    grL = E.granger_table(BL, GRANGER_LAGS)
    grL.to_csv(tabs / "13_long_sample_granger.csv", index=False)
    grL_pref, grL_rng = granger_summary(grL)
    psumL, _, _, probL_rob, _ = probit_block(BL)
    psumL.to_csv(tabs / "14_long_sample_probit_summary.csv", index=False)
    evL, _, thrL = E.find_unwinds(BL["ret"])
    evL.to_csv(tabs / "15_long_sample_unwind_episodes.csv", index=False)
    ccL = E.cross_correlation(BL)
    ruleL, _, _ = E.risk_reversal_rule(BL)
    ruleL.to_csv(tabs / "16_long_sample_rule.csv")

    # 7. Figures
    F.policy_rates(S, figs)
    F.usdjpy_panels(P, figs)
    F.implied_vs_realised(P, figs)
    F.basket(B, events, figs)
    if paths is not None:
        F.event_study(paths, len(used), figs)
    F.cross_corr(cc, figs)
    F.rule(base, ruled, figs)
    F.probit_fit(*main_fit, PROBIT_TAILS[0], figs)

    # 8. Summary
    iv = P["vol"]["USDJPY"]
    rv_fwd = (P["logret"]["USDJPY"].rolling(63).std() * np.sqrt(252) * 100).shift(-63)
    prem = (iv - rv_fwd).loc["2000":].dropna()
    last = P["spot"].index[-1]
    m3 = ["horizon", "regressor", "L", "coef", "z", "p_value", "R2", "N"]
    gcols = ["hypothesis_tested", "lags", "N", "Wald_HAC", "Wald_p", "F_classical", "F_p", "BG_LM", "BG_p"]
    md = [
        "# Results",
        "",
        f"Main basket: USD/JPY, AUD/JPY, NZD/JPY, GBP/JPY, CAD/JPY, equal weights, "
        f"{B.index[0].date()} to {B.index[-1].date()} ({len(B)} trading days). The sample starts after the "
        "last gap longer than seven calendar days in the Bloomberg history of the cross-currency options. "
        f"Robustness basket: USD/JPY and AUD/JPY, {BL.index[0].date()} to {BL.index[-1].date()} ({len(BL)} days). "
        "Section and equation numbers refer to Greene, *Econometric Analysis*, 5th edition. "
        "All numbers are produced by `run_analysis.py`.",
        "",
        "## Latest values, USD/JPY",
        "",
        md_table(pd.DataFrame([
            {"item": "date", "value": str(last.date())},
            {"item": "3M implied volatility (ATM, %)", "value": f"{iv.iloc[-1]:.2f}"},
            {"item": "forward-implied differential, USD minus JPY (% p.a.)", "value": f"{P['diff']['USDJPY'].iloc[-1]:.2f}"},
            {"item": "carry-to-risk, forward-implied", "value": f"{P['ctr']['USDJPY'].iloc[-1]:.2f}"},
            {"item": "carry-to-risk, policy rates", "value": f"{P['ctr_policy'].iloc[-1]:.2f}"},
            {"item": "risk reversal 25D 3M, sign of Galati, Heath and McGuire (2007)", "value": f"{P['rr']['USDJPY'].iloc[-1]:.2f}"},
            {"item": "implied minus subsequent 63-day realised volatility, mean since 2000 (vol points)", "value": f"{prem.mean():.2f}"},
            {"item": "share of days with implied above subsequent realised, since 2000", "value": f"{(prem > 0).mean():.0%}"},
        ])),
        "",
        "## 1. Unit root tests (Greene 20.3.4), constant included, lags chosen by AIC",
        "",
        "The level of the carry-to-risk ratio does not reject a unit root, so it appears only in charts. "
        "Every regressor used for inference is a change, and every change rejects a unit root.",
        "",
        md_table(adf),
        "",
        "## 2. Predictive regressions, model M3",
        "",
        "Dependent variable: basket return over the next h days, in per cent. Regressors: 5-day changes in "
        "carry-to-risk and risk reversal, standardised. Newey-West errors (eq. 12-17), "
        "L = max(h, ceil(T^(1/4))), cover the MA(h-1) structure of overlapping sums.",
        "",
        md_table(reg[reg["model"] == "M3"][m3]),
        "",
        "Non-overlapping subsamples, one per starting day, Newey-West with L = ceil(N^(1/4)):",
        "",
        md_table(reg_rob[reg_rob["model"] == "M3"].drop(columns=["model"])),
        "",
        "## 3. Residual diagnostics",
        "",
        "Breusch-Godfrey LM, P = 5 (eq. 12-20); Ljung-Box Q, P = 10 (eq. 12-22); ARCH LM, q = 5 (11.8.4).",
        "",
        md_table(diag),
        "",
        "## 4. Lead-lag correlation, daily basket return and daily change in the risk reversal",
        "",
        lead_lag_line(cc),
        "",
        "## 5. Granger causality (Greene 19.6.5), Wald tests with Newey-West covariance",
        "",
        "Lag order: the smallest p in {5, 10, 15, 20, 25, 30} whose residuals pass the Breusch-Godfrey "
        "test, because autocorrelation with a lagged dependent variable makes OLS inconsistent "
        "(Greene p. 266).",
        "",
        md_table(gr_pref[gcols]),
        "",
        "Range of Wald p-values over the six lag orders:",
        "",
        md_table(gr_rng),
        "",
        "## 6. Probit for tail weeks (Greene 21.4), non-overlapping weeks",
        "",
        "Outcome: the basket return over the next five days is in the worst 5% (or 10%) of weeks. "
        "Regressors: 5-day changes in carry-to-risk and risk reversal, standardised, and with controls "
        "the 5-day change in the VIX. Each specification is estimated on the five weekly grids "
        "(starting days); a result found on a minority of grids is not robust.",
        "",
        md_table(prob_rob),
        "",
        "First grid, fit measures (21.4.5) and tests (21.4.3):",
        "",
        md_table(psum[psum["offset"] == 0].drop(columns=["offset"])),
        "",
        "First grid, marginal effects at the means with delta-method errors (21.4.2):",
        "",
        md_table(pmfx[["spec", "variable", "marginal_effect_at_means", "se_delta", "z", "p_value"]]),
        "",
        "## 7. Unwind episodes (descriptive)",
        "",
        f"First day of each cluster of 5-day basket returns at or below {thr * 100:.2f}% "
        "(worst 1% of days), clusters separated by more than 60 trading days.",
        "",
        md_table(ev_tab),
        "",
        "## 8. Risk reversal exposure rule (one threshold, fixed ex ante)",
        "",
        md_table(rule_tab.reset_index(names="strategy"), 2),
        "",
        "## 9. Robustness: USD/JPY and AUD/JPY basket, longer sample",
        "",
        "Predictive regressions, model M3:",
        "",
        md_table(regL[regL["model"] == "M3"][m3]),
        "",
        "Granger causality, preferred lag order:",
        "",
        md_table(grL_pref[gcols]),
        "",
        "Probit across the five weekly grids:",
        "",
        md_table(probL_rob),
        "",
        "Lead-lag correlation: " + lead_lag_line(ccL),
        "",
        f"Unwind episodes (threshold {thrL * 100:.2f}%):",
        "",
        md_table(evL),
        "",
        "Exposure rule:",
        "",
        md_table(ruleL.reset_index(names="strategy"), 2),
        "",
    ]
    (a.results_dir / "RESULTS.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Done. Results in {a.results_dir}")


if __name__ == "__main__":
    main()
