"""Risk inspection + pre-trade evaluation (server-side, binding)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..services import get_risk_manager

router = APIRouter(prefix="/risk", tags=["risk"])


class EvaluateRequest(BaseModel):
    balance: float
    entry: float
    stop_loss: float
    tick_value: float = 1.0
    tick_size: float = 0.01
    risk_pct: float | None = None
    day_pnl: float = 0.0
    open_positions: int = 0
    open_risk_pct: float = 0.0
    current_spread: float = 0.0
    recent_spreads: list[float] = []


@router.get("/status")
def status():
    rm = get_risk_manager()
    return {
        "circuit": rm.breaker.status(),
        "caps": {"default_risk_pct": rm.sizing.default_risk_pct,
                 "max_risk_pct": rm.sizing.max_risk_pct,
                 "hard_ceiling": rm.sizing.HARD_MAX_RISK_PCT},
        "guards": {"spread_max_mult": rm.guards.config.spread_max_mult,
                   "daily_loss_limit_pct": rm.guards.config.daily_loss_limit_pct,
                   "max_open_positions": rm.guards.config.max_open_positions,
                   "rollover_blackout_utc": [rm.guards.config.rollover_start_utc, rm.guards.config.rollover_end_utc]},
    }


@router.post("/evaluate")
def evaluate(req: EvaluateRequest):
    return get_risk_manager().evaluate(**req.model_dump()).to_dict()


@router.post("/circuit/reset")
def circuit_reset():
    """Dev/test only — disabled in production (allow_circuit_reset=false)."""
    rm = get_risk_manager()
    try:
        rm.breaker.reset()
    except PermissionError as e:
        raise HTTPException(403, str(e))
    return {"ok": True, "circuit": rm.breaker.status()}
