"""Market guards: spread-spike filter + rollover blackout + daily loss limit."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone


@dataclass
class GuardConfig:
    spread_max_mult: float = 2.0       # block if spread > avg * mult
    spread_avg_window: int = 100
    rollover_start_utc: str = "23:55"  # daily blackout window (server time approx UTC)
    rollover_end_utc: str = "00:15"
    daily_loss_limit_pct: float = 6.0  # block new trades if day P&L < -limit
    max_open_positions: int = 3
    max_open_risk_pct: float = 6.0


class MarketGuards:
    def __init__(self, config: GuardConfig | None = None):
        self.config = config or GuardConfig()

    def check_spread(self, current_spread: float, recent_spreads: list[float]) -> tuple[bool, str]:
        if current_spread < 0:
            return False, "negative spread quote — refusing to trade on bad feed"
        if len(recent_spreads) < 10:
            return True, "spread history too short — guard passes open (warn)"
        avg = sum(recent_spreads[-self.config.spread_avg_window:]) / min(len(recent_spreads), self.config.spread_avg_window)
        if avg <= 0:
            return True, "spread average unavailable — guard passes open (warn)"
        if current_spread > avg * self.config.spread_max_mult:
            return False, f"spread spike: {current_spread:.1f} > {self.config.spread_max_mult}x avg {avg:.1f}"
        return True, "spread ok"

    def check_rollover(self, now: datetime | None = None) -> tuple[bool, str]:
        now = now or datetime.now(timezone.utc)
        t = now.time()
        start = time.fromisoformat(self.config.rollover_start_utc)
        end = time.fromisoformat(self.config.rollover_end_utc)
        in_window = (t >= start or t <= end) if start > end else (start <= t <= end)
        if in_window:
            return False, f"rollover blackout {self.config.rollover_start_utc}–{self.config.rollover_end_utc} UTC"
        return True, "outside rollover window"

    def check_daily_loss(self, day_pnl: float, balance: float) -> tuple[bool, str]:
        if balance <= 0:
            return False, "invalid balance for daily-loss check"
        dd_pct = -day_pnl / balance * 100.0
        if dd_pct >= self.config.daily_loss_limit_pct:
            return False, f"daily loss limit hit: -{dd_pct:.2f}% >= {self.config.daily_loss_limit_pct}%"
        return True, "daily loss within limit"

    def check_exposure(self, open_positions: int, open_risk_pct: float) -> tuple[bool, str]:
        if open_positions >= self.config.max_open_positions:
            return False, f"max open positions reached ({open_positions}/{self.config.max_open_positions})"
        if open_risk_pct >= self.config.max_open_risk_pct:
            return False, f"max open risk reached ({open_risk_pct:.2f}%/{self.config.max_open_risk_pct}%)"
        return True, "exposure ok"
