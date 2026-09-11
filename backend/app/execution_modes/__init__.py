"""Execution modes + the Backtest Gate (§2.1, §2.2).

Modes: ALERT_ONLY -> PAPER -> LIVE_AUTO. Live Auto unlocks ONLY when a
strategy passes backtest thresholds AND paper-trade thresholds. Status badges
(Unvalidated/Backtested/Paper-Tested/Live-Verified) are derived here — the UI
only renders them.
"""
from .gate import Gate, GateThresholds, StrategyStatus, derive_status, evaluate_backtest, evaluate_paper, gate_decision
from .modes import ExecutionMode, ModeState
from .paper_engine import PaperEngine

__all__ = ["Gate", "GateThresholds", "StrategyStatus", "derive_status", "evaluate_backtest",
           "evaluate_paper", "gate_decision", "ExecutionMode", "ModeState", "PaperEngine"]
