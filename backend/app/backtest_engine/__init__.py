"""Backtest engine: CSV -> walk-forward simulation -> honest metrics.

§2.3: metrics shown in the UI come ONLY from here (or paper/live logs).
Missing/gappy data is flagged 'incomplete_data', never silently interpolated.
"""
from .data_loader import DataIssue, load_csv, TIMEFRAMES_MIN
from .metrics import compute_metrics
from .runner import BacktestRunner, run_backtest
from .simulator import Simulator, SimParams
from .strategy import SMCStrategy, StrategyParams
from .walkforward import walk_forward_splits

__all__ = [
    "DataIssue", "load_csv", "TIMEFRAMES_MIN",
    "compute_metrics", "BacktestRunner", "run_backtest",
    "Simulator", "SimParams",
    "SMCStrategy", "StrategyParams", "walk_forward_splits",
]
