"""Trade execution pipeline — the ONLY path that can place orders.

Flow: fresh analysis -> AI advisory -> RiskManager (binding) -> mode routing.
  * alert_only: journal + telegram, no fill
  * paper: virtual fill in PaperEngine + DB
  * live_auto: gate re-checked + live bridge required, else refused loudly
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import SessionLocal
from ..execution_modes import ExecutionMode
from ..models import LiveTrade, PaperTrade, Strategy
from ..mt5_bridge import OrderRequest
from ..services import (
    analyze_symbol, ensure_strategy, get_executor, get_gate, get_journal,
    get_notifier, get_paper, get_risk_manager, review_with_ai,
)

router = APIRouter(prefix="/execution", tags=["execution"])


class TradeRequest(BaseModel):
    symbol: str = "EURUSD"
    timeframe: str = "M5"
    strategy: str = "smc_fvg_retest_v1"
    balance: float = 10_000.0
    risk_pct: float | None = None
    tick_value: float = 1.0
    tick_size: float = 0.01
    use_ai: bool = True


@router.post("/signal")
def execute_signal(req: TradeRequest):
    journal = get_journal()
    notifier = get_notifier()
    rm = get_risk_manager()

    strat = ensure_strategy(req.strategy, req.symbol, req.timeframe)
    mode = ExecutionMode(strat["mode"])

    # 1. Fresh analysis (never trust a stale/cached signal for execution)
    try:
        a = analyze_symbol(req.symbol, req.timeframe, 300)
    except Exception as e:
        journal.log_error("analysis", str(e), {"symbol": req.symbol})
        raise HTTPException(502, f"analysis failed: {e}")
    sig = a.get("signal", {})
    if sig.get("action") != "enter":
        rec = journal.log_skip(sig.get("reason", "no_entry"), {
            "symbol": req.symbol, "timeframe": req.timeframe, "strategy": req.strategy,
            "checklist": (a.get("smc") or {}).get("checklist"),
            "confidence": (a.get("confluence") or {}).get("score")})
        return {"executed": False, "stage": "no_signal", "reason": sig.get("reason"), "journal": rec}

    # 2. AI advisory (can only veto, never force)
    ai_verdict = None
    if req.use_ai:
        try:
            ai_verdict = review_with_ai(a)
            if ai_verdict.get("verdict") != "enter":
                rec = journal.log_skip("ai_veto", {"symbol": req.symbol, "strategy": req.strategy,
                                                   "reasoning": ai_verdict.get("reasoning"),
                                                   "checklist": ai_verdict.get("checklist")})
                return {"executed": False, "stage": "ai_veto", "ai": ai_verdict, "journal": rec}
        except Exception as e:
            journal.log_error("ai_review", str(e), {"symbol": req.symbol})

    # 3. Risk gate — BINDING, server-side
    decision = rm.evaluate(
        balance=req.balance, entry=sig["price"], stop_loss=sig["sl"],
        tick_value=req.tick_value, tick_size=req.tick_size, risk_pct=req.risk_pct,
        current_spread=float((a.get("candles") or [{}])[-1].get("spread", 0) or 0),
        recent_spreads=[float(c.get("spread", 0) or 0) for c in (a.get("candles") or [])],
        open_positions=len(get_paper().positions),
    )
    if not decision.allowed:
        rec = journal.log_risk_block(decision.to_dict(), {"symbol": req.symbol, "strategy": req.strategy})
        return {"executed": False, "stage": "risk_block", "risk": decision.to_dict(), "journal": rec}

    lots = decision.lots
    conf = (a.get("confluence") or {}).get("score")
    checklist = (a.get("smc") or {}).get("checklist") or {}
    reasoning = (ai_verdict or {}).get("reasoning", "") or str((sig.get("explanation") or sig.get("reason") or ""))

    # 4. Mode routing
    if mode == ExecutionMode.ALERT_ONLY:
        rec = journal.log_signal({"symbol": req.symbol, "side": sig["side"], "lots": lots,
                                  "entry": sig["price"], "sl": sig["sl"], "tp": sig["tp"],
                                  "confidence": conf, "checklist": checklist, "reasoning": reasoning,
                                  "mode": mode.value})
        notifier.send(f"🔔 ALERT {req.symbol} {sig['side'].upper()} @ {sig['price']} (conf {conf}) — {checklist}")
        return {"executed": False, "stage": "alert_only", "signal": rec, "risk": decision.to_dict()}

    if mode == ExecutionMode.PAPER:
        pos = get_paper().open(req.symbol, sig["side"], lots, sig["price"], sig["sl"], sig["tp"],
                               conf, checklist, reasoning)
        db = SessionLocal()
        try:
            db.add(PaperTrade(strategy=req.strategy, symbol=req.symbol, side=sig["side"], lots=lots,
                              entry=pos.entry, sl=sig["sl"], tp=sig["tp"], confidence=conf,
                              checklist=checklist, reasoning=reasoning, status="open"))
            db.commit()
        finally:
            db.close()
        rec = journal.log_fill({"mode": "paper", "paper_id": pos.id, "symbol": req.symbol, "side": sig["side"],
                                "lots": lots, "entry": pos.entry, "sl": sig["sl"], "tp": sig["tp"],
                                "confidence": conf, "checklist": checklist, "reasoning": reasoning})
        notifier.send(f"📝 PAPER {req.symbol} {sig['side'].upper()} {lots} @ {pos.entry}")
        return {"executed": True, "stage": "paper", "fill": rec, "risk": decision.to_dict()}

    # LIVE_AUTO — re-verify gate + bridge at execution time (never trust UI state)
    db = SessionLocal()
    try:
        row = db.query(Strategy).filter(Strategy.name == req.strategy).first()
        bt_gate = (row.backtest_gate if row else None)
        from ..backtest_engine.metrics import compute_metrics
        prows = db.query(PaperTrade).filter(PaperTrade.strategy == req.strategy, PaperTrade.status == "closed").all()
        ptrades = [{"pnl": r.pnl or 0.0, "r_multiple": r.r_multiple or 0.0} for r in prows]
        eq = [10_000.0]
        b = 10_000.0
        for t in ptrades:
            b += t["pnl"]
            eq.append(b)
        paper_gate = get_gate().check_paper(compute_metrics(ptrades, eq, None, 10_000.0))
        decision_gate = get_gate().decide(bt_gate, paper_gate)
    finally:
        db.close()
    if not decision_gate["live_auto_allowed"]:
        rec = journal.log_risk_block({"allowed": False, "reasons": decision_gate["reasons"]},
                                     {"symbol": req.symbol, "strategy": req.strategy})
        raise HTTPException(403, {"detail": "Live Auto blocked at execution time", "reasons": decision_gate["reasons"]})

    res = get_executor().send(OrderRequest(req.symbol, sig["side"], lots, sig["sl"], sig["tp"]))
    if not res.ok:
        rec = journal.log_error("live_order", res.detail, {"symbol": req.symbol, "lots": lots})
        notifier.send(f"⛔ LIVE ORDER FAILED {req.symbol}: {res.detail}")
        raise HTTPException(502, {"detail": res.detail, "journal": rec})

    db = SessionLocal()
    try:
        db.add(LiveTrade(strategy=req.strategy, symbol=req.symbol, side=sig["side"], lots=lots,
                         entry=res.fill_price or sig["price"], sl=sig["sl"], tp=sig["tp"],
                         order_id=res.order_id, confidence=conf, checklist=checklist,
                         reasoning=reasoning, status="open"))
        row = db.query(Strategy).filter(Strategy.name == req.strategy).first()
        if row:
            row.live_trades = (row.live_trades or 0) + 1
        db.commit()
    finally:
        db.close()
    rec = journal.log_fill({"mode": "live", "order_id": res.order_id, "symbol": req.symbol, "side": sig["side"],
                            "lots": lots, "entry": res.fill_price, "sl": sig["sl"], "tp": sig["tp"],
                            "confidence": conf, "checklist": checklist})
    notifier.send(f"✅ LIVE {req.symbol} {sig['side'].upper()} {lots} @ {res.fill_price} (#{res.order_id})")
    return {"executed": True, "stage": "live", "fill": rec, "risk": decision.to_dict()}


@router.get("/paper")
def paper_state():
    p = get_paper()
    return {"balance": round(p.balance, 2), "open": len(p.positions),
            "positions": [vars(x) for x in p.positions.values()],
            "closed": p.closed[-50:], "metrics": p.metrics()}


class TickRequest(BaseModel):
    symbol: str = "EURUSD"
    bid: float
    ask: float
    tick_value: float = 1.0
    tick_size: float = 0.01


@router.post("/paper/tick")
def paper_tick(req: TickRequest):
    """Advance paper engine with a tick (called by poller / tests)."""
    closed = get_paper().on_tick(req.symbol, req.bid, req.ask, req.tick_value, req.tick_size)
    rm = get_risk_manager()
    journal = get_journal()
    for c in closed:
        rm.breaker.record_result((c["pnl"] or 0) > 0, trade_id=c["id"])
        journal.log_close({"mode": "paper", **{k: c.get(k) for k in (
            "id", "symbol", "side", "lots", "entry", "exit_price", "sl", "tp",
            "pnl", "r_multiple", "exit_reason", "confidence", "checklist")}})
        db = SessionLocal()
        try:
            row = db.query(PaperTrade).filter(PaperTrade.symbol == req.symbol, PaperTrade.status == "open").first()
            if row:
                row.status = "closed"
                row.exit_price = c["exit_price"]
                row.pnl = c["pnl"]
                row.r_multiple = c["r_multiple"]
                row.exit_reason = c["exit_reason"]
                row.closed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
    return {"closed": closed, "circuit": rm.breaker.status()}
