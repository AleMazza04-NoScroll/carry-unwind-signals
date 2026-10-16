"""Figures. Every chart carries the source line required for Bloomberg-derived data."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from .config import BOJ_UNWIND, EVENT_WIN, LEHMAN

NAVY, RED, GREY, GOLD, TEAL = "#1f3a5f", "#b5342f", "#6b7280", "#c28a1c", "#2a7f7f"
NOTE = "Source: Bloomberg (BGN). Author's calculations."

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.25, "axes.titleweight": "bold", "legend.frameon": False,
})


def _years(ax, step=2):
    ax.xaxis.set_major_locator(mdates.YearLocator(step))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def _episodes(ax, label=True):
    for d, lab in [(LEHMAN, "Lehman (Sep 2008)"), (BOJ_UNWIND, "BoJ unwind (5 Aug 2024)")]:
        ax.axvline(d, color=GREY, lw=0.8, ls="--", label=lab if label else None)


def _save(fig, path, note):
    fig.text(0.01, 0.005, note, fontsize=7, color=GREY)
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def policy_rates(S, out):
    fig, ax = plt.subplots(figsize=(9, 4))
    f, b = S["FDTR"].loc["2000":], S["BOJDTR"].loc["2000":]
    ax.step(f.index, f.values, where="post", color=NAVY, lw=1.6, label="Federal Reserve (fed funds target, upper bound)")
    ax.step(b.index, b.values, where="post", color=RED, lw=1.6, label="Bank of Japan (policy rate)")
    ax.set_ylabel("Per cent")
    ax.set_title("Policy rates of the Federal Reserve and the Bank of Japan")
    ax.legend(loc="upper right")
    _years(ax)
    _save(fig, out / "fig1_policy_rates.png", NOTE)


def usdjpy_panels(P, out):
    spot = P["spot"]["USDJPY"].loc["2000":]
    ctr_f, ctr_p = P["ctr"]["USDJPY"].loc["2000":], P["ctr_policy"].loc["2000":]
    rr = P["rr"]["USDJPY"].dropna()
    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True, gridspec_kw={"height_ratios": [1.1, 1, 1]})
    ax[0].plot(spot.index, spot.values, color=NAVY, lw=1.1)
    ax[0].set_ylabel("Yen per US dollar")
    ax[0].set_title("USD/JPY exchange rate")
    _episodes(ax[0])
    ax[0].legend(loc="upper left", fontsize=8)
    ax[1].plot(ctr_f.index, ctr_f.values, color=NAVY, lw=0.9, label="Forward-implied rate differential / 3M implied volatility")
    ax[1].plot(ctr_p.index, ctr_p.values, color=GOLD, lw=0.9, label="Policy-rate differential / 3M implied volatility")
    ax[1].axhline(0, color="black", lw=0.6)
    ax[1].set_ylim(-0.02, float(max(ctr_f.max(), ctr_p.max())) * 1.3)
    ax[1].set_ylabel("Ratio")
    ax[1].set_title("Carry-to-risk ratio, USD/JPY")
    _episodes(ax[1], False)
    ax[1].legend(loc="upper left", fontsize=8)
    ax[2].plot(rr.index, rr.values, color=RED, lw=0.9)
    ax[2].axhline(0, color="black", lw=0.6)
    ax[2].set_ylabel("Volatility points")
    ax[2].set_title("25-delta risk reversal, 3M (positive values: hedging yen appreciation costs more)")
    _episodes(ax[2], False)
    _years(ax[2])
    ax[2].set_xlim(spot.index[0], spot.index[-1])
    _save(fig, out / "fig2_usdjpy_carry_to_risk_risk_reversal.png",
          NOTE + " Risk reversal sign as in Galati, Heath and McGuire (2007).")


def implied_vs_realised(P, out):
    iv = P["vol"]["USDJPY"].loc["2000":]
    rv = (P["logret"]["USDJPY"].rolling(63).std() * np.sqrt(252) * 100).loc["2000":]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(iv.index, iv.values, color=NAVY, lw=1.0, label="3M implied volatility (ATM)")
    ax.plot(rv.index, rv.values, color=GOLD, lw=0.9, label="63-day realised volatility (trailing)")
    ax.set_ylabel("Per cent, annualised")
    ax.set_title("USD/JPY implied and realised volatility")
    ax.legend(loc="upper right")
    _years(ax)
    _save(fig, out / "fig3_usdjpy_implied_vs_realised.png", NOTE)


def basket(B, events, out):
    idx = 100 * (1 + B["ret"]).cumprod()
    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    ax[0].plot(idx.index, idx.values, color=NAVY, lw=1.1)
    ax[0].set_title("JPY-funded carry basket, cumulative excess return (equal weights, index = 100)")
    ax[1].plot(B.index, B["ctr"], color=TEAL, lw=0.9)
    ax[1].axhline(0, color="black", lw=0.6)
    ax[1].set_title("Basket carry-to-risk ratio (average of five pairs)")
    ax[2].plot(B.index, B["rr"], color=RED, lw=0.9)
    ax[2].axhline(0, color="black", lw=0.6)
    ax[2].set_title("Basket 25-delta risk reversal, 3M (average of five pairs)")
    for a in ax:
        for e in events:
            a.axvline(e, color=GREY, lw=0.7, ls="--")
    _years(ax[2])
    _save(fig, out / "fig4_basket_signals_and_unwinds.png", NOTE + " Dashed lines: first day of each unwind episode.")


def event_study(paths, n, out):
    lo, hi = EVENT_WIN
    tau = np.arange(lo, hi + 1)
    titles = {"ret": "Basket cumulative return since day -40 (per cent)",
              "rr": "Change in basket risk reversal since day -40 (volatility points)",
              "ctr": "Change in basket carry-to-risk ratio since day -40"}
    fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    for a, key in zip(ax, ["ret", "rr", "ctr"]):
        for row in paths[key]:
            a.plot(tau, row, color=GREY, lw=0.7, alpha=0.6)
        a.plot(tau, paths[key].mean(axis=0), color=RED if key == "rr" else NAVY, lw=2.0, label=f"Average of {n} episodes")
        a.axvline(0, color="black", lw=0.8, ls="--")
        a.axhline(0, color="black", lw=0.5)
        a.set_title(titles[key])
        a.legend(loc="upper left", fontsize=8)
    ax[2].set_xlabel("Trading days from the first breach of the unwind threshold")
    _save(fig, out / "fig5_event_study.png", NOTE + " Few independent episodes, the figure is descriptive.")


def cross_corr(cc, out):
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(cc["k"], cc["corr"], color=[RED if k == 0 else NAVY for k in cc["k"]], width=0.7)
    band = cc["naive_95pct_band"].iloc[0]
    ax.axhline(band, color=GREY, ls="--", lw=0.8, label="Approximate 95% band (independent observations)")
    ax.axhline(-band, color=GREY, ls="--", lw=0.8)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xlabel("k (positive k: the risk reversal change occurs k days after the basket return)")
    ax.set_ylabel("Correlation")
    ax.set_title("Daily basket return and daily change in the risk reversal")
    ax.legend(loc="upper right")
    _save(fig, out / "fig6_lead_lag_correlation.png", NOTE)


def rule(base, ruled, out):
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(base.index, 100 * (1 + base).cumprod(), color=NAVY, lw=1.1, label="Passive basket")
    ax.plot(ruled.index, 100 * (1 + ruled).cumprod(), color=RED, lw=1.1, label="Exposure halved when the risk reversal is high")
    ax.set_title("Passive basket and a risk reversal exposure rule (index = 100)")
    ax.legend(loc="upper left")
    _years(ax)
    _save(fig, out / "fig7_risk_reversal_rule.png", NOTE + " The rule uses only information available the previous day.")


def probit_fit(fitted, yb, tail, out):
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(fitted.index, fitted.values, color=NAVY, lw=0.9, label="Fitted probability of a tail week")
    ev = yb[yb == 1].index
    ax.scatter(ev, np.zeros(len(ev)), marker="|", s=120, color=RED, label=f"Weeks in the worst {tail:.0%}")
    ax.axhline(tail, color=GREY, ls="--", lw=0.8, label="Unconditional frequency")
    ax.set_ylabel("Probability")
    ax.set_title("Probit for tail weeks of the carry basket (changes in carry-to-risk and risk reversal)")
    ax.legend(loc="upper left", fontsize=8)
    _years(ax)
    _save(fig, out / "fig8_probit_fitted_probability.png", NOTE + " In-sample fit, one of five weekly grids; results vary across grids (Table 07).")
