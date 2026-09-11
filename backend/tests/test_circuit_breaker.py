import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from app.risk_manager import CircuitBreaker


def test_two_losses_lock_24h(tmp_path):
    cb = CircuitBreaker(state_path=str(tmp_path / "cb.json"), allow_reset=True)
    cb.record_result(False, "t1")
    assert cb.is_locked()[0] is False
    out = cb.record_result(False, "t2")
    assert out["tripped_now"] is True
    locked, until = cb.is_locked()
    assert locked is True
    remaining = cb.time_remaining()
    assert remaining is not None and remaining > timedelta(hours=23)


def test_win_resets_counter(tmp_path):
    cb = CircuitBreaker(state_path=str(tmp_path / "cb.json"), allow_reset=True)
    cb.record_result(False, "t1")
    cb.record_result(True, "t2")
    assert cb.status()["consecutive_losses"] == 0
    assert cb.is_locked()[0] is False


def test_lock_survives_restart(tmp_path):
    p = str(tmp_path / "cb.json")
    cb = CircuitBreaker(state_path=p, allow_reset=True)
    cb.record_result(False, "t1")
    cb.record_result(False, "t2")
    cb2 = CircuitBreaker(state_path=p, allow_reset=True)
    assert cb2.is_locked()[0] is True


def test_lock_expires_by_time(tmp_path):
    p = str(tmp_path / "cb.json")
    cb = CircuitBreaker(state_path=p, allow_reset=True)
    cb.record_result(False, "t1")
    cb.record_result(False, "t2")
    # force expiry
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["locked_until"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f)
    cb2 = CircuitBreaker(state_path=p, allow_reset=True)
    assert cb2.is_locked()[0] is False


def test_reset_disabled_in_production_mode(tmp_path):
    cb = CircuitBreaker(state_path=str(tmp_path / "cb.json"), allow_reset=False)
    cb.record_result(False, "t1")
    cb.record_result(False, "t2")
    with pytest.raises(PermissionError):
        cb.reset()
    assert cb.is_locked()[0] is True
