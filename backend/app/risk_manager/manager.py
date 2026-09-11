"""RiskManager — the single server-side gate every order must pass.

Call order: circuit breaker -> execution gate -> market guards -> sizing cap.
A trade is allowed ONLY if every check passes. Failures return human-readable
reasons for the journal + UI ("why-no-trade" mode, §2.6).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .circuit_breaker import CircuitBreaker
from .guards import GuardConfig, MarketGuards
from .position_sizing import PositionSizing


@dataclass
class RiskDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    lots: float = 0.0
    risk_amount: float = 0.0
    risk_pct_applied: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reasons": self.reasons,
            "lots": self.lots,
            "risk_amount": self.risk_amount,
            "risk_pct_applied": self.risk_pct_applied,
            "details": self.details,
        }


class RiskManager:
    def __init__(
        self,
        sizing: PositionSizing | None = None,
        breaker: CircuitBreaker | None = None,
        guards: MarketGuards | None = None,
    ):
        self.sizing = sizing or PositionSizing()
        self.breaker = breaker or CircuitBreaker()
        self.guards = guards or MarketGuards()

    def evaluate(
        self,
        *,
        balance: float,
        entry: float,
        stop_loss: float,
        tick_value: float,
        tick_size: float,
        risk_pct: float | None = None,
        day_pnl: float = 0.0,
        open_positions: int = 0,
        open_risk_pct: float = 0.0,
        current_spread: float = 0.0,
        recent_spreads: list[float] | None = None,
        volume_min: float = 0.01,
        volume_max: float = 100.0,
        volume_step: float = 0.01,
    ) -> RiskDecision:
        reasons: list[str] = []
        details: dict[str, Any] = {}

        # 1. Circuit breaker (backend-owned, unbypassable)
        locked, locked_until = self.breaker.is_locked()
        details["circuit"] = self.breaker.status()
        if locked:
            return RiskDecision(False, [f"circuit breaker LOCKED until {locked_until} — 24h cooldown after consecutive losses"])

        # 2. Market guards
        ok, msg = self.guards.check_rollover()
        if not ok:
            reasons.append(msg)
        ok, msg = self.guards.check_spread(current_spread, recent_spreads or [])
        details["spread_check"] = msg
        if not ok:
            reasons.append(msg)
        ok, msg = self.guards.check_daily_loss(day_pnl, balance)
        if not ok:
            reasons.append(msg)
        ok, msg = self.guards.check_exposure(open_positions, open_risk_pct)
        if not ok:
            reasons.append(msg)
        if reasons:
            return RiskDecision(False, reasons, details=details)

        # 3. Position sizing with hardcoded cap
        try:
            s = self.sizing.calculate(
                balance, entry, stop_loss, tick_value, tick_size,
                risk_pct=risk_pct, volume_min=volume_min,
                volume_max=volume_max, volume_step=volume_step,
            )
        except ValueError as e:
            return RiskDecision(False, [f"sizing rejected: {e}"], details=details)

        details["sizing_notes"] = s.notes
        if s.lots <= 0:
            return RiskDecision(False, ["computed volume is 0 — stop too wide for balance/min-volume"] + s.notes, details=details)

        ok_reasons = ["all risk checks passed"]
        if s.clamped:
            ok_reasons.append(f"risk clamped to {s.risk_pct_applied}% (requested {s.risk_pct_requested}%)")
        return RiskDecision(True, ok_reasons, lots=s.lots, risk_amount=s.risk_amount,
                             risk_pct_applied=s.risk_pct_applied, details=details)
