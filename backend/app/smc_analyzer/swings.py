"""Fractal swing high/low detection."""
from __future__ import annotations

import pandas as pd


def find_swings(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    """Return swing points as DataFrame with columns: index, time, price, kind.

    kind is "high" or "low". `index` is the positional bar index in `df`.
    A confirmed swing at bar i needs `right` bars after it (repaint-safe: only
    swings with index <= len(df)-1-right are returned).
    """
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    n = len(df)
    rows: list[dict] = []
    for i in range(left, n - right):
        window_h = highs[i - left : i + right + 1]
        window_l = lows[i - left : i + right + 1]
        if highs[i] == window_h.max() and (window_h == highs[i]).sum() == 1:
            rows.append({"index": i, "time": df["time"].iloc[i], "price": float(highs[i]), "kind": "high"})
        if lows[i] == window_l.min() and (window_l == lows[i]).sum() == 1:
            rows.append({"index": i, "time": df["time"].iloc[i], "price": float(lows[i]), "kind": "low"})
    out = pd.DataFrame(rows, columns=["index", "time", "price", "kind"])
    return out.sort_values("index").reset_index(drop=True)


def last_swing(df_swings: pd.DataFrame, kind: str) -> dict | None:
    sub = df_swings[df_swings["kind"] == kind]
    if sub.empty:
        return None
    r = sub.iloc[-1]
    return {"index": int(r["index"]), "time": r["time"], "price": float(r["price"]), "kind": kind}
