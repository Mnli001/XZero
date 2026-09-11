"""SMC/ICT detection module.

All detection rules are parameterized via SMCConfig (UI-tunable, never hardcoded
thresholds). Pure functions over OHLC DataFrames — no MT5 dependency, so the
backtest engine can run on plain CSV files.
"""
from .config import SMCConfig
from .analyzer import SMCAnalyzer, analyze

__all__ = ["SMCConfig", "SMCAnalyzer", "analyze"]
