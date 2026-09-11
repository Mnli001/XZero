"""Performance metrics — the ONLY legal source of stats for the UI (§2.3)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def compute_metrics(
    trades: list[dict],
    equity: list[float],
    equity_times: list[str] | None = None,
    initial_balance: float = 10_000.0,
    periods_per_year: int = 252 * 288,  # ~M5 bars/year; used only for Sharpe annualisation
) -> dict:
    n = len(trades)
    if n == 0 or not equity:
        return {
            "trade_count": 0, "win_rate": None, "expectancy": None, "expectancy_r": None,
            "profit_factor": None, "max_drawdown": 0.0, "max_drawdown_pct": 0.0,
            "sharpe": None, "total_return_pct": 0.0, "final_equity": initial_balance,
            "note": "insufficient_data — no completed trades",
        }
    pnl = np.array([t["pnl"] for t in trades], dtype=float)
    r_mult = np.array([t.get("r_multiple", 0.0) for t in trades], dtype=float)
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0

    eq = np.array(equity, dtype=float)
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq)
    dd_pct = np.where(peak > 0, dd / peak * 100.0, 0.0)
    max_dd = float(dd.max())
    max_dd_pct = float(dd_pct.max())

    rets = np.diff(eq) / np.where(eq[:-1] != 0, eq[:-1], np.nan)
    rets = rets[~np.isnan(rets)]
    if len(rets) > 1 and float(rets.std(ddof=1)) > 0:
        sharpe = float(rets.mean() / rets.std(ddof=1) * math.sqrt(periods_per_year))
    else:
        sharpe = None

    return {
        "trade_count": n,
        "win_rate": round(float(len(wins) / n * 100), 2),
        "expectancy": round(float(pnl.mean()), 2),
        "expectancy_r": round(float(r_mult.mean()), 3),
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else None,
        "avg_win": round(float(wins.mean()), 2) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 2) if len(losses) else 0.0,
        "max_drawdown": round(max_dd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "sharpe": round(sharpe, 3) if sharpe is not None else None,
        "total_return_pct": round((float(eq[-1]) - initial_balance) / initial_balance * 100, 2),
        "final_equity": round(float(eq[-1]), 2),
        "note": "ok" if n >= 30 else "low_sample — fewer than 30 trades, treat stats as preliminary",
    }
