"""Fair Value Gap (3-candle imbalance) detector.

Bullish FVG at bar i: low[i+1] > high[i-1]  -> zone [high[i-1], low[i+1]].
Bearish FVG at bar i: high[i+1] < low[i-1]  -> zone [high[i+1], low[i-1]].
Zones are mitigated on touch (or close-through, per config) and expire after
`max_age_bars`.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class FVGZone:
    index: int  # middle (displacement) bar
    time: object
    direction: str  # "bullish" | "bearish"
    top: float
    bottom: float
    size: float
    mitigated_index: int | None = None
    active: bool = True


def detect_fvgs(
    df: pd.DataFrame,
    atr: pd.Series | None = None,
    atr_period: int = 14,
    min_atr_mult: float = 0.2,
    max_age_bars: int = 60,
    mitigation: str = "touch",
) -> list[FVGZone]:
    if len(df) < 3:
        return []
    if atr is None:
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / atr_period, min_periods=atr_period, adjust=False).mean()

    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    zones: list[FVGZone] = []
    n = len(df)
    for i in range(1, n - 1):
        a = atr.iloc[i + 1]
        if pd.isna(a) or a <= 0:
            continue
        # Bullish FVG
        if lows[i + 1] > highs[i - 1]:
            size = lows[i + 1] - highs[i - 1]
            if size >= min_atr_mult * a:
                zones.append(FVGZone(i, df["time"].iloc[i], "bullish", float(lows[i + 1]), float(highs[i - 1]), float(size)))
        # Bearish FVG
        elif highs[i + 1] < lows[i - 1]:
            size = lows[i - 1] - highs[i + 1]
            if size >= min_atr_mult * a:
                zones.append(FVGZone(i, df["time"].iloc[i], "bearish", float(lows[i - 1]), float(highs[i + 1]), float(size)))

    # Mitigation + expiry pass
    for z in zones:
        for j in range(z.index + 2, min(z.index + 2 + max_age_bars, n)):
            touched = False
            if mitigation == "touch":
                touched = lows[j] <= z.top and highs[j] >= z.bottom
            else:  # close_through
                if z.direction == "bullish":
                    touched = closes[j] < z.bottom
                else:
                    touched = closes[j] > z.top
            if touched:
                z.mitigated_index = j
                z.active = False
                break
        else:
            # loop finished without mitigation
            if z.index + 2 + max_age_bars < n:
                z.active = False  # expired
    return zones


def active_fvgs(zones: list[FVGZone], at_index: int | None = None) -> list[FVGZone]:
    out = [z for z in zones if z.active]
    if at_index is not None:
        out = [z for z in out if z.index <= at_index and (z.mitigated_index is None or z.mitigated_index > at_index)]
    return out
