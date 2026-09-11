import numpy as np
import pandas as pd

from app.backtest_engine import BacktestRunner, StrategyParams, compute_metrics, load_csv


def _write_csv(path, n=2500, seed=11):
    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2023-01-02", tz="UTC")  # a Monday
    rows = []
    p = 1.0850
    drift = 0.0
    t = base
    for i in range(n):
        # skip weekends to reduce artificial gaps
        while t.weekday() >= 5:
            t += pd.Timedelta(minutes=5)
        if rng.random() < 0.02:
            drift = rng.choice([-1.0, 0.0, 1.0]) * 0.00008
        o = p
        c = o + drift + rng.normal(0, 0.0006)
        h = max(o, c) + abs(rng.normal(0, 0.0003))
        l = min(o, c) - abs(rng.normal(0, 0.0003))
        rows.append((t.isoformat(), o, h, l, c, 0.00012))
        p = c
        t += pd.Timedelta(minutes=5)
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "spread"])
    df.to_csv(path, index=False)
    return path


def test_loader_flags_gaps(tmp_path):
    p = _write_csv(str(tmp_path / "d.csv"), n=500)
    df, issues = load_csv(p, "M5")
    assert len(df) > 400
    assert isinstance(issues, list)


def test_loader_rejects_bad_csv(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("foo,bar\n1,2\n")
    try:
        load_csv(str(p))
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_full_run_structure(tmp_path):
    p = _write_csv(str(tmp_path / "d.csv"), n=2500)
    rep = BacktestRunner(str(tmp_path / "reports")).run(
        p, timeframe="M5", strategy_params=StrategyParams(min_confluence=40.0),
        n_splits=2, symbol="EURUSD")
    assert rep["bars"] > 2000
    assert "folds" in rep and len(rep["folds"]) >= 1
    oos = rep["oos_overall"]
    for k in ["trade_count", "win_rate", "expectancy_r", "max_drawdown_pct", "sharpe"]:
        assert k in oos
    assert rep["data_quality"]["status"] in ("ok", "incomplete_data")


def test_metrics_empty_safe():
    m = compute_metrics([], [10_000.0], None, 10_000.0)
    assert m["trade_count"] == 0
    assert m["win_rate"] is None
