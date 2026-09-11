"""Market data + analysis endpoints (read-only, no orders)."""
from fastapi import APIRouter, HTTPException, Query

from ..services import analyze_symbol, ensure_strategy, get_market_data, review_with_ai

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/candles")
def candles(symbol: str = "EURUSD", timeframe: str = "M5", count: int = Query(300, le=1000)):
    try:
        return get_market_data().get_candles(symbol, timeframe, count)
    except Exception as e:
        raise HTTPException(502, f"market data failed: {e}")


@router.get("/tick")
def tick(symbol: str = "EURUSD"):
    try:
        return get_market_data().tick(symbol)
    except Exception as e:
        raise HTTPException(502, f"tick failed: {e}")


@router.get("/analysis")
def analysis(symbol: str = "EURUSD", timeframe: str = "M5", count: int = Query(300, le=1000), ai: bool = False):
    try:
        out = analyze_symbol(symbol, timeframe, count)
    except Exception as e:
        raise HTTPException(502, f"analysis failed: {e}")
    if ai:
        try:
            out["ai_review"] = review_with_ai(out)
        except Exception as e:
            out["ai_review"] = {"verdict": "skip", "confidence": 0, "reasoning": f"AI review failed safely: {e}",
                                "checklist": {}, "referenced_sources": [], "provider": "error", "advisory_only": True}
    strat = ensure_strategy()
    out["strategy"] = {"name": strat["name"], "mode": strat["mode"]}
    return out
