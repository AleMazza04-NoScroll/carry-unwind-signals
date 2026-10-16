# Methodology

Section, equation and page numbers refer to W. H. Greene, *Econometric Analysis*, 5th edition (2003). Every parameter mentioned below is set in `src/carry_unwind/config.py` before estimation.

## 1. Variables

**Interest rate differentials.** For each currency the three-month differential against the US dollar is taken from Bloomberg three-month forward points through covered interest parity. For a pair quoted as USD/XXX, F/S - 1 = (i_XXX - i_USD) τ / (1 + i_USD τ); for a pair quoted as XXX/USD the sign is reversed. With τ = 91/360 the denominator is dropped, an approximation whose relative error is about i·τ, below 1.5% of the differential for rates under 6%. Forward points are divided by 100 for USD/JPY and by 10,000 for the other pairs. The differential of each cross against the yen is the difference of the two differentials against the dollar. Spot rates against the dollar are rebuilt from the yen crosses, so every input shares the BGN timestamp. Forward-implied differentials include the cross-currency basis. A policy-rate version (Fed funds target minus BoJ policy rate) is computed for USD/JPY as a comparison.

**Carry-to-risk ratio.** Differential divided by the three-month at-the-money implied volatility, as in note 4 of Graph 1 in Galati, Heath and McGuire (2007).

**Risk reversal.** The Bloomberg 25-delta three-month risk reversal is quoted as the implied volatility of the call minus that of the put on the first currency of the pair. It is multiplied by -1, so that positive values mean that hedging a yen appreciation costs more, the sign used in Galati, Heath and McGuire (2007).

**Returns.** The daily excess return of a long position in the target currency funded in yen is the spot return plus the carry accrued on the previous day's differential (ACT/360). The basket is the equal-weighted average of the five pairs.

**Sample.** Rolling sums and differences require consecutive observations. The basket sample starts on the first day after the last gap longer than seven calendar days in any of its series. For the five-pair basket this is 30 August 2007, because the Bloomberg option history of NZD/JPY and CAD/JPY has gaps of several months in 2006 and 2007. A two-pair basket (USD/JPY and AUD/JPY), continuous from October 2004, is the robustness sample and includes the August 2007 unwind. Gaps of up to five trading days in daily signals are bridged by carrying the last value forward.

## 2. Stationarity

The asymptotic results used throughout require stationary and ergodic series (12.4, Theorem 12.1). Each series is tested with an augmented Dickey-Fuller regression with a constant and lags chosen by AIC (20.3.4); critical values are those of Dickey and Fuller (5% asymptotic value -2.86, Table 20.4).

The level of the carry-to-risk ratio does not reject a unit root for the basket or for any pair. It is therefore used only in charts. Every regressor used for inference is a 5-day change, and every change rejects a unit root at 1%. Differencing to obtain stationarity follows 20.3.1.

## 3. Predictive regressions

For h = 1, 5 and 21 trading days,

    r(t+1) + ... + r(t+h) = α + β1 ΔCTR5(t) + β2 ΔRR5(t) + u(t)

with the two regressors standardised (a rescaling that leaves t-ratios and fit unchanged). Models M1 and M2 include one regressor each, M3 both.

Overlapping sums give u(t) an MA(h-1) structure, so OLS remains consistent but s²(X'X)⁻¹ is not a valid covariance estimator (12.5.2). The covariance is the Newey-West estimator of eq. (12-17), with Bartlett weights w_j = 1 - j/(L+1) and no degrees-of-freedom correction. Greene (p. 267) requires L large enough for autocorrelations beyond L to be negligible and reports the current practice of the smallest integer ≥ T^(1/4). The study uses L = max(h, ceil(T^(1/4))), that is 9 for h = 1 and 5 and 21 for h = 21. Inference uses the normal distribution.

Robustness: for h > 1 the regression is repeated on each of the h non-overlapping subsamples (one per starting day). The residual tests of section 4 show autocorrelation in the weekly non-overlapping residuals, so these regressions also use Newey-West errors, with L = ceil(N^(1/4)).

The same regression is estimated pair by pair.

## 4. Residual diagnostics

* **Breusch-Godfrey LM**, eq. (12-20): T times the uncentred R² of the regression of the residuals on the regressors and P = 5 lagged residuals, chi-squared with P degrees of freedom. Missing initial lags are filled with zeros; Greene (p. 269) notes that software differs on this point and asks users to state the convention. The test remains valid with lagged dependent variables (12.7.4).
* **Ljung-Box Q**, eq. (12-22), with P = 10 and r_j defined as in (12-21).
* **ARCH LM** (11.8.4, p. 244): T times the R² of the regression of squared residuals on a constant and q = 5 lags.

The ARCH test rejects strongly at daily and weekly frequency, which supports covariance estimators that are robust to heteroscedasticity. Newey-West is robust to both heteroscedasticity and autocorrelation.

## 5. Lead and lag

**Cross-correlations** between the daily basket return at t and the daily change of the risk reversal at t + k, for k from -10 to +10. The band ±1.96/√T assumes independent observations and is approximate under heteroscedasticity.

**Granger causality** (19.6.5). Single-equation regressions of y(t) on p lags of y and p lags of x, with a Wald test that the p coefficients on lagged x are zero, using the Newey-West covariance (Greene p. 593 indicates the Wald test as the more general option when the likelihood ratio test's normality assumption is doubtful; the ARCH results make it doubtful here). The classical F test is reported alongside. Greene (p. 266) shows that OLS is inconsistent when a regression contains a lagged dependent variable and the disturbances are autocorrelated. The preferred lag order is therefore the smallest p in {5, 10, 15, 20, 25, 30} whose residuals pass the Breusch-Godfrey test at 5%, and results are reported for every order. Greene's caveat (p. 593) applies: Granger causality establishes precedence in time, and an omitted variable correlated with both series could produce the same pattern.

## 6. Probit for tail weeks

The outcome is 1 when the basket return over the next five trading days falls in the worst 5% (or 10%) of weeks. The regressors are known at t: the 5-day changes in carry-to-risk and risk reversal, standardised, and in a second specification the 5-day change in the VIX. Observations are weekly and non-overlapping, so the independence assumption of the likelihood is not broken by construction. There are five possible weekly grids (one per starting day) and every specification is estimated on all of them.

Reported for each fit, following 21.4: the coefficients with z statistics from the Hessian-based covariance (the usual choice, p. 673), z statistics from the sandwich estimator (21.4.1), marginal effects at the means with delta-method errors (21.4.2), the log-likelihood and the constant-only log-likelihood (21-28), McFadden's likelihood ratio index (21.4.5), the likelihood ratio test of all slopes and the Wald test (21-27) of the two signals (21.4.3). Greene warns (p. 674) that a robust covariance does not repair an inconsistent estimator, so the sandwich results are a sensitivity check. Weekly returns show some residual autocorrelation (section 4), which could make the probit p-values too small; the conclusion that the probit result is not robust across grids holds regardless.

## 7. Descriptive analysis

**Unwind episodes.** A day belongs to an unwind when the 5-day basket return is in the worst 1% of days; days less than 60 trading days apart form one episode, dated by its first day. The percentile uses the whole sample, so the definition is descriptive and is never used as a trading signal.

**Event study.** Basket return, risk reversal and carry-to-risk from 40 days before to 20 days after the first day of each episode, rebased at day -40.

**Exposure rule.** Exposure is halved on day t when the risk reversal of day t-1 exceeds its 90th percentile over the previous 252 days. Threshold, window and haircut are fixed in advance; a test in `tests/` confirms that changing the last observation leaves every earlier exposure unchanged.

## 8. Verification log

The pipeline was checked three times against the intended design and against the textbook. Each check changed the study.

1. **Unit roots.** The first version used the level of the carry-to-risk ratio as a regressor. The Dickey-Fuller test does not reject a unit root for it, which violates the stationarity assumption of 12.4. The level was replaced by its 5-day change.
2. **Robustness of the probit.** The first version estimated the probit on one weekly grid and found p = 0.003. On the other four grids the p-value reached 0.68. Every probit is now estimated on all five grids and the result is reported as not robust.
3. **Residual autocorrelation.** Non-overlapping monthly residuals failed the Breusch-Godfrey test, so White errors were replaced by Newey-West errors; Granger equations with autocorrelated residuals led to the lag selection rule of section 5.
4. **Gaps in the data.** A chart of fitted probabilities showed straight segments in 2006-2007. The cause was months of missing option data for two crosses, across which rolling windows were computed. The sample rule of section 1 removes the problem.
5. **Textbook formulas.** `tests/test_econometrics.py` checks that the Newey-West covariance equals eq. (12-17) computed by hand (to 10 decimal places), that the Breusch-Godfrey, Ljung-Box and ARCH statistics equal their textbook definitions, that covered interest parity gives the right signs for both quoting conventions, that h-day sums are aligned with r(t+1) to r(t+h), that the exposure rule uses only past data, and that the probit fit measures match (21-28) and McFadden's index.
6. **Data against the terminal.** On 16 October 2026 the Bloomberg OVDV screen for USD/JPY showed a three-month 25-delta risk reversal of -1.830/-1.645 (mid -1.74) and the file value was -1.7425; the one-month deposit rates on the same screen (USD 3.985%, JPY 1.097%) imply a differential of about -2.9%, against -3.0% from the three-month forward points.
