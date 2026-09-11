"""Liquidity sweep detector — strictly repaint-safe.

A sweep = a reference level (prior swing, previous day high/low, Asian session
high/low) is pierced by a wick and price closes back on the original side
within `confirmation_bars`. Direction of the *trade idea* is opposite to the
pierced side (sweep of lows -> bullish idea).

Repaint-safety rules (enforced here, both for live prefix-calls and batch):
  * A swing level is usable only from its confirmation bar (swing + swing_right).
  * A PDH/PDL level is usable only from the first bar of the NEXT day.
  * An Asian level is usable only from the first bar after the session ends.
  * An event is knowable at `confirmed_at` (the bar the close-back printed),
    which may be up to `confirmation_bars` after the pierce bar.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .swings import find_swings


@dataclass
class SweepEvent:
    index: int            # pierce bar
    confirmed_at: int     # bar the close-back was observed (knowable-from)
    level_index: int      # bar the reference level belongs to
    time: object
    level: float
    level_type: str  # "swing_high" | "swing_low" | "pdh" | "pdl" | "asian_high" | "asian_low"
    side: str  # "lows" (swept below) | "highs" (swept above)
    idea_bias: str  # "bullish" | "bearish"
    wick_pierce: float
    confirmed: bool = True


def _atr_values(df: pd.DataFrame, atr: pd.Series | None, atr_period: int):
    import numpy as np
    if atr is None:
        h, l, c = df["high"], df["low"], df["close"]
        prev_c = c.shift(1)
        tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / atr_period, min_periods=atr_period, adjust=False).mean()
    return atr.to_numpy()


def _session_levels(df: pd.DataFrame, asian_start: int, asian_end: int) -> list[dict]:
    """Previous-day + Asian levels with availability bars."""
    levels: list[dict] = []
    n = len(df)
    if n == 0:
        return levels
    t = pd.to_datetime(df["time"])
    day = t.dt.floor("D")
    hours = t.dt.hour.to_numpy()
    pos = list(range(n))
    days = sorted(day.unique())
    first_idx_of_day = {}
    for d in days:
        idxs = [k for k in pos if day.iloc[k] == d]
        first_idx_of_day[d] = idxs[0]
        last = idxs[-1]
        if len(idxs) >= 5:
            hi = float(df["high"].iloc[idxs].max())
            lo = float(df["low"].iloc[idxs].min())
            avail_next = last + 1  # usable from next day's first bar
            levels.append({"index": last, "available_from": avail_next, "price": hi, "type": "pdh"})
            levels.append({"index": last, "available_from": avail_next, "price": lo, "type": "pdl"})
        asian_idxs = [k for k in idxs if asian_start <= hours[k] < asian_end]
        if len(asian_idxs) >= 3:
            after = [k for k in idxs if hours[k] >= asian_end]
            avail = after[0] if after else n  # session not finished -> unusable in this data
            levels.append({"index": asian_idxs[-1], "available_from": avail,
                           "price": float(df["high"].iloc[asian_idxs].max()), "type": "asian_high"})
            levels.append({"index": asian_idxs[-1], "available_from": avail,
                           "price": float(df["low"].iloc[asian_idxs].min()), "type": "asian_low"})
    return levels


def detect_sweeps(
    df: pd.DataFrame,
    atr: pd.Series | None = None,
    atr_period: int = 14,
    swing_left: int = 3,
    swing_right: int = 3,
    min_wick_atr_mult: float = 0.15,
    confirmation_bars: int = 2,
    asian_start: int = 0,
    asian_end: int = 7,
) -> list[SweepEvent]:
    if len(df) < swing_left + swing_right + confirmation_bars + 2:
        return []
    n = len(df)
    atr_v = _atr_values(df, atr, atr_period)
    swings = find_swings(df, swing_left, swing_right)

    ref_levels: list[dict] = []
    for _, r in swings.iterrows():
        li = int(r["index"])
        ref_levels.append({
            "index": li,
            "available_from": li + swing_right,  # swing confirmation bar
            "price": float(r["price"]),
            "type": "swing_high" if r["kind"] == "high" else "swing_low",
        })
    ref_levels.extend(_session_levels(df.reset_index(drop=True), asian_start, asian_end))
    ref_levels.sort(key=lambda d: (d["index"], d["type"]))

    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    times = df["time"].to_numpy()
    events: list[SweepEvent] = []
    seen: set[tuple[float, str]] = set()

    for lvl in ref_levels:
        li = lvl["index"]
        price = lvl["price"]
        start = max(li + 1, lvl["available_from"])
        if start >= n:
            continue
        is_high_level = lvl["type"] in ("swing_high", "pdh", "asian_high")
        side = "highs" if is_high_level else "lows"
        if (price, side) in seen:
            continue
        for i in range(start, n):
            a = atr_v[i]
            if not (a == a) or a <= 0:
                continue
            min_pierce = min_wick_atr_mult * a
            if is_high_level:
                pierce = highs[i] - price
                swept = pierce >= min_pierce
                back_inside = closes[i] < price
            else:
                pierce = price - lows[i]
                swept = pierce >= min_pierce
                back_inside = closes[i] > price
            if not swept:
                if is_high_level and closes[i] > price + 2 * min_pierce:
                    break
                if not is_high_level and closes[i] < price - 2 * min_pierce:
                    break
                continue
            confirmed_at = None
            if back_inside:
                confirmed_at = i
            else:
                for j in range(i + 1, min(i + 1 + confirmation_bars, n)):
                    cj = closes[j]
                    if (is_high_level and cj < price) or (not is_high_level and cj > price):
                        confirmed_at = j
                        break
            if confirmed_at is not None:
                if (price, side) not in seen:
                    seen.add((price, side))
                    events.append(SweepEvent(
                        index=i, confirmed_at=confirmed_at, level_index=li,
                        time=times[i], level=price, level_type=lvl["type"], side=side,
                        idea_bias="bearish" if is_high_level else "bullish",
                        wick_pierce=float(pierce), confirmed=True))
                break
    events.sort(key=lambda e: (e.confirmed_at, e.index))
    return events
