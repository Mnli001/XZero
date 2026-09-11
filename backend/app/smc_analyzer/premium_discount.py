"""Premium / Discount dealing-range valuation.

Dealing range = highest high / lowest low over the lookback window.
Price above equilibrium (50%) = premium (prefer shorts), below = discount
(prefer longs). Within tolerance = equilibrium (no-man's land).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Valuation:
    range_high: float
    range_low: float
    equilibrium: float
    position_pct: float  # 0 = range low, 50 = equilibrium, 100 = range high
    zone: str  # "premium" | "discount" | "equilibrium"


def evaluate(df: pd.DataFrame, lookback: int = 120, tolerance_pct: float = 0.05, at_index: int | None = None) -> Valuation | None:
    if df.empty:
        return None
    i = len(df) - 1 if at_index is None else at_index
    if i < 1:
        return None
    window = df.iloc[max(0, i - lookback + 1) : i + 1]
    rh = float(window["high"].max())
    rl = float(window["low"].min())
    if rh <= rl:
        return None
    eq = (rh + rl) / 2
    price = float(df["close"].iloc[i])
    pos = (price - rl) / (rh - rl) * 100.0
    tol = tolerance_pct * 100.0
    if abs(pos - 50.0) <= tol:
        zone = "equilibrium"
    elif pos > 50.0:
        zone = "premium"
    else:
        zone = "discount"
    return Valuation(rh, rl, eq, pos, zone)
