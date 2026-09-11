"""The Backtest Gate (§2.1): no live auto-execution without proof."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StrategyStatus(str, Enum):
    UNVALIDATED = "Unvalidated"
    BACKTESTED = "Backtested"
    PAPER_TESTED = "Paper-Tested"
    LIVE_VERIFIED = "Live-Verified"


@dataclass
class GateThresholds:
    min_backtest_trades: int = 30
    min_expectancy_r: float = 0.0      # must be strictly positive edge
    max_drawdown_pct: float = 25.0
    min_profit_factor: float = 1.1
    min_paper_trades: int = 30
    min_paper_expectancy_r: float = 0.0


def evaluate_backtest(oos_metrics: dict, t: GateThresholds | None = None) -> dict:
    """Check OOS backtest metrics against gate thresholds."""
    t = t or GateThresholds()
    checks = {
        "trades>=30": (oos_metrics.get("trade_count", 0) or 0) >= t.min_backtest_trades,
        "expectancy_r>0": (oos_metrics.get("expectancy_r") or 0) > t.min_expectancy_r,
        "max_dd<=25%": (oos_metrics.get("max_drawdown_pct") or 100) <= t.max_drawdown_pct,
        "profit_factor>=1.1": (oos_metrics.get("profit_factor") or 0) >= t.min_profit_factor,
    }
    return {"passed": all(checks.values()), "checks": checks,
            "metrics": {k: oos_metrics.get(k) for k in ("trade_count", "expectancy_r", "max_drawdown_pct", "profit_factor", "win_rate", "sharpe")}}


def evaluate_paper(paper_metrics: dict, t: GateThresholds | None = None) -> dict:
    t = t or GateThresholds()
    checks = {
        "paper_trades>=30": (paper_metrics.get("trade_count", 0) or 0) >= t.min_paper_trades,
        "paper_expectancy_r>0": (paper_metrics.get("expectancy_r") or 0) > t.min_paper_expectancy_r,
    }
    return {"passed": all(checks.values()), "checks": checks,
            "metrics": {k: paper_metrics.get(k) for k in ("trade_count", "expectancy_r", "win_rate")}}


def derive_status(backtest: dict | None, paper: dict | None, live_trades: int = 0) -> str:
    if live_trades > 0 and paper and paper.get("passed") and backtest and backtest.get("passed"):
        return f"{StrategyStatus.LIVE_VERIFIED.value} ({live_trades} trades)"
    if paper and paper.get("passed"):
        return StrategyStatus.PAPER_TESTED.value
    if backtest and backtest.get("passed"):
        return StrategyStatus.BACKTESTED.value
    return StrategyStatus.UNVALIDATED.value


def gate_decision(backtest: dict | None, paper: dict | None, thresholds: GateThresholds | None = None) -> dict:
    """Can this strategy enable Live Auto? Returns decision + UI-ready reasons."""
    reasons: list[str] = []
    bt_ok = bool(backtest and backtest.get("passed"))
    pp_ok = bool(paper and paper.get("passed"))
    if not bt_ok:
        failed = [k for k, v in (backtest or {}).get("checks", {}).items() if not v]
        reasons.append("backtest gate NOT passed" + (f" (failed: {', '.join(failed)})" if failed else " (no passing backtest report)"))
    else:
        reasons.append("backtest gate passed")
    if not pp_ok:
        failed = [k for k, v in (paper or {}).get("checks", {}).items() if not v]
        reasons.append("paper gate NOT passed" + (f" (failed: {', '.join(failed)})" if failed else " (needs ≥30 paper trades with positive expectancy)"))
    else:
        reasons.append("paper gate passed")
    allowed = bt_ok and pp_ok
    if allowed:
        reasons.append("Live Auto UNLOCKED — risk manager still approves every order")
    else:
        reasons.append("Live Auto LOCKED until both gates pass")
    return {"live_auto_allowed": allowed, "reasons": reasons, "status": derive_status(backtest, paper)}


class Gate:
    """Thin wrapper keeping thresholds configurable per deployment."""

    def __init__(self, thresholds: GateThresholds | None = None):
        self.thresholds = thresholds or GateThresholds()

    def check_backtest(self, oos_metrics: dict) -> dict:
        return evaluate_backtest(oos_metrics, self.thresholds)

    def check_paper(self, paper_metrics: dict) -> dict:
        return evaluate_paper(paper_metrics, self.thresholds)

    def decide(self, backtest: dict | None, paper: dict | None) -> dict:
        return gate_decision(backtest, paper, self.thresholds)
