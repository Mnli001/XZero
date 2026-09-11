from app.execution_modes import ExecutionMode, ModeState, derive_status, gate_decision
from app.execution_modes.gate import evaluate_backtest, evaluate_paper

PASS_BT = {"trade_count": 60, "expectancy_r": 0.4, "max_drawdown_pct": 12.0, "profit_factor": 1.6}
FAIL_BT = {"trade_count": 10, "expectancy_r": -0.2, "max_drawdown_pct": 30.0, "profit_factor": 0.8}
PASS_PP = {"trade_count": 35, "expectancy_r": 0.2}
FAIL_PP = {"trade_count": 5, "expectancy_r": 0.1}


def test_backtest_thresholds():
    assert evaluate_backtest(PASS_BT)["passed"] is True
    bad = evaluate_backtest(FAIL_BT)
    assert bad["passed"] is False
    assert bad["checks"]["trades>=30"] is False


def test_gate_blocks_until_both_pass():
    d = gate_decision(evaluate_backtest(PASS_BT), None)
    assert d["live_auto_allowed"] is False
    d = gate_decision(evaluate_backtest(PASS_BT), evaluate_paper(PASS_PP))
    assert d["live_auto_allowed"] is True
    d = gate_decision(evaluate_backtest(FAIL_BT), evaluate_paper(PASS_PP))
    assert d["live_auto_allowed"] is False


def test_status_badges():
    assert derive_status(None, None) == "Unvalidated"
    assert derive_status(evaluate_backtest(PASS_BT), None) == "Backtested"
    assert derive_status(evaluate_backtest(PASS_BT), evaluate_paper(PASS_PP)) == "Paper-Tested"
    assert derive_status(evaluate_backtest(PASS_BT), evaluate_paper(PASS_PP), 7).startswith("Live-Verified")


def test_mode_transition_requires_gate():
    m = ModeState()
    r = m.request(ExecutionMode.LIVE_AUTO, gate={"live_auto_allowed": False, "reasons": ["no gate"]})
    assert r["ok"] is False
    assert m.mode == ExecutionMode.ALERT_ONLY
    r = m.request(ExecutionMode.PAPER)
    assert r["ok"] is True
