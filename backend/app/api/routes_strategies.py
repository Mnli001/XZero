"""Strategy registry + status badges + execution mode control."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..backtest_engine.metrics import compute_metrics
from ..database import SessionLocal
from ..execution_modes import ExecutionMode, Gate, derive_status
from ..models import PaperTrade, Strategy
from ..services import ensure_strategy, get_gate

router = APIRouter(prefix="/strategies", tags=["strategies"])


class ModeRequest(BaseModel):
    mode: ExecutionMode


def _paper_metrics(strategy: str) -> dict:
    db = SessionLocal()
    try:
        rows = db.query(PaperTrade).filter(PaperTrade.strategy == strategy, PaperTrade.status == "closed").all()
        trades = [{"pnl": r.pnl or 0.0, "r_multiple": r.r_multiple or 0.0} for r in rows]
        eq = [10_000.0]
        b = 10_000.0
        for t in trades:
            b += t["pnl"]
            eq.append(b)
        return compute_metrics(trades, eq, None, 10_000.0)
    finally:
        db.close()


def _serialize(row: Strategy) -> dict:
    gate = get_gate()
    paper_m = _paper_metrics(row.name)
    paper_eval = gate.check_paper(paper_m)
    decision = gate.decide(row.backtest_gate, paper_eval if paper_eval["passed"] or paper_m["trade_count"] > 0 else None)
    # persist paper gate snapshot
    db = SessionLocal()
    try:
        fresh = db.query(Strategy).filter(Strategy.id == row.id).first()
        if fresh is not None:
            fresh.paper_gate = paper_eval
            db.commit()
    finally:
        db.close()
    status = derive_status(row.backtest_gate, paper_eval, row.live_trades)
    return {
        "name": row.name, "symbol": row.symbol, "timeframe": row.timeframe,
        "mode": row.mode, "status": status,
        "backtest_gate": row.backtest_gate, "paper_gate": paper_eval,
        "paper_metrics": paper_m, "live_trades": row.live_trades,
        "live_auto_allowed": decision["live_auto_allowed"], "gate_reasons": decision["reasons"],
    }


@router.get("")
def list_strategies():
    ensure_strategy()
    db = SessionLocal()
    try:
        rows = db.query(Strategy).all()
        ids = [r.id for r in rows]
    finally:
        db.close()
    db = SessionLocal()
    try:
        return {"strategies": [_serialize(db.query(Strategy).get(i)) for i in ids]}
    finally:
        db.close()


@router.get("/{name}")
def get_strategy(name: str):
    db = SessionLocal()
    try:
        row = db.query(Strategy).filter(Strategy.name == name).first()
        if not row:
            raise HTTPException(404, "strategy not found")
        return _serialize(row)
    finally:
        db.close()


@router.post("/{name}/mode")
def set_mode(name: str, req: ModeRequest):
    db = SessionLocal()
    try:
        row = db.query(Strategy).filter(Strategy.name == name).first()
        if not row:
            raise HTTPException(404, "strategy not found")
        gate = get_gate()
        paper_m = _paper_metrics(name)
        paper_eval = gate.check_paper(paper_m)
        decision = gate.decide(row.backtest_gate, paper_eval)
        if req.mode == ExecutionMode.LIVE_AUTO and not decision["live_auto_allowed"]:
            raise HTTPException(403, {"detail": "Live Auto locked by Backtest Gate", "reasons": decision["reasons"]})
        row.mode = req.mode.value
        db.commit()
        return {"ok": True, "mode": row.mode, "gate": decision}
    finally:
        db.close()
