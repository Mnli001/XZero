"""SMCAnalyzer — orchestrates all detectors into one explainable snapshot.

Output is the single source of truth for:
  * the confluence engine (quant layer),
  * the AI reasoning layer (LLM advisory),
  * the "why / why-not" explainability panel in the UI,
  * the backtest strategy.

Nothing here decides to trade — it only describes market structure.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from .choch import detect_structure
from .config import SMCConfig
from .fvg import active_fvgs, detect_fvgs
from .liquidity_sweep import detect_sweeps
from .premium_discount import evaluate as evaluate_valuation
from .swings import find_swings


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


class SMCAnalyzer:
    def __init__(self, config: SMCConfig | None = None):
        self.config = config or SMCConfig()

    def analyze(self, df: pd.DataFrame, at_index: int | None = None) -> dict[str, Any]:
        """Full structure snapshot. If at_index is set, only data up to that bar
        (inclusive) is used — required for repaint-safe backtesting."""
        cfg = self.config
        if df.empty:
            return {"ok": False, "reason": "empty_dataframe"}
        work = df if at_index is None else df.iloc[: at_index + 1]
        if len(work) < cfg.swing_left + cfg.swing_right + 5:
            return {"ok": False, "reason": "insufficient_bars", "bars": len(work)}
        work = work.reset_index(drop=True)
        i = len(work) - 1

        atr = _atr(work, cfg.atr_period)
        swings = find_swings(work, cfg.swing_left, cfg.swing_right)
        sweeps = detect_sweeps(
            work, atr=atr, atr_period=cfg.atr_period,
            swing_left=cfg.swing_left, swing_right=cfg.swing_right,
            min_wick_atr_mult=cfg.sweep_min_wick_atr_mult,
            confirmation_bars=cfg.sweep_confirmation_bars,
            asian_start=cfg.asian_session_start_utc, asian_end=cfg.asian_session_end_utc,
        )
        struct_events = detect_structure(
            work, atr=atr, atr_period=cfg.atr_period,
            swing_left=cfg.swing_left, swing_right=cfg.swing_right,
            require_close=cfg.choch_require_close,
            min_break_atr_mult=cfg.choch_min_break_atr_mult,
        )
        fvgs = detect_fvgs(
            work, atr=atr, atr_period=cfg.atr_period,
            min_atr_mult=cfg.fvg_min_atr_mult, max_age_bars=cfg.fvg_max_age_bars,
            mitigation=cfg.fvg_mitigation,
        )
        valuation = evaluate_valuation(work, cfg.dealing_range_lookback, cfg.equilibrium_tolerance_pct)

        # Only events knowable at bar i (confirmed_at <= i) — repaint-safe.
        sweeps = [e for e in sweeps if e.confirmed_at <= i]
        struct_events = [e for e in struct_events if e.index <= i]
        last_sweep = sweeps[-1] if sweeps else None
        last_struct = struct_events[-1] if struct_events else None
        actives = active_fvgs(fvgs, at_index=i)

        # Bias: most recent confirmed idea (sweep bias, then structure side).
        bias = "neutral"
        bias_source: str | None = None
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

        # Retest check: is price inside an active FVG aligned with bias?
        price = float(work["close"].iloc[i])
        a = float(atr.iloc[i]) if not pd.isna(atr.iloc[i]) else 0.0
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
            "structure_break": last_struct is not None,  # BOS or CHoCH
            "fvg": len(actives) > 0,
            "valuation": valuation is not None and (
                (bias == "bullish" and valuation.zone == "discount")
                or (bias == "bearish" and valuation.zone == "premium")
            ),
            "retest": retest_zone is not None,
        }

        return {
            "ok": True,
            "bar_index": i,
            "time": str(work["time"].iloc[i]),
            "price": price,
            "atr": a,
            "bias": bias,
            "bias_source": bias_source,
            "checklist": checklist,
            "sweep": asdict(last_sweep) if last_sweep else None,
            "structure": asdict(last_struct) if last_struct else None,
            "active_fvgs": [asdict(z) for z in actives],
            "valuation": asdict(valuation) if valuation else None,
            "swings_tail": swings.tail(6).to_dict(orient="records") if not swings.empty else [],
            "config": cfg.to_dict(),
        }


def analyze(df: pd.DataFrame, config: SMCConfig | None = None, at_index: int | None = None) -> dict[str, Any]:
    return SMCAnalyzer(config).analyze(df, at_index=at_index)
