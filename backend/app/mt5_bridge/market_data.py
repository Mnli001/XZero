"""Candle + tick feed. Live via MT5 terminal; mock via seeded random-walk."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pandas as pd

from .client import MT5Client

TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}


class MarketData:
    def __init__(self, client: MT5Client | None = None):
        self.client = client or MT5Client()
        self._mock_price: dict[str, float] = {}

    def get_candles(self, symbol: str, timeframe: str = "M5", count: int = 300) -> dict:
        """Returns {symbol, timeframe, data_source, candles:[{time,open,high,low,close,spread}]}."""
        tf = timeframe.upper()
        if tf not in TF_MINUTES:
            raise ValueError(f"unsupported timeframe {timeframe}")
        info = self.client.status()
        if info.mode.value == "live" and info.connected and self.client.mt5 is not None:
            return self._live_candles(symbol, tf, count)
        return self._mock_candles(symbol, tf, count)

    # ── live ────────────────────────────────────────────────────
    def _live_candles(self, symbol: str, tf: str, count: int) -> dict:
        mt5 = self.client.mt5
        tf_map = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
                  "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
        rates = mt5.copy_rates_from_pos(symbol, tf_map[tf], 0, count)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"MT5 returned no rates for {symbol} {tf}: {mt5.last_error()}")
        candles = [{
            "time": datetime.fromtimestamp(int(r["time"]), tz=timezone.utc).isoformat(),
            "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]),
            "close": float(r["close"]), "spread": float(r.get("spread", 0)),
            "tick_volume": int(r.get("tick_volume", 0)),
        } for r in rates]
        return {"symbol": symbol, "timeframe": tf, "data_source": "live", "candles": candles}

    # ── mock ────────────────────────────────────────────────────
    def _mock_candles(self, symbol: str, tf: str, count: int) -> dict:
        step = TF_MINUTES[tf]
        rng = random.Random(hash((symbol, tf, datetime.now(timezone.utc).strftime("%Y%m%d"))) & 0xFFFFFFFF)
        base = self._mock_price.get(symbol, 1.0850 if "JPY" not in symbol else 155.0)
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        now -= timedelta(minutes=now.minute % step)
        candles: list[dict] = []
        price = base * (1 + (rng.random() - 0.5) * 0.004)
        vol = base * 0.0004
        # Gentle regime drift so SMC structures actually form in mock data
        drift = 0
        for k in range(count):
            if rng.random() < 0.04:
                drift = rng.choice([-1, 0, 1])
            o = price
            c = o + rng.gauss(drift * vol * 0.6, vol)
            h = max(o, c) + abs(rng.gauss(0, vol * 0.6))
            l = min(o, c) - abs(rng.gauss(0, vol * 0.6))
            t = now - timedelta(minutes=step * (count - 1 - k))
            candles.append({"time": t.isoformat(), "open": o, "high": h, "low": l,
                            "close": c, "spread": round(abs(rng.gauss(1.2, 0.3)), 1), "tick_volume": rng.randint(20, 400)})
            price = c
        self._mock_price[symbol] = price
        return {"symbol": symbol, "timeframe": tf, "data_source": "mock", "candles": candles}

    def to_frame(self, payload: dict) -> pd.DataFrame:
        df = pd.DataFrame(payload["candles"])
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df[["time", "open", "high", "low", "close", "spread"]]

    def tick(self, symbol: str) -> dict:
        info = self.client.status()
        if info.mode.value == "live" and info.connected and self.client.mt5 is not None:
            t = self.client.mt5.symbol_info_tick(symbol)
            if t is None:
                raise RuntimeError(f"MT5 tick failed for {symbol}")
            return {"symbol": symbol, "bid": float(t.bid), "ask": float(t.ask),
                    "time": datetime.fromtimestamp(t.time, tz=timezone.utc).isoformat(), "data_source": "live"}
        px = self._mock_price.get(symbol, 1.0850)
        spread_px = 0.00012
        return {"symbol": symbol, "bid": px, "ask": px + spread_px,
                "time": datetime.now(timezone.utc).isoformat(), "data_source": "mock"}
