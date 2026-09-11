"""BacktestRunner — full run: load -> splits -> simulate -> metrics -> verdict."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from .data_loader import load_csv
from .metrics import compute_metrics
from .simulator import Simulator, SimParams
from .strategy import SMCStrategy, StrategyParams
from .walkforward import walk_forward_splits


class BacktestRunner:
    def __init__(self, reports_dir: str = "./data/reports"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)

    def run(
        self,
        csv_path: str,
        timeframe: str = "M5",
        strategy_params: StrategyParams | None = None,
        sim_params: SimParams | None = None,
        n_splits: int = 3,
        symbol: str = "UNKNOWN",
        save: bool = True,
    ) -> dict[str, Any]:
        t0 = datetime.now(timezone.utc)
        df, issues = load_csv(csv_path, timeframe)
        strategy = SMCStrategy(strategy_params or StrategyParams())
        sim = Simulator(sim_params or SimParams())

        splits = walk_forward_splits(len(df), n_splits=n_splits)
        folds: list[dict] = []
        oos_trades: list[dict] = []
        for s in splits:
            tr0, tr1 = s["train"]
            te0, te1 = s["test"]
            test_res = sim.run(df, strategy, start=te0, end=te1)
            m = compute_metrics(test_res["trades"], test_res["equity"], test_res["equity_times"],
                                initial_balance=sim.params.initial_balance)
            folds.append({"name": s["name"], "train_bars": [tr0, tr1], "test_bars": [te0, te1], "metrics": m,
                          "equity": test_res["equity"], "equity_times": test_res["equity_times"]})
            oos_trades.extend(test_res["trades"])

        # Aggregate OOS equity (concatenated; per-fold equity preserved above)
        agg_equity = [sim.params.initial_balance]
        bal = sim.params.initial_balance
        for t in sorted(oos_trades, key=lambda x: x["exit_time"]):
            bal += t["pnl"]
            agg_equity.append(bal)
        overall = compute_metrics(oos_trades, agg_equity, None, sim.params.initial_balance)

        gaps = [i for i in issues if i.kind == "gap"]
        weekends = [i for i in issues if i.kind == "weekend"]
        report = {
            "report_id": hashlib.sha256(f"{csv_path}{t0.isoformat()}".encode()).hexdigest()[:12],
            "created_at": t0.isoformat(),
            "symbol": symbol, "timeframe": timeframe, "csv_path": csv_path,
            "bars": len(df), "range": [str(df['time'].iloc[0]), str(df['time'].iloc[-1])],
            "data_quality": {
                "issues": [{"kind": i.kind, "at": i.at_time, "detail": i.detail} for i in issues[:50]],
                "issue_count": len(issues), "gap_count": len(gaps),
                "weekend_closures": len(weekends),
                "status": "incomplete_data" if gaps else "ok",
            },
            "strategy": {"name": strategy.name, "params": (strategy_params or StrategyParams()).to_dict()},
            "simulation": {"initial_balance": sim.params.initial_balance, "risk_pct": sim.params.risk_pct,
                           "spread": sim.params.spread, "use_csv_spread": sim.params.use_csv_spread,
                           "slippage": sim.params.slippage},
            "folds": folds,
            "oos_overall": overall,
            "trades": oos_trades[-500:],
        }
        if save:
            path = os.path.join(self.reports_dir, f"{report['report_id']}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            report["saved_to"] = path
        return report


def run_backtest(csv_path: str, **kwargs) -> dict[str, Any]:
    return BacktestRunner().run(csv_path, **kwargs)
