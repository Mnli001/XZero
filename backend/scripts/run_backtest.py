"""CLI: python scripts/run_backtest.py <csv> [SYMBOL] [TIMEFRAME]

Runs the reference SMC strategy with walk-forward OOS evaluation and prints
the gate verdict. Exit code 0 = gate passed, 2 = gate failed (still prints).
"""
import json
import sys

sys.path.insert(0, ".")

from app.backtest_engine import BacktestRunner, SimParams, StrategyParams  # noqa: E402
from app.execution_modes import Gate  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    csv, symbol, tf = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "EURUSD", sys.argv[3] if len(sys.argv) > 3 else "M5"
    rep = BacktestRunner().run(csv, timeframe=tf, strategy_params=StrategyParams(),
                               sim_params=SimParams(), n_splits=3, symbol=symbol)
    gate = Gate().check_backtest(rep["oos_overall"])
    print(json.dumps({"report_id": rep["report_id"], "oos": rep["oos_overall"],
                      "data_quality": rep["data_quality"], "gate": gate}, indent=2))
    sys.exit(0 if gate["passed"] else 2)


if __name__ == "__main__":
    main()
