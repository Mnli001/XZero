"""Tunable parameters for every SMC/ICT detection rule.

Rationale (§3.2): SMC rules require tuning per symbol/timeframe. Nothing here is
a magic constant — the web terminal exposes these for editing and the backtest
engine can grid-search them.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SMCConfig:
    # Swing detection (fractal)
    swing_left: int = 3
    swing_right: int = 3

    # Liquidity sweep: wick must pierce the level by at least this fraction of
    # ATR, then close back inside within `sweep_confirmation_bars` bars.
    sweep_min_wick_atr_mult: float = 0.15
    sweep_confirmation_bars: int = 2

    # CHoCH / BOS: break of a swing with (optional) close confirmation.
    choch_require_close: bool = True
    choch_min_break_atr_mult: float = 0.05

    # FVG: 3-candle imbalance; gap size must exceed ATR multiple; zones expire.
    fvg_min_atr_mult: float = 0.2
    fvg_max_age_bars: int = 60
    fvg_mitigation: str = "touch"  # "touch" | "close_through"

    # Premium / Discount dealing range
    dealing_range_lookback: int = 120
    equilibrium_tolerance_pct: float = 0.05  # ±5% around 50% = equilibrium

    # Retest: entry trigger zone tolerance around FVG / order-block edge
    retest_tolerance_atr_mult: float = 0.25

    # Sessions (UTC hours) for Asian high/low liquidity reference
    asian_session_start_utc: int = 0
    asian_session_end_utc: int = 7

    atr_period: int = 14

    def to_dict(self) -> dict:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "SMCConfig":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)
