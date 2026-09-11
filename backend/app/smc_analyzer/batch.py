"""BatchContext — precompute structure ONCE per dataset, snapshot at any bar.

Repaint-safe by construction: every event carries the bar index it was knowable
at, and snapshot_at(i) only exposes events with index <= i (levels additionally
must be *confirmed* by bar i). Results are identical to calling
SMCAnalyzer.analyze(df, at_index=i) per bar, but O(n) total instead of O(n^2).

Used by the backtest simulator. Live analysis (single shot) keeps the simple
per-call path in analyzer.py.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import asdict
from typing import Any

import pandas as pd

from .choch import detect_structure
from .config import SMCConfig
from .fvg import detect_fvgs
from .liquidity_sweep import detect_sweeps
from .premium_discount import evaluate as evaluate_valuation
from .swings import find_swings


class BatchContext:
    def __init__(self, df: pd.DataFrame, config: SMCConfig | None = None):
        self.config = config or SMCConfig()
        cfg = self.config
        self.df = df.reset_index(drop=True)
        h, l, c = self.df["high"], self.df["low"], self.df["close"]
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        self.atr = tr.ewm(alpha=1 / cfg.atr_period, min_periods=cfg.atr_period, adjust=False).mean()

        self.swings = find_swings(self.df, cfg.swing_left, cfg.swing_right)
        self.struct_events = detect_structure(
            self.df, atr=self.atr, atr_period=cfg.atr_period,
            swing_left=cfg.swing_left, swing_right=cfg.swing_right,
            require_close=cfg.choch_require_close, min_break_atr_mult=cfg.choch_min_break_atr_mult)
        self.sweeps = detect_sweeps(
            self.df, atr=self.atr, atr_period=cfg.atr_period,
            swing_left=cfg.swing_left, swing_right=cfg.swing_right,
            min_wick_atr_mult=cfg.sweep_min_wick_atr_mult,
            confirmation_bars=cfg.sweep_confirmation_bars,
            asian_start=cfg.asian_session_start_utc, asian_end=cfg.asian_session_end_utc)
        self.fvgs = detect_fvgs(
            self.df, atr=self.atr, atr_period=cfg.atr_period,
            min_atr_mult=cfg.fvg_min_atr_mult, max_age_bars=cfg.fvg_max_age_bars,
            mitigation=cfg.fvg_mitigation)

        self._struct_idx = [e.index for e in self.struct_events]
        self._sweep_idx = [e.index for e in self.sweeps]

    # ── snapshot ────────────────────────────────────────────────
    def snapshot_at(self, i: int) -> dict[str, Any]:
        cfg = self.config
        df, n = self.df, len(self.df)
        if i >= n:
            i = n - 1
        if i < cfg.swing_left + cfg.swing_right + 4:
            return {"ok": False, "reason": "insufficient_bars", "bars": i + 1}

        # Last structure event knowable at bar i (event bar itself is knowable).
        si = bisect_right(self._struct_idx, i) - 1
        last_struct = self.struct_events[si] if si >= 0 else None

        # Last sweep knowable at bar i (confirmed_at <= i).
        last_sweep = None
        for e in self.sweeps:
            if e.confirmed_at > i:
                break
            last_sweep = e

        actives = [z for z in self.fvgs
                   if z.index + 1 <= i
                   and (z.mitigated_index is None or z.mitigated_index > i)
                   and (i - (z.index + 1) < cfg.fvg_max_age_bars)]

        valuation = evaluate_valuation(df, cfg.dealing_range_lookback, cfg.equilibrium_tolerance_pct, at_index=i)

        bias, bias_source = "neutral", None
        if last_struct is not None and last_sweep is not None:
            if last_struct.index >= last_sweep.index:
                bias = "bullish" if "bullish" in last_struct.kind else "bearish"
                bias_source = last_struct.kind
            else:
                bias = last_sweep.idea_bias
                bias_source = f"sweep_{last_sweep.side}"
        elif last_struct is not None:
            bias = "bullish" if "bullish" in last_struct.kind else "bearish"
            bias_source = last_struct.kind
        elif last_sweep is not None:
            bias = last_sweep.idea_bias
            bias_source = f"sweep_{last_sweep.side}"

        price = float(df["close"].iloc[i])
        a = self.atr.iloc[i]
        a = float(a) if a == a else 0.0
        tol = cfg.retest_tolerance_atr_mult * a
        retest_zone = None
        for z in actives:
            aligned = (z.direction == "bullish" and bias == "bullish") or (z.direction == "bearish" and bias == "bearish")
            if aligned and (z.bottom - tol) <= price <= (z.top + tol):
                retest_zone = z
                break

        checklist = {
            "sweep": last_sweep is not None,
            "choch": last_struct is not None and last_struct.kind.startswith("choch"),
            "structure_break": last_struct is not None,
            "fvg": len(actives) > 0,
            "valuation": valuation is not None and (
                (bias == "bullish" and valuation.zone == "discount")
                or (bias == "bearish" and valuation.zone == "premium")),
            "retest": retest_zone is not None,
        }
        return {
            "ok": True, "bar_index": i, "time": str(df["time"].iloc[i]),
            "price": price, "atr": a, "bias": bias, "bias_source": bias_source,
            "checklist": checklist,
            "sweep": asdict(last_sweep) if last_sweep else None,
            "structure": asdict(last_struct) if last_struct else None,
            "active_fvgs": [asdict(z) for z in actives],
            "valuation": asdict(valuation) if valuation else None,
            "config": cfg.to_dict(),
        }
