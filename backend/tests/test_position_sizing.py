import pytest

from app.risk_manager import PositionSizing


def test_basic_math():
    s = PositionSizing()
    r = s.calculate(balance=10_000, entry=1.1000, stop_loss=1.0950,
                    tick_value=1.0, tick_size=0.0001, risk_pct=2.0)
    # risk $200; stop = 50 ticks * $1 = $50/lot -> 4.0 lots
    assert r.lots == pytest.approx(4.0)
    assert r.risk_amount == pytest.approx(200.0)
    assert r.clamped is False


def test_hard_cap_clamps_server_side():
    s = PositionSizing()
    r = s.calculate(balance=10_000, entry=1.1000, stop_loss=1.0950,
                    tick_value=1.0, tick_size=0.0001, risk_pct=50.0)
    assert r.risk_pct_applied == 5.0
    assert r.clamped is True
    assert r.lots == pytest.approx(10.0)  # $500 / $50


def test_constructor_rejects_above_ceiling():
    with pytest.raises(ValueError):
        PositionSizing(max_risk_pct=10.0)


def test_zero_stop_rejected():
    s = PositionSizing()
    with pytest.raises(ValueError):
        s.calculate(balance=10_000, entry=1.1, stop_loss=1.1, tick_value=1.0, tick_size=0.0001)


def test_too_small_returns_zero_lots():
    s = PositionSizing()
    r = s.calculate(balance=100, entry=1.1000, stop_loss=1.0000,
                    tick_value=1.0, tick_size=0.0001, risk_pct=1.0, volume_min=0.01)
    assert r.lots == 0.0
