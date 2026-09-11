"""Shared service singletons + the live signal pipeline.

Pipeline per symbol/timeframe:
  MarketData -> SMCAnalyzer -> ConfluenceScorer -> (optional) AIReasoner
  -> RiskManager.evaluate -> execution mode (alert/paper/live).
Live orders additionally require: passing gate + live MT5 bridge.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from .ai_reasoning import AIReasoner, KnowledgeBase, ReasonRequest
from .backtest_engine.strategy import SMCStrategy, StrategyParams
from .config import settings
from .confluence_engine import ConfluenceScorer, add_indicators
from .database import SessionLocal
from .execution_modes import Gate, PaperEngine
from .journal_logger import JournalLogger, TelegramNotifier
from .models import LiveTrade, PaperTrade, Strategy
from .mt5_bridge import MarketData, MT5Client, OrderExecutor, OrderRequest
from .risk_manager import CircuitBreaker, GuardConfig, MarketGuards, PositionSizing, RiskManager
from .smc_analyzer import SMCAnalyzer


@lru_cache(maxsize=1)
def get_mt5_client() -> MT5Client:
    c = MT5Client()
    c.connect()
    return c


@lru_cache(maxsize=1)
def get_market_data() -> MarketData:
    return MarketData(get_mt5_client())


@lru_cache(maxsize=1)
def get_risk_manager() -> RiskManager:
    sizing = PositionSizing(default_risk_pct=settings.default_risk_pct, max_risk_pct=settings.max_risk_pct)
    breaker = CircuitBreaker(state_path=settings.circuit_path,
                             max_consecutive_losses=settings.circuit_max_consec_losses,
                             lock_hours=settings.circuit_lock_hours,
                             allow_reset=settings.allow_circuit_reset)
    return RiskManager(sizing=sizing, breaker=breaker, guards=MarketGuards(GuardConfig()))


@lru_cache(maxsize=1)
def get_journal() -> JournalLogger:
    return JournalLogger(settings.journal_path)


@lru_cache(maxsize=1)
def get_notifier() -> TelegramNotifier:
    return TelegramNotifier()


@lru_cache(maxsize=1)
def get_kb() -> KnowledgeBase:
    return KnowledgeBase(settings.knowledge_dir)


@lru_cache(maxsize=1)
def get_reasoner() -> AIReasoner:
    return AIReasoner(kb=get_kb())


@lru_cache(maxsize=1)
def get_gate() -> Gate:
    return Gate()


@lru_cache(maxsize=1)
def get_paper() -> PaperEngine:
    return PaperEngine()


@lru_cache(maxsize=1)
def get_executor() -> OrderExecutor:
    return OrderExecutor(get_mt5_client())


def get_strategy_row(name: str) -> Strategy | None:
    db = SessionLocal()
    try:
        return db.query(Strategy).filter(Strategy.name == name).first()
    finally:
        db.close()


def ensure_strategy(name: str = "smc_fvg_retest_v1", symbol: str = "EURUSD", timeframe: str = "M5") -> dict:
    db = SessionLocal()
    try:
        row = db.query(Strategy).filter(Strategy.name == name).first()
        if row is None:
            row = Strategy(name=name, symbol=symbol, timeframe=timeframe, params=StrategyParams().to_dict())
            db.add(row)
            db.commit()
            db.refresh(row)
        return {"name": row.name, "symbol": row.symbol, "timeframe": row.timeframe,
                "params": row.params, "mode": row.mode,
                "backtest_gate": row.backtest_gate, "paper_gate": row.paper_gate,
                "live_trades": row.live_trades}
    finally:
        db.close()


def analyze_symbol(symbol: str, timeframe: str, count: int = 300, strategy_params: dict | None = None) -> dict[str, Any]:
    """Run the full read-only analysis pipeline (no orders)."""
    md = get_market_data()
    payload = md.get_candles(symbol, timeframe, count)
    df = md.to_frame(payload)
    params = StrategyParams.from_dict(strategy_params) if strategy_params else StrategyParams()
    strategy = SMCStrategy(params)
    prepared = strategy.prepare(df)
    i = len(prepared) - 1
    sig = strategy.signal(prepared, i)
    smc = sig.get("smc", {})
    out = {
        "symbol": symbol, "timeframe": timeframe, "data_source": payload["data_source"],
        "time": str(df["time"].iloc[-1]), "price": float(df["close"].iloc[-1]),
        "candles": payload["candles"][-120:],
        "signal": {k: sig.get(k) for k in ("action", "side", "price", "sl", "tp", "reason", "risk_dist")},
        "explanation": sig.get("explanation"),
        "confluence": sig.get("confluence"),
        "smc": {
            "bias": smc.get("bias"), "bias_source": smc.get("bias_source"),
            "checklist": smc.get("checklist"), "sweep": smc.get("sweep"),
            "structure": smc.get("structure"), "active_fvgs": (smc.get("active_fvgs") or [])[-5:],
            "valuation": smc.get("valuation"),
        },
        "risk": get_risk_manager().breaker.status(),
    }
    return out


def review_with_ai(analysis: dict[str, Any]) -> dict[str, Any]:
    sig = analysis.get("signal", {})
    smc = analysis.get("smc", {})
    req = ReasonRequest(
        symbol=analysis["symbol"], timeframe=analysis["timeframe"],
        side=sig.get("side", "flat"), price=sig.get("price") or analysis["price"],
        sl=sig.get("sl") or 0.0, tp=sig.get("tp") or 0.0,
        smc_checklist=smc.get("checklist") or {},
        confluence_score=(analysis.get("confluence") or {}).get("score", 0.0) or 0.0,
        bias=smc.get("bias", "neutral"),
    )
    return get_reasoner().review(req).model_dump()
