from app.risk_manager import CircuitBreaker, GuardConfig, MarketGuards, PositionSizing, RiskManager


def _mgr(tmp_path, **kw):
    cb = CircuitBreaker(state_path=str(tmp_path / "cb.json"), allow_reset=True)
    guards = MarketGuards(GuardConfig(**kw) if kw else GuardConfig())
    return RiskManager(sizing=PositionSizing(), breaker=cb, guards=guards), cb


def _base():
    return dict(balance=10_000, entry=1.1000, stop_loss=1.0950, tick_value=1.0,
                tick_size=0.0001, risk_pct=1.0, current_spread=1.0,
                recent_spreads=[1.0] * 50)


def test_allows_clean_trade(tmp_path):
    mgr, _ = _mgr(tmp_path)
    d = mgr.evaluate(**_base())
    assert d.allowed is True
    assert d.lots > 0


def test_circuit_lock_blocks_everything(tmp_path):
    mgr, cb = _mgr(tmp_path)
    cb.record_result(False, "a")
    cb.record_result(False, "b")
    d = mgr.evaluate(**_base())
    assert d.allowed is False
    assert any("circuit" in r.lower() for r in d.reasons)


def test_spread_spike_blocks(tmp_path):
    mgr, _ = _mgr(tmp_path)
    kw = _base()
    kw["current_spread"] = 10.0
    d = mgr.evaluate(**kw)
    assert d.allowed is False
    assert any("spread" in r.lower() for r in d.reasons)


def test_daily_loss_limit_blocks(tmp_path):
    mgr, _ = _mgr(tmp_path)
    kw = _base()
    kw["day_pnl"] = -700.0  # -7% of 10k > 6% limit
    d = mgr.evaluate(**kw)
    assert d.allowed is False


def test_exposure_blocks(tmp_path):
    mgr, _ = _mgr(tmp_path)
    kw = _base()
    kw["open_positions"] = 3
    d = mgr.evaluate(**kw)
    assert d.allowed is False


def test_rollover_blocks(tmp_path):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=30)).strftime("%H:%M")
    end = (now + timedelta(minutes=30)).strftime("%H:%M")
    mgr, _ = _mgr(tmp_path, rollover_start_utc=start, rollover_end_utc=end)
    d = mgr.evaluate(**_base())
    assert d.allowed is False
    assert any("rollover" in r.lower() for r in d.reasons)
