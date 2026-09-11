"""Order execution. Mock mode REFUSES live orders (paper/alerts only)."""
from __future__ import annotations

from dataclasses import dataclass

from .client import MT5Client


@dataclass
class OrderRequest:
    symbol: str
    side: str  # "buy" | "sell"
    lots: float
    sl: float = 0.0
    tp: float = 0.0
    magic: int = 20260911
    comment: str = "xzero"


@dataclass
class OrderResult:
    ok: bool
    order_id: str | None = None
    fill_price: float | None = None
    detail: str = ""
    data_source: str = "mock"


class OrderExecutor:
    def __init__(self, client: MT5Client | None = None):
        self.client = client or MT5Client()

    def send(self, req: OrderRequest) -> OrderResult:
        info = self.client.status()
        if info.mode.value != "live" or not info.connected or self.client.mt5 is None:
            return OrderResult(False, detail=f"order refused: bridge is in {info.mode.value} mode — live orders need the Windows VPS bridge", data_source=info.mode.value)
        mt5 = self.client.mt5
        sym = mt5.symbol_info(req.symbol)
        if sym is None:
            return OrderResult(False, detail=f"unknown symbol {req.symbol}", data_source="live")
        tick = mt5.symbol_info_tick(req.symbol)
        price = tick.ask if req.side == "buy" else tick.bid
        order = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": req.symbol, "volume": req.lots,
            "type": mt5.ORDER_TYPE_BUY if req.side == "buy" else mt5.ORDER_TYPE_SELL,
            "price": price, "sl": req.sl, "tp": req.tp, "magic": req.magic,
            "comment": req.comment, "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(order)
        if res is None:
            return OrderResult(False, detail=f"order_send returned None: {mt5.last_error()}", data_source="live")
        if res.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(False, detail=f"broker rejected: retcode={res.retcode} comment={res.comment}", data_source="live")
        return OrderResult(True, order_id=str(res.order), fill_price=float(res.price), detail="filled", data_source="live")
