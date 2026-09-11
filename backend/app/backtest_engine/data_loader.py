"""CSV market-data loader with gap detection (§6: incomplete data is flagged)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

TIMEFRAMES_MIN = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}

REQUIRED_COLS = ["time", "open", "high", "low", "close"]


@dataclass
class DataIssue:
    kind: str  # "gap" | "invalid_row" | "non_monotonic"
    at_time: str
    detail: str


def load_csv(path: str, timeframe: str = "M5") -> tuple[pd.DataFrame, list[DataIssue]]:
    """Load OHLC CSV. Expected columns: time,open,high,low,close (+optional spread,tick_volume).

    Returns (clean_df, issues). Gaps larger than 3x the timeframe step are
    recorded as issues and the dataset is flagged incomplete downstream.
    """
    issues: list[DataIssue] = []
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV {path} missing columns: {missing}")
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    bad = df[REQUIRED_COLS].isna().any(axis=1)
    for t in df.loc[bad, "time"].dropna().astype(str).head(20):
        issues.append(DataIssue("invalid_row", t, "NaN in OHLC/time — row dropped"))
    df = df.loc[~bad].copy()
    # OHLC sanity
    violated = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    for t in df.loc[violated, "time"].astype(str).head(20):
        issues.append(DataIssue("invalid_row", t, "high/low violates OHLC geometry — row dropped"))
    df = df.loc[~violated].copy()

    df = df.sort_values("time").drop_duplicates(subset="time", keep="last").reset_index(drop=True)
    if df.empty:
        raise ValueError(f"CSV {path} has no valid rows")

    step_min = TIMEFRAMES_MIN.get(timeframe.upper(), 5)
    if len(df) > 1:
        diffs = df["time"].diff().dt.total_seconds() / 60.0
        gap_mask = diffs > step_min * 3 + 1e-9
        prev_wd = df["time"].shift(1).dt.weekday
        cur_wd = df["time"].dt.weekday
        for idx in df.index[gap_mask.fillna(False)]:
            # Friday close -> Sunday/Monday open = normal weekend closure, not missing data.
            is_weekend = prev_wd.at[idx] == 4 and cur_wd.at[idx] in (6, 0) and diffs.at[idx] <= 3 * 24 * 60 + 60
            kind = "weekend" if is_weekend else "gap"
            detail = (f"{diffs.at[idx]:.0f}min weekend closure (expected)" if is_weekend
                      else f"{diffs.at[idx]:.0f}min gap (expected {step_min}min) — holiday or missing data")
            issues.append(DataIssue(kind, str(df.at[idx, "time"]), detail))
    if "spread" not in df.columns:
        df["spread"] = 0.0
    return df, issues
