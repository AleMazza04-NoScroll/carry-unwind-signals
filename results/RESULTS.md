# Results

Main basket: USD/JPY, AUD/JPY, NZD/JPY, GBP/JPY, CAD/JPY, equal weights, 2007-08-30 to 2026-10-16 (4983 trading days). The sample starts after the last gap longer than seven calendar days in the Bloomberg history of the cross-currency options. Robustness basket: USD/JPY and AUD/JPY, 2004-10-08 to 2026-10-16 (5744 days). Section and equation numbers refer to Greene, *Econometric Analysis*, 5th edition. All numbers are produced by `run_analysis.py`.

## Latest values, USD/JPY

| item | value |
|---|---|
| date | 2026-10-16 |
| 3M implied volatility (ATM, %) | 7.86 |
| forward-implied differential, USD minus JPY (% p.a.) | 2.98 |
| carry-to-risk, forward-implied | 0.38 |
| carry-to-risk, policy rates | 0.35 |
| risk reversal 25D 3M, sign of Galati, Heath and McGuire (2007) | 1.74 |
| implied minus subsequent 63-day realised volatility, mean since 2000 (vol points) | 0.58 |
| share of days with implied above subsequent realised, since 2000 | 67% |

## 1. Unit root tests (Greene 20.3.4), constant included, lags chosen by AIC

The level of the carry-to-risk ratio does not reject a unit root, so it appears only in charts. Every regressor used for inference is a change, and every change rejects a unit root.

| series | ADF_stat | p_value | lags_AIC | N | crit_5pct | unit_root_rejected_5pct |
|---|---|---|---|---|---|---|
| basket return | -13.214 | 0.000 | 28 | 4954 | -2.862 | yes |
| basket carry-to-risk (level) | -2.333 | 0.162 | 25 | 4957 | -2.862 | no |
| change in basket carry-to-risk (5d) | -11.616 | 0.000 | 30 | 4947 | -2.862 | yes |
| daily change in basket carry-to-risk | -14.720 | 0.000 | 24 | 4957 | -2.862 | yes |
| basket risk reversal (level) | -4.501 | 0.000 | 16 | 4966 | -2.862 | yes |
| change in basket risk reversal (5d) | -12.726 | 0.000 | 32 | 4945 | -2.862 | yes |
| daily change in basket risk reversal | -18.093 | 0.000 | 15 | 4966 | -2.862 | yes |
| VIX (level) | -5.768 | 0.000 | 11 | 4971 | -2.862 | yes |
| change in VIX (5d) | -13.796 | 0.000 | 32 | 4945 | -2.862 | yes |
| carry-to-risk USDJPY (level) | -1.996 | 0.288 | 32 | 4957 | -2.862 | no |
| carry-to-risk AUDJPY (level) | -2.871 | 0.049 | 30 | 4959 | -2.862 | yes |
| carry-to-risk NZDJPY (level) | -2.742 | 0.067 | 32 | 4957 | -2.862 | no |
| carry-to-risk GBPJPY (level) | -1.844 | 0.359 | 25 | 4960 | -2.862 | no |
| carry-to-risk CADJPY (level) | -2.191 | 0.209 | 32 | 4954 | -2.862 | no |

## 2. Predictive regressions, model M3

Dependent variable: basket return over the next h days, in per cent. Regressors: 5-day changes in carry-to-risk and risk reversal, standardised. Newey-West errors (eq. 12-17), L = max(h, ceil(T^(1/4))), cover the MA(h-1) structure of overlapping sums.

| horizon | regressor | L | coef | z | p_value | R2 | N |
|---|---|---|---|---|---|---|---|
| 1 | dCTR_5d | 9 | 0.029 | 2.085 | 0.037 | 0.002 | 4977 |
| 1 | dRR_5d | 9 | 0.030 | 1.425 | 0.154 | 0.002 | 4977 |
| 5 | dCTR_5d | 9 | 0.042 | 0.847 | 0.397 | 0.001 | 4973 |
| 5 | dRR_5d | 9 | 0.068 | 0.969 | 0.333 | 0.001 | 4973 |
| 21 | dCTR_5d | 21 | 0.004 | 0.039 | 0.969 | 0.000 | 4957 |
| 21 | dRR_5d | 21 | 0.021 | 0.189 | 0.850 | 0.000 | 4957 |

Non-overlapping subsamples, one per starting day, Newey-West with L = ceil(N^(1/4)):

| horizon | regressor | subsamples | N_each | z_min | z_median | z_max | share_abs_z_above_1.96 |
|---|---|---|---|---|---|---|---|
| 5 | dCTR_5d | 5 | 995 | 0.213 | 0.447 | 1.804 | 0.000 |
| 5 | dRR_5d | 5 | 995 | 0.363 | 0.692 | 1.296 | 0.000 |
| 21 | dCTR_5d | 21 | 237 | -1.917 | 0.064 | 1.876 | 0.000 |
| 21 | dRR_5d | 21 | 237 | -2.774 | 0.243 | 2.328 | 0.095 |

## 3. Residual diagnostics

Breusch-Godfrey LM, P = 5 (eq. 12-20); Ljung-Box Q, P = 10 (eq. 12-22); ARCH LM, q = 5 (11.8.4).

| horizon | model | sample | N | BG_LM | BG_df | BG_p | LB_Q | LB_df | LB_p | ARCH_LM | ARCH_df | ARCH_p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | M1 | all days | 4977 | 16.244 | 5 | 0.006 | 26.571 | 10 | 0.003 | 898.529 | 5 | 0.000 |
| 1 | M2 | all days | 4977 | 9.113 | 5 | 0.105 | 18.785 | 10 | 0.043 | 917.826 | 5 | 0.000 |
| 1 | M3 | all days | 4977 | 10.795 | 5 | 0.056 | 20.027 | 10 | 0.029 | 917.966 | 5 | 0.000 |
| 5 | M1 | non-overlapping, first grid | 995 | 25.909 | 5 | 0.000 | 44.499 | 10 | 0.000 | 179.478 | 5 | 0.000 |
| 5 | M2 | non-overlapping, first grid | 995 | 19.172 | 5 | 0.002 | 36.384 | 10 | 0.000 | 159.294 | 5 | 0.000 |
| 5 | M3 | non-overlapping, first grid | 995 | 19.817 | 5 | 0.001 | 36.568 | 10 | 0.000 | 159.818 | 5 | 0.000 |
| 21 | M1 | non-overlapping, first grid | 237 | 10.940 | 5 | 0.053 | 13.630 | 10 | 0.191 | 17.074 | 5 | 0.004 |
| 21 | M2 | non-overlapping, first grid | 237 | 11.491 | 5 | 0.042 | 14.325 | 10 | 0.159 | 17.623 | 5 | 0.003 |
| 21 | M3 | non-overlapping, first grid | 237 | 11.458 | 5 | 0.043 | 14.267 | 10 | 0.161 | 16.844 | 5 | 0.005 |

## 4. Lead-lag correlation, daily basket return and daily change in the risk reversal

k = 0: -0.447; k = 1: -0.296; largest absolute value for k < 0: 0.034; approximate 95% band: +/- 0.028.

## 5. Granger causality (Greene 19.6.5), Wald tests with Newey-West covariance

Lag order: the smallest p in {5, 10, 15, 20, 25, 30} whose residuals pass the Breusch-Godfrey test, because autocorrelation with a lagged dependent variable makes OLS inconsistent (Greene p. 266).

| hypothesis_tested | lags | N | Wald_HAC | Wald_p | F_classical | F_p | BG_LM | BG_p |
|---|---|---|---|---|---|---|---|---|
| dRR does not Granger-cause return | 5 | 4977 | 2.379 | 0.795 | 0.954 | 0.445 | 10.777 | 0.056 |
| return does not Granger-cause dRR | 20 | 4962 | 136.644 | 0.000 | 20.761 | 0.000 | 2.845 | 0.724 |
| dCTR does not Granger-cause return | 5 | 4977 | 8.934 | 0.112 | 2.403 | 0.035 | 7.375 | 0.194 |
| return does not Granger-cause dCTR | 10 | 4972 | 56.240 | 0.000 | 8.436 | 0.000 | 6.268 | 0.281 |

Range of Wald p-values over the six lag orders:

| hypothesis_tested | Wald_p_min | Wald_p_max |
|---|---|---|
| dRR does not Granger-cause return | 0.253 | 0.831 |
| return does not Granger-cause dRR | 0.000 | 0.000 |
| dCTR does not Granger-cause return | 0.033 | 0.296 |
| return does not Granger-cause dCTR | 0.000 | 0.000 |

## 6. Probit for tail weeks (Greene 21.4), non-overlapping weeks

Outcome: the basket return over the next five days is in the worst 5% (or 10%) of weeks. Regressors: 5-day changes in carry-to-risk and risk reversal, standardised, and with controls the 5-day change in the VIX. Each specification is estimated on the five weekly grids (starting days); a result found on a minority of grids is not robust.

| tail | controls | LR_p_min | LR_p_median | LR_p_max | grids_with_LR_p_below_5pct | LRI_mean |
|---|---|---|---|---|---|---|
| 0.050 | no | 0.001 | 0.045 | 0.385 | 3 | 0.018 |
| 0.050 | yes | 0.002 | 0.082 | 0.583 | 2 | 0.020 |
| 0.100 | no | 0.014 | 0.287 | 0.896 | 1 | 0.006 |
| 0.100 | yes | 0.036 | 0.401 | 0.962 | 1 | 0.006 |

First grid, fit measures (21.4.5) and tests (21.4.3):

| tail | controls | N | events | threshold_pct | lnL | lnL0 | LRI_McFadden | LR_all_slopes | LR_df | LR_p | Wald_signals | Wald_signals_p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.050 | no | 995 | 50 | -2.581 | -195.151 | -198.258 | 0.016 | 6.214 | 2 | 0.045 | 6.349 | 0.042 |
| 0.050 | yes | 995 | 50 | -2.581 | -194.906 | -198.258 | 0.017 | 6.703 | 3 | 0.082 | 3.205 | 0.201 |
| 0.100 | no | 995 | 100 | -1.661 | -322.369 | -324.555 | 0.007 | 4.373 | 2 | 0.112 | 4.413 | 0.110 |
| 0.100 | yes | 995 | 100 | -1.661 | -321.810 | -324.555 | 0.008 | 5.490 | 3 | 0.139 | 5.467 | 0.065 |

First grid, marginal effects at the means with delta-method errors (21.4.2):

| spec | variable | marginal_effect_at_means | se_delta | z | p_value |
|---|---|---|---|---|---|
| tail=5%, controls=none | dCTR_5d | -0.006 | 0.007 | -0.919 | 0.358 |
| tail=5%, controls=none | dRR_5d | 0.011 | 0.006 | 1.675 | 0.094 |
| tail=5%, controls=VIX | dCTR_5d | -0.006 | 0.007 | -0.840 | 0.401 |
| tail=5%, controls=VIX | dRR_5d | 0.008 | 0.007 | 1.186 | 0.236 |
| tail=5%, controls=VIX | dVIX_5d | 0.005 | 0.007 | 0.702 | 0.483 |
| tail=10%, controls=none | dCTR_5d | -0.009 | 0.010 | -0.865 | 0.387 |
| tail=10%, controls=none | dRR_5d | 0.013 | 0.010 | 1.303 | 0.192 |
| tail=10%, controls=VIX | dCTR_5d | -0.010 | 0.010 | -0.946 | 0.344 |
| tail=10%, controls=VIX | dRR_5d | 0.017 | 0.011 | 1.619 | 0.105 |
| tail=10%, controls=VIX | dVIX_5d | -0.011 | 0.010 | -1.051 | 0.293 |

## 7. Unwind episodes (descriptive)

First day of each cluster of 5-day basket returns at or below -4.50% (worst 1% of days), clusters separated by more than 60 trading days.

| first_breach | worst_5d_date | worst_5d_return_pct | days_below_threshold |
|---|---|---|---|
| 2007-11-12 | 2007-11-12 | -7.050 | 3 |
| 2008-09-04 | 2008-10-27 | -18.360 | 22 |
| 2009-04-20 | 2009-07-08 | -5.870 | 3 |
| 2010-05-06 | 2010-05-20 | -7.770 | 6 |
| 2011-03-16 | 2011-03-17 | -5.950 | 2 |
| 2015-08-24 | 2015-08-25 | -5.810 | 3 |
| 2016-01-08 | 2016-01-08 | -5.380 | 1 |
| 2016-04-07 | 2016-06-30 | -5.740 | 5 |
| 2020-03-09 | 2020-03-09 | -5.160 | 1 |
| 2022-12-22 | 2022-12-22 | -4.510 | 1 |
| 2024-08-02 | 2024-08-05 | -6.490 | 3 |

## 8. Risk reversal exposure rule (one threshold, fixed ex ante)

| strategy | ann_return_pct | ann_vol_pct | sharpe | max_drawdown_pct | share_days_reduced_pct |
|---|---|---|---|---|---|
| passive_basket | 3.82 | 11.52 | 0.33 | -32.59 | 0.00 |
| rr_rule | 4.21 | 9.79 | 0.43 | -24.46 | 13.51 |

## 9. Robustness: USD/JPY and AUD/JPY basket, longer sample

Predictive regressions, model M3:

| horizon | regressor | L | coef | z | p_value | R2 | N |
|---|---|---|---|---|---|---|---|
| 1 | dCTR_5d | 9 | 0.022 | 1.805 | 0.071 | 0.002 | 5738 |
| 1 | dRR_5d | 9 | 0.036 | 1.954 | 0.051 | 0.002 | 5738 |
| 5 | dCTR_5d | 9 | 0.004 | 0.105 | 0.916 | 0.002 | 5734 |
| 5 | dRR_5d | 9 | 0.066 | 1.174 | 0.241 | 0.002 | 5734 |
| 21 | dCTR_5d | 21 | -0.047 | -0.548 | 0.583 | 0.000 | 5718 |
| 21 | dRR_5d | 21 | 0.001 | 0.007 | 0.995 | 0.000 | 5718 |

Granger causality, preferred lag order:

| hypothesis_tested | lags | N | Wald_HAC | Wald_p | F_classical | F_p | BG_LM | BG_p |
|---|---|---|---|---|---|---|---|---|
| dRR does not Granger-cause return | 10 | 5733 | 5.991 | 0.816 | 1.160 | 0.313 | 8.550 | 0.128 |
| return does not Granger-cause dRR | 10 | 5733 | 88.628 | 0.000 | 50.321 | 0.000 | 8.031 | 0.155 |
| dCTR does not Granger-cause return | 10 | 5733 | 12.920 | 0.228 | 2.145 | 0.018 | 10.722 | 0.057 |
| return does not Granger-cause dCTR | 15 | 5728 | 72.060 | 0.000 | 7.800 | 0.000 | 7.061 | 0.216 |

Probit across the five weekly grids:

| tail | controls | LR_p_min | LR_p_median | LR_p_max | grids_with_LR_p_below_5pct | LRI_mean |
|---|---|---|---|---|---|---|
| 0.050 | no | 0.023 | 0.547 | 0.897 | 1 | 0.005 |
| 0.050 | yes | 0.055 | 0.398 | 0.854 | 0 | 0.007 |
| 0.100 | no | 0.008 | 0.493 | 0.838 | 1 | 0.004 |
| 0.100 | yes | 0.010 | 0.524 | 0.941 | 1 | 0.005 |

Lead-lag correlation: k = 0: -0.423; k = 1: -0.267; largest absolute value for k < 0: 0.028; approximate 95% band: +/- 0.026.

Unwind episodes (threshold -4.21%):

| first_breach | worst_5d_date | worst_5d_return_pct | days_below_threshold |
|---|---|---|---|
| 2005-12-16 | 2005-12-16 | -4.550 | 1 |
| 2007-03-05 | 2007-03-05 | -5.660 | 1 |
| 2007-08-15 | 2007-08-16 | -7.020 | 7 |
| 2008-09-04 | 2008-10-27 | -16.690 | 18 |
| 2009-04-20 | 2009-07-08 | -5.770 | 4 |
| 2010-05-06 | 2010-05-20 | -7.790 | 6 |
| 2011-03-16 | 2011-03-17 | -5.990 | 2 |
| 2013-06-11 | 2013-06-11 | -5.140 | 1 |
| 2015-08-24 | 2015-08-24 | -6.280 | 3 |
| 2016-01-08 | 2016-05-03 | -5.950 | 9 |
| 2020-03-09 | 2020-03-09 | -5.180 | 2 |
| 2024-08-02 | 2024-08-05 | -6.860 | 3 |
| 2025-04-08 | 2025-04-08 | -4.730 | 1 |

Exposure rule:

| strategy | ann_return_pct | ann_vol_pct | sharpe | max_drawdown_pct | share_days_reduced_pct |
|---|---|---|---|---|---|
| passive_basket | 4.86 | 11.21 | 0.43 | -32.81 | 0.00 |
| rr_rule | 4.51 | 9.53 | 0.47 | -25.58 | 13.35 |
