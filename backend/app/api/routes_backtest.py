"""Backtest runs + reports. Results feed the Backtest Gate (§2.1)."""
import glob
import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..backtest_engine import BacktestRunner, SimParams, StrategyParams
from ..config import settings
from ..database import SessionLocal
from ..models import Strategy
from ..services import ensure_strategy, get_gate

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    csv_path: str
    symbol: str = "EURUSD"
    timeframe: str = "M5"
    strategy: str = "smc_fvg_retest_v1"
    strategy_params: dict | None = None
    risk_pct: float = 1.0
    spread: float = 0.0
    slippage: float = 0.0
    n_splits: int = 3


@router.post("/run")
def run_backtest(req: BacktestRequest):
    if not os.path.exists(req.csv_path):
        raise HTTPException(404, f"csv not found: {req.csv_path}")
    sp = StrategyParams.from_dict(req.strategy_params or {})
    sim = SimParams(initial_balance=10_000.0, risk_pct=req.risk_pct, spread=req.spread,
                    slippage=req.slippage, use_csv_spread=True)
    try:
        report = BacktestRunner(settings.reports_dir).run(
            req.csv_path, timeframe=req.timeframe, strategy_params=sp, sim_params=sim,
            n_splits=req.n_splits, symbol=req.symbol)
    except Exception as e:
        raise HTTPException(500, f"backtest failed: {e}")

    gate_eval = get_gate().check_backtest(report["oos_overall"])

    # Persist gate state to the strategy row
    ensure_strategy(req.strategy, req.symbol, req.timeframe)
    db = SessionLocal()
    try:
        row = db.query(Strategy).filter(Strategy.name == req.strategy).first()
        row.backtest_report_id = report["report_id"]
        row.backtest_gate = gate_eval
        row.params = sp.to_dict()
        db.commit()
    finally:
        db.close()

    report["gate"] = gate_eval
    return report


@router.get("/reports")
def list_reports():
    files = sorted(glob.glob(os.path.join(settings.reports_dir, "*.json")), reverse=True)[:50]
    out = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                r = json.load(fh)
            out.append({"report_id": r.get("report_id"), "created_at": r.get("created_at"),
                        "symbol": r.get("symbol"), "timeframe": r.get("timeframe"),
                        "oos_overall": r.get("oos_overall"), "data_quality": r.get("data_quality")})
        except Exception:
            continue
    return {"reports": out, "note": "stats come only from real backtest runs (§2.3) — no demo numbers"}


@router.get("/reports/{report_id}")
def get_report(report_id: str):
    path = os.path.join(settings.reports_dir, f"{report_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "report not found")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
