from fastapi import APIRouter

from .. import __version__
from ..services import get_mt5_client, get_risk_manager

router = APIRouter()


@router.get("/health")
def health():
    mt5 = get_mt5_client().status()
    return {
        "ok": True, "app": "project-zero", "version": __version__,
        "mt5_mode": mt5.mode.value, "mt5_connected": mt5.connected, "mt5_detail": mt5.detail,
        "circuit": get_risk_manager().breaker.status(),
    }
