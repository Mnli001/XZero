"""Reference SMC strategy evaluated by the backtest gate.

Entry model (long example; short mirrored):
  1. Liquidity sweep of lows (idea_bias bullish)
  2. Bullish CHoCH/BOS after the sweep
  3. Active bullish FVG + price in discount
  4. Retest: price trades into the FVG -> enter at close
  SL: beyond the sweep extreme (+ATR buffer). TP: R-multiple of SL distance.

Every parameter is tunable; defaults are starting points for walk-forward
tuning, not recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from ..confluence_engine import ConfluenceScorer, ScorerWeights, add_indicators
from ..smc_analyzer import SMCAnalyzer, SMCConfig
from ..smc_analyzer.batch import BatchContext


@dataclass
class StrategyParams:
    min_confluence: float = 55.0
    risk_reward: float = 2.0
    sl_atr_buffer_mult: float = 0.25
    max_hold_bars: int = 200
    use_valuation_filter: bool = True
    use_retest_trigger: bool = True
    smc: SMCConfig = None  # type: ignore
    weights: ScorerWeights = None  # type: ignore

    def __post_init__(self):
        if self.smc is None:
            self.smc = SMCConfig()
        if self.weights is None:
            self.weights = ScorerWeights()

    def to_dict(self) -> dict:
        return {
            "min_confluence": self.min_confluence,
            "risk_reward": self.risk_reward,
            "sl_atr_buffer_mult": self.sl_atr_buffer_mult,
            "max_hold_bars": self.max_hold_bars,
            "use_valuation_filter": self.use_valuation_filter,
            "use_retest_trigger": self.use_retest_trigger,
            "smc": self.smc.to_dict(),
            "weights": self.weights.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyParams":
        smc = SMCConfig.from_dict(d.get("smc", {}))
        w = ScorerWeights.from_dict(d.get("weights", {}))
        return cls(
            min_confluence=float(d.get("min_confluence", 55.0)),
            risk_reward=float(d.get("risk_reward", 2.0)),
            sl_atr_buffer_mult=float(d.get("sl_atr_buffer_mult", 0.25)),
            max_hold_bars=int(d.get("max_hold_bars", 200)),
            use_valuation_filter=bool(d.get("use_valuation_filter", True)),
            use_retest_trigger=bool(d.get("use_retest_trigger", True)),
            smc=smc, weights=w,
        )


class SMCStrategy:
    name = "smc_fvg_retest_v1"

    def __init__(self, params: StrategyParams | None = None):
        self.params = params or StrategyParams()
        self.analyzer = SMCAnalyzer(self.params.smc)
        self.scorer = ConfluenceScorer(self.params.weights)
        self._batch: BatchContext | None = None
        self._batch_id: int | None = None

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        return add_indicators(df)

    def bind(self, df: pd.DataFrame) -> "SMCStrategy":
        """Precompute structure once for a full backtest dataset (fast path).
        Results are identical to the per-bar path; repaint-safe by construction."""
        self._batch = BatchContext(df, self.params.smc)
        self._batch_id = id(df)
        return self

    def unbind(self) -> "SMCStrategy":
        self._batch = None
        self._batch_id = None
        return self

    def signal(self, df: pd.DataFrame, i: int) -> dict[str, Any]:
        """Evaluate bar i (uses data up to i only). Returns entry intent or skip."""
        p = self.params
        if self._batch is not None and self._batch_id == id(df):
            smc = self._batch.snapshot_at(i)
        else:
            smc = self.analyzer.analyze(df, at_index=i)
        if not smc.get("ok"):
            return {"action": "skip", "reason": "smc_insufficient_data", "smc": smc}
        bias = smc["bias"]
        if bias == "neutral":
            return {"action": "skip", "reason": "no_bias", "smc": smc}
        confluence = self.scorer.score(df, i, smc)
        ch = smc["checklist"]
        missing = [k for k in ["sweep", "structure_break", "fvg"] if not ch.get(k)]
        if missing:
            return {"action": "skip", "reason": f"missing: {','.join(missing)}", "smc": smc, "confluence": confluence}
        if p.use_valuation_filter and not ch.get("valuation"):
            return {"action": "skip", "reason": "valuation_mismatch", "smc": smc, "confluence": confluence}
        if p.use_retest_trigger and not ch.get("retest"):
            return {"action": "skip", "reason": "awaiting_retest", "smc": smc, "confluence": confluence}
        if confluence["score"] < p.min_confluence:
            return {"action": "skip", "reason": f"confluence {confluence['score']} < {p.min_confluence}", "smc": smc, "confluence": confluence}

        # Build SL/TP
        price = float(df["close"].iloc[i])
        atr_v = smc.get("atr") or float(df["atr"].iloc[i])
        buf = p.sl_atr_buffer_mult * (atr_v or 0)
        sweep = smc.get("sweep") or {}
        if bias == "bullish":
            ref_low = min(sweep.get("level", price), float(df["low"].iloc[i]))
            sl = ref_low - buf
            risk_dist = price - sl
            tp = price + risk_dist * p.risk_reward
            side = "buy"
        else:
            ref_high = max(sweep.get("level", price), float(df["high"].iloc[i]))
            sl = ref_high + buf
            risk_dist = sl - price
            tp = price - risk_dist * p.risk_reward
            side = "sell"
        if risk_dist <= 0:
            return {"action": "skip", "reason": "invalid_sl_geometry", "smc": smc, "confluence": confluence}
        return {
            "action": "enter", "side": side, "price": price, "sl": sl, "tp": tp,
            "risk_dist": risk_dist, "smc": smc, "confluence": confluence,
            "explanation": {
                "rules_passed": [k for k, v in ch.items() if v],
                "rules_failed": [k for k, v in ch.items() if not v],
                "confidence": confluence["score"],
                "bias_source": smc.get("bias_source"),
            },
        }
