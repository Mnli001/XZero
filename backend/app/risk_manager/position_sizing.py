"""Position sizing with hardcoded risk caps (§2.4).

Risk% is clamped server-side: default 2%, absolute max 5%. Any caller asking
for more gets clamped (and told about it) — never silently granted.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SizingResult:
    lots: float
    risk_amount: float
    risk_pct_applied: float
    risk_pct_requested: float
    clamped: bool
    stop_distance_price: float
    value_per_lot_per_point: float
    notes: list[str]


class PositionSizing:
    HARD_MAX_RISK_PCT = 5.0
    DEFAULT_RISK_PCT = 2.0

    def __init__(self, default_risk_pct: float = DEFAULT_RISK_PCT, max_risk_pct: float = HARD_MAX_RISK_PCT):
        if max_risk_pct > self.HARD_MAX_RISK_PCT:
            raise ValueError(f"max_risk_pct {max_risk_pct} exceeds hardcoded ceiling {self.HARD_MAX_RISK_PCT}")
        self.default_risk_pct = min(default_risk_pct, max_risk_pct)
        self.max_risk_pct = max_risk_pct

    def calculate(
        self,
        balance: float,
        entry: float,
        stop_loss: float,
        tick_value: float,
        tick_size: float,
        risk_pct: float | None = None,
        volume_min: float = 0.01,
        volume_max: float = 100.0,
        volume_step: float = 0.01,
        contract_point_value: float | None = None,
    ) -> SizingResult:
        notes: list[str] = []
        requested = self.default_risk_pct if risk_pct is None else risk_pct
        applied = requested
        clamped = False
        if applied > self.max_risk_pct:
            notes.append(f"risk_pct {applied}% exceeds max {self.max_risk_pct}% — clamped server-side")
            applied = self.max_risk_pct
            clamped = True
        if applied <= 0:
            raise ValueError("risk_pct must be positive")
        if balance <= 0:
            raise ValueError("balance must be positive")
        if tick_size <= 0 or tick_value <= 0:
            raise ValueError("tick_size and tick_value must be positive")

        stop_dist = abs(entry - stop_loss)
        if stop_dist <= 0:
            raise ValueError("entry and stop_loss must differ")

        risk_amount = balance * applied / 100.0
        # Loss for 1.0 lot if SL is hit:
        ticks_in_stop = stop_dist / tick_size
        loss_per_lot = ticks_in_stop * tick_value
        if loss_per_lot <= 0:
            raise ValueError("invalid stop/tick geometry")
        lots = risk_amount / loss_per_lot

        # Round down to broker step, clamp to min/max (epsilon guards float dust)
        lots = int(lots / volume_step + 1e-9) * volume_step
        lots = round(lots, 8)
        if lots < volume_min:
            notes.append(f"computed lots {lots} below broker minimum {volume_min} — trade too small for this stop")
            lots = 0.0
        if lots > volume_max:
            notes.append(f"computed lots {lots} above broker maximum {volume_max} — clamped")
            lots = volume_max

        actual_risk = lots * loss_per_lot
        return SizingResult(
            lots=lots,
            risk_amount=round(actual_risk, 2),
            risk_pct_applied=applied,
            risk_pct_requested=requested,
            clamped=clamped,
            stop_distance_price=stop_dist,
            value_per_lot_per_point=tick_value / tick_size,
            notes=notes,
        )
