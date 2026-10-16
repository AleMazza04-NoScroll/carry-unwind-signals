"""Reading Bloomberg history exports (one series per .xlsx file, PX_LAST used)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .config import OPTIONAL, REQUIRED


def read_bbg_file(path: Path):
    """Return (code, security, PX_LAST series) or None if the file is not a history export.

    The series is identified by the 'Security' cell, so file names are irrelevant.
    Works with and without the 'Pricing Source' row.
    """
    raw = pd.read_excel(path, header=None, engine="openpyxl")
    first = raw.iloc[:, 0].astype(str).str.strip()
    sec_rows = raw.index[first.eq("Security")]
    hdr_rows = raw.index[first.eq("Date")]
    if len(sec_rows) == 0 or len(hdr_rows) == 0:
        return None
    security = str(raw.iloc[sec_rows[0], 1]).strip()
    h = hdr_rows[0]
    header = raw.iloc[h].astype(str).str.strip().tolist()
    if "PX_LAST" not in header:
        return None
    col = header.index("PX_LAST")
    dates = pd.to_datetime(raw.iloc[h + 1:, 0], errors="coerce")
    values = pd.to_numeric(raw.iloc[h + 1:, col], errors="coerce")
    s = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(dates))
    s = s[s.index.notna()].dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return security.split()[0], security, s


def load_all(data_dir: Path):
    series, meta = {}, []
    for f in sorted(Path(data_dir).glob("*.xlsx")):
        if f.name.startswith("~$"):
            continue
        parsed = read_bbg_file(f)
        if parsed is None:
            print(f"  skipped (not a Bloomberg history export): {f.name}")
            continue
        code, security, s = parsed
        if code in series:
            sys.exit(f"Duplicate series {code} (file {f.name}). Remove one of the two files.")
        series[code] = s
        meta.append({
            "ticker": security, "field": "PX_LAST",
            "first_date": s.index[0].date(), "last_date": s.index[-1].date(),
            "observations": len(s),
        })
    missing = [c for c in REQUIRED if c not in series]
    if missing:
        sys.exit("Missing required series: " + ", ".join(missing))
    absent = [c for c in OPTIONAL if c not in series]
    if absent:
        print("  optional series not found: " + ", ".join(absent))
    return series, pd.DataFrame(meta).sort_values("ticker").reset_index(drop=True)
