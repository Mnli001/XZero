"""WebSocket live stream: tick + signal snapshot every N seconds."""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services import analyze_symbol, get_market_data, get_risk_manager

router = APIRouter()


@router.websocket("/ws/live")
async def live(ws: WebSocket):
    await ws.accept()
    params = {"symbol": "EURUSD", "timeframe": "M5", "interval": 5}
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=2.0)
        try:
            params.update(json.loads(raw))
        except Exception:
            pass
    except asyncio.TimeoutError:
        pass
    md = get_market_data()
    try:
        while True:
            try:
                tick = md.tick(params["symbol"])
                a = analyze_symbol(params["symbol"], params["timeframe"], 120)
                await ws.send_json({
                    "type": "snapshot", "tick": tick,
                    "price": a["price"], "data_source": a["data_source"],
                    "signal": a["signal"], "confluence": a.get("confluence"),
                    "smc": {"bias": a["smc"]["bias"], "checklist": a["smc"]["checklist"],
                            "valuation": (a["smc"].get("valuation") or {}).get("zone")},
                    "circuit": get_risk_manager().breaker.status(),
                })
            except Exception as e:
                await ws.send_json({"type": "error", "detail": str(e)})
            await asyncio.sleep(max(2, min(int(params.get("interval", 5)), 60)))
    except WebSocketDisconnect:
        pass
