"""Parameters of the study. Every choice is fixed here, before estimation."""
import pandas as pd

PAIRS = ["USDJPY", "AUDJPY", "NZDJPY", "GBPJPY", "CADJPY"]
TARGET = {"USDJPY": "USD", "AUDJPY": "AUD", "NZDJPY": "NZD", "GBPJPY": "GBP", "CADJPY": "CAD"}
FWD_POINTS = ["JPY3M", "AUD3M", "NZD3M", "GBP3M", "CAD3M"]

REQUIRED = (
    PAIRS
    + [p + "V3M" for p in PAIRS]
    + [p + "25R3M" for p in PAIRS]
    + FWD_POINTS
    + ["VIX", "FDTR", "BOJDTR"]
)
OPTIONAL = ["MUTKCALM", "JPMVXYG7", "USDJPYV1M", "USDJPY25R1M"]

# Forward points: (ticker, scale, USD is the base currency of the quoted pair)
# JPY3M -> USDJPY, AUD3M -> AUDUSD, NZD3M -> NZDUSD, GBP3M -> GBPUSD, CAD3M -> USDCAD
FWD_SPEC = {
    "JPY": ("JPY3M", 100.0, True),
    "AUD": ("AUD3M", 1e4, False),
    "NZD": ("NZD3M", 1e4, False),
    "GBP": ("GBP3M", 1e4, False),
    "CAD": ("CAD3M", 1e4, True),
}

TAU = 91 / 360          # three-month accrual factor
FFILL_LIMIT = 5         # longest gap (trading days) bridged in daily signal series
MAX_GAP_DAYS = 7        # a basket sample must have no gap longer than this (calendar days)
LONG_SAMPLE_PAIRS = ["USDJPY", "AUDJPY"]   # robustness basket with a longer continuous history

# Predictive regressions
HORIZONS = (1, 5, 21)   # trading days ahead

# Residual diagnostics (Greene, 5th ed., 12.7 and 11.8.4)
BG_LAGS = 5             # Breusch-Godfrey LM, P
LB_LAGS = 10            # Ljung-Box Q, P
ARCH_LAGS = 5           # ARCH LM, q

# Granger causality (Greene 19.6.5)
GRANGER_LAGS = (5, 10, 15, 20, 25, 30)   # preferred: smallest with BG not rejected

# Unwind episodes (descriptive definition)
UNWIND_PCTL = 0.01      # 5-day basket return in the worst 1% of days
UNWIND_GAP = 60         # trading days separating two episodes
EVENT_WIN = (-40, 20)

# Probit on weekly, non-overlapping observations
WEEK = 5
PROBIT_TAILS = (0.05, 0.10)

# Exposure rule (fixed ex ante, a single threshold)
RULE_WINDOW = 252
RULE_PCTL = 0.90
RULE_HAIRCUT = 0.5

LEHMAN = pd.Timestamp("2008-09-15")
BOJ_UNWIND = pd.Timestamp("2024-08-05")
