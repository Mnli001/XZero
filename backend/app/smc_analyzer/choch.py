"""CHoCH (Change of Character) / BOS (Break of Structure) detector.

Trend is defined by the sequence of confirmed swings: higher highs + higher
lows = bullish, lower highs + lower lows = bearish. A close through the last
swing against the prevailing trend leg = CHoCH; with the trend = BOS.

Single-pass incremental implementation: O(n) — each swing is confirmed exactly
once at bar (swing_bar + swing_right), identical to the naive re-scan.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class StructureEvent:
    index: int
    time: object
    kind: str  # "choch_bullish" | "choch_bearish" | "bos_bullish" | "bos_bearish"
    broken_swing_price: float
    broken_swing_index: int


def _side_from_swings(swings: list[dict[str, Any]]) -> str:
    if len(swings) < 4:
        return "unknown"
    tail = swings[-4:]
    highs = [s["price"] for s in tail if s["kind"] == "high"]
    lows = [s["price"] for s in tail if s["kind"] == "low"]
    if len(highs) >= 2 and len(lows) >= 2:
        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            return "bullish"
        if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            return "bearish"
    return "unknown"


def detect_structure(
    df: pd.DataFrame,
    atr: pd.Series | None = None,
    atr_period: int = 14,
    swing_left: int = 3,
    swing_right: int = 3,
    require_close: bool = True,
    min_break_atr_mult: float = 0.05,
) -> list[StructureEvent]:
    if len(df) < swing_left + swing_right + 5:
        return []
    n = len(df)
    if atr is None:
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / atr_period, min_periods=atr_period, adjust=False).mean()
    atr_v = atr.to_numpy()

    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    times = df["time"].to_numpy()

    confirmed: list[dict[str, Any]] = []  # swings confirmed so far, chronological
    last_high: dict | None = None
    last_low: dict | None = None
    events: list[StructureEvent] = []

    for i in range(swing_left + swing_right + 1, n):
        # Newly confirmable swing candidate at bar j = i - swing_right.
        j = i - swing_right
        if j >= swing_left:
            wh = highs[j - swing_left : j + swing_right + 1]
            wl = lows[j - swing_left : j + swing_right + 1]
            if highs[j] == wh.max() and (wh == highs[j]).sum() == 1:
                last_high = {"index": j, "price": float(highs[j])}
                confirmed.append({"index": j, "price": float(highs[j]), "kind": "high"})
            if lows[j] == wl.min() and (wl == lows[j]).sum() == 1:
                last_low = {"index": j, "price": float(lows[j])}
                confirmed.append({"index": j, "price": float(lows[j]), "kind": "low"})
            confirmed.sort(key=lambda s: s["index"])

        if len(confirmed) < 2:
            continue
        a = atr_v[i]
        if not (a == a) or a <= 0:  # NaN check without pandas
            continue
        buf = min_break_atr_mult * a
        side = _side_from_swings(confirmed)
        fired = False
        if last_high is not None and last_high["index"] < i:
            broke = closes[i] > last_high["price"] + buf if require_close else highs[i] > last_high["price"] + buf
            if broke:
                kind = "bos_bullish" if side == "bullish" else "choch_bullish"
                events.append(StructureEvent(i, times[i], kind, last_high["price"], last_high["index"]))
                fired = True
        if last_low is not None and last_low["index"] < i and not fired:
            broke = closes[i] < last_low["price"] - buf if require_close else lows[i] < last_low["price"] - buf
            if broke:
                kind = "bos_bearish" if side == "bearish" else "choch_bearish"
                events.append(StructureEvent(i, times[i], kind, last_low["price"], last_low["index"]))
    return events
