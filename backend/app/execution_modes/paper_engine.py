"""Paper trading engine: real-time data, virtual fills, real accounting.

Fills at tick bid/ask + slippage, tracks SL/TP, and feeds the same metrics +
circuit-breaker path as live so paper stats are directly comparable.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class PaperPosition:
    id: str
    symbol: str
    side: str
    lots: float
    entry: float
    sl: float
    tp: float
    opened_at: str
    confidence: float | None = None
    checklist: dict = field(default_factory=dict)
    reasoning: str = ""


class PaperEngine:
    def __init__(self, balance: float = 10_000.0, slippage_price: float = 0.0):
        self.balance = balance
        self.start_balance = balance
        self.slippage = slippage_price
        self.positions: dict[str, PaperPosition] = {}
        self.closed: list[dict] = []

    def open(self, symbol: str, side: str, lots: float, price: float, sl: float, tp: float,
             confidence: float | None = None, checklist: dict | None = None, reasoning: str = "") -> PaperPosition:
        fill = price + self.slippage * (1 if side == "buy" else -1)
        pos = PaperPosition(str(uuid.uuid4())[:8], symbol, side, lots, fill, sl, tp,
                            datetime.now(timezone.utc).isoformat(), confidence, checklist or {}, reasoning)
        self.positions[pos.id] = pos
        return pos

    def on_tick(self, symbol: str, bid: float, ask: float, tick_value: float = 1.0, tick_size: float = 0.01) -> list[dict]:
        """Push a tick; returns list of positions closed by this tick."""
        closed_now: list[dict] = []
        for pid, p in list(self.positions.items()):
            if p.symbol != symbol:
                continue
            exit_px = None
            reason = ""
            if p.side == "buy":
                if bid <= p.sl:
                    exit_px, reason = p.sl, "sl"
                elif bid >= p.tp:
                    exit_px, reason = p.tp, "tp"
            else:
                if ask >= p.sl:
                    exit_px, reason = p.sl, "sl"
                elif ask <= p.tp:
                    exit_px, reason = p.tp, "tp"
            if exit_px is not None:
                pnl = (exit_px - p.entry) * (1 if p.side == "buy" else -1) / tick_size * tick_value * p.lots
                self.balance += pnl
                rec = {**asdict(p), "exit_price": exit_px, "exit_reason": reason, "pnl": round(pnl, 2),
                       "closed_at": datetime.now(timezone.utc).isoformat(),
                       "r_multiple": round((exit_px - p.entry) * (1 if p.side == "buy" else -1) / abs(p.entry - p.sl), 3) if p.entry != p.sl else 0.0}
                self.closed.append(rec)
                del self.positions[pid]
                closed_now.append(rec)
        return closed_now

    def metrics(self) -> dict:
        from ..backtest_engine.metrics import compute_metrics
        eq = [self.start_balance]
        b = self.start_balance
        for t in self.closed:
            b += t["pnl"]
            eq.append(b)
        return compute_metrics(self.closed, eq, None, self.start_balance)
