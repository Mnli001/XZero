"""Weighted confluence scorer.

score = weighted sum of normalized feature votes, scaled to 0–100.
Weights are tunable (UI/backtest), NOT hardcoded magic — defaults below are a
neutral starting point and must be re-tuned per symbol/timeframe.

IMPORTANT (§2.6): this score is a RELATIVE confluence measure, not a win
probability. The UI must display that disclaimer next to every score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ScorerWeights:
    trend_ema_stack: float = 1.0
    momentum_rsi: float = 1.0
    trend_strength_adx: float = 1.0
    smc_checklist: float = 2.0
    valuation_align: float = 1.5

    def to_dict(self) -> dict:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "ScorerWeights":
        known = {k: float(v) for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


class ConfluenceScorer:
    def __init__(self, weights: ScorerWeights | None = None):
        self.weights = weights or ScorerWeights()

    def score(self, df: pd.DataFrame, i: int, smc: dict[str, Any]) -> dict[str, Any]:
        """Score bar i. `df` must include indicator columns (see add_indicators)."""
        w = self.weights
        row = df.iloc[i]
        bias = smc.get("bias", "neutral")
        direction = 1 if bias == "bullish" else (-1 if bias == "bearish" else 0)

        votes: dict[str, float] = {}

        # 1. EMA stack alignment
        if direction == 0 or pd.isna(row.get("ema9")) or pd.isna(row.get("ema50")):
            votes["trend_ema_stack"] = 0.0
        else:
            e9, e21, e50 = float(row["ema9"]), float(row["ema21"]), float(row["ema50"])
            if direction == 1:
                votes["trend_ema_stack"] = 1.0 if e9 > e21 > e50 else (0.5 if e9 > e50 else 0.0)
            else:
                votes["trend_ema_stack"] = 1.0 if e9 < e21 < e50 else (0.5 if e9 < e50 else 0.0)

        # 2. RSI momentum (not overbought/oversold against us)
        rsi_v = float(row.get("rsi", 50.0))
        if direction == 1:
            votes["momentum_rsi"] = 1.0 if 50 <= rsi_v <= 70 else (0.5 if 45 <= rsi_v < 50 else 0.0)
        elif direction == -1:
            votes["momentum_rsi"] = 1.0 if 30 <= rsi_v <= 50 else (0.5 if 50 < rsi_v <= 55 else 0.0)
        else:
            votes["momentum_rsi"] = 0.0

        # 3. ADX trend strength + DI alignment
        adx_v = float(row.get("adx", 0.0) or 0.0)
        pdi = float(row.get("plus_di", 0.0) or 0.0)
        mdi = float(row.get("minus_di", 0.0) or 0.0)
        di_ok = (direction == 1 and pdi > mdi) or (direction == -1 and mdi > pdi)
        strength = min(adx_v / 25.0, 1.0)
        votes["trend_strength_adx"] = round(strength if di_ok else strength * 0.3, 3)

        # 4. SMC checklist completion
        checklist = smc.get("checklist", {}) or {}
        keys = ["sweep", "structure_break", "fvg", "valuation", "retest"]
        done = sum(1 for k in keys if checklist.get(k))
        votes["smc_checklist"] = done / len(keys)

        # 5. Valuation alignment
        votes["valuation_align"] = 1.0 if checklist.get("valuation") else 0.0

        weight_map = {
            "trend_ema_stack": w.trend_ema_stack,
            "momentum_rsi": w.momentum_rsi,
            "trend_strength_adx": w.trend_strength_adx,
            "smc_checklist": w.smc_checklist,
            "valuation_align": w.valuation_align,
        }
        total_w = sum(weight_map.values()) or 1.0
        total = sum(votes[k] * weight_map[k] for k in votes) / total_w
        return {
            "score": round(total * 100, 1),
            "bias": bias,
            "votes": votes,
            "weights": weight_map,
            "disclaimer": "Relative confluence measure, NOT a win probability.",
        }


def score(df: pd.DataFrame, i: int, smc: dict[str, Any], weights: ScorerWeights | None = None) -> dict[str, Any]:
    return ConfluenceScorer(weights).score(df, i, smc)
