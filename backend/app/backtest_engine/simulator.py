"""Bar-by-bar trade simulator with spread + slippage costs.

Conservative intrabar handling: if both SL and TP are touched within one bar,
the SL is assumed to fill first. Costs: half-spread on entry + half-spread on
exit + fixed slippage (all in price units, configurable per run).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class SimParams:
    initial_balance: float = 10_000.0
    risk_pct: float = 1.0
    spread: float = 0.0        # full spread in price units (static fallback)
    use_csv_spread: bool = True
    slippage: float = 0.0      # per-side slippage in price units
    tick_value: float = 1.0    # account-currency value of one tick per 1.0 lot
    tick_size: float = 0.01
    volume_min: float = 0.01
    volume_step: float = 0.01


class Simulator:
    def __init__(self, params: SimParams | None = None):
        self.params = params or SimParams()

    def _lots(self, balance: float, risk_dist: float) -> float:
        p = self.params
        risk_amount = balance * p.risk_pct / 100.0
        ticks = risk_dist / p.tick_size
        loss_per_lot = ticks * p.tick_value
        if loss_per_lot <= 0:
            return 0.0
        lots = risk_amount / loss_per_lot
        lots = int(lots / p.volume_step + 1e-9) * p.volume_step
        return round(lots, 8) if lots >= p.volume_min else 0.0

    def run(self, df: pd.DataFrame, strategy, start: int = 0, end: int | None = None) -> dict[str, Any]:
        p = self.params
        n = len(df)
        end = n - 1 if end is None else min(end, n - 1)
        prepared = strategy.prepare(df)
        if hasattr(strategy, "bind"):
            strategy.bind(prepared)  # one-shot O(n) structure precompute (repaint-safe)
        balance = p.initial_balance
        equity = [balance]
        equity_times = [str(df["time"].iloc[start])]
        trades: list[dict] = []
        position: dict | None = None
        skipped_no_volume = 0

        for i in range(start, end + 1):
            bar_time = str(df["time"].iloc[i])
            spread = float(df["spread"].iloc[i]) if (p.use_csv_spread and "spread" in df.columns) else p.spread

            # 1. Manage open position against this bar's range
            if position is not None:
                high = float(df["high"].iloc[i])
                low = float(df["low"].iloc[i])
                side = position["side"]
                exit_price = None
                exit_reason = ""
                if side == "buy":
                    sl_hit = low <= position["sl"]
                    tp_hit = high >= position["tp"]
                    if sl_hit:  # conservative: SL first
                        exit_price, exit_reason = position["sl"], "sl"
                    elif tp_hit:
                        exit_price, exit_reason = position["tp"], "tp"
                else:
                    sl_hit = high >= position["sl"]
                    tp_hit = low <= position["tp"]
                    if sl_hit:
                        exit_price, exit_reason = position["sl"], "sl"
                    elif tp_hit:
                        exit_price, exit_reason = position["tp"], "tp"
                if position["bars_held"] + 1 >= position["max_hold"] and exit_price is None:
                    exit_price, exit_reason = float(df["close"].iloc[i]), "max_hold"
                if exit_price is not None:
                    lots = position["lots"]
                    gross = (exit_price - position["entry"]) * (1 if side == "buy" else -1) / p.tick_size * p.tick_value * lots
                    costs = (spread + 2 * p.slippage) / p.tick_size * p.tick_value * lots
                    pnl = gross - costs
                    r_mult = (exit_price - position["entry"]) * (1 if side == "buy" else -1) / position["risk_dist"] if position["risk_dist"] > 0 else 0.0
                    balance += pnl
                    trades.append({
                        **position, "exit_price": exit_price, "exit_time": bar_time,
                        "exit_reason": exit_reason, "pnl": round(pnl, 2),
                        "r_multiple": round(r_mult, 3), "costs": round(costs, 2),
                    })
                    position = None
                else:
                    position["bars_held"] += 1

            # 2. Entry signal at close of this bar (fills next bar open)
            if position is None and i + 1 <= end:
                sig = strategy.signal(prepared, i)
                if sig.get("action") == "enter":
                    lots = self._lots(balance, sig["risk_dist"])
                    if lots <= 0:
                        skipped_no_volume += 1
                    else:
                        nxt_open = float(df["open"].iloc[i + 1])
                        side = sig["side"]
                        # pay half-spread + slippage on entry
                        entry = nxt_open + (spread / 2 + p.slippage) * (1 if side == "buy" else -1)
                        position = {
                            "trade_no": len(trades) + 1, "side": side, "lots": lots,
                            "entry": entry, "sl": sig["sl"], "tp": sig["tp"],
                            "entry_time": str(df["time"].iloc[i + 1]),
                            "signal_time": bar_time, "risk_dist": sig["risk_dist"],
                            "confidence": sig.get("confluence", {}).get("score"),
                            "explanation": sig.get("explanation"),
                            "bars_held": 0, "max_hold": strategy.params.max_hold_bars,
                        }

            equity.append(balance if position is None else balance)  # closed-trade equity
            equity_times.append(bar_time)

        if position is not None:
            # Force-close at last close so open risk never leaks out of the report
            last_close = float(df["close"].iloc[end])
            lots = position["lots"]
            side = position["side"]
            gross = (last_close - position["entry"]) * (1 if side == "buy" else -1) / p.tick_size * p.tick_value * lots
            pnl = gross
            balance += pnl
            trades.append({**position, "exit_price": last_close, "exit_time": str(df["time"].iloc[end]),
                           "exit_reason": "end_of_data", "pnl": round(pnl, 2), "r_multiple": 0.0, "costs": 0.0})
            equity.append(balance)
            equity_times.append(str(df["time"].iloc[end]))

        return {
            "trades": trades, "equity": equity, "equity_times": equity_times,
            "final_balance": round(balance, 2), "skipped_no_volume": skipped_no_volume,
        }
