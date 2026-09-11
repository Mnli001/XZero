"""MT5 bridge: market data + order execution.

CRITICAL INFRA NOTE (§3.1): the `MetaTrader5` package runs on WINDOWS ONLY.
On Linux (Vercel, this dev container) the bridge runs in MOCK mode — clearly
labeled `data_source: "mock"` — so the dashboard, backtests and paper trading
work end-to-end without MT5. Production MT5 connectivity runs on a Windows VPS
against the same API surface.
"""
from .client import MT5Client, MT5Mode
from .executor import OrderExecutor, OrderRequest, OrderResult
from .market_data import MarketData

__all__ = ["MT5Client", "MT5Mode", "OrderExecutor", "OrderRequest", "OrderResult", "MarketData"]
