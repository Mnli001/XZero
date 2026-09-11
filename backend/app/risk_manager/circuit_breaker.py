"""Circuit breaker (§2.5): 2 consecutive losses -> 24h trading lock.

Backend-owned, UI-independent. State is persisted to disk so a restart cannot
clear a lock. There is NO API unlock — the lock expires by time only. A reset()
exists purely for unit tests / local dev and must be disabled in production
via allow_reset=False.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone


@dataclass
class CircuitState:
    consecutive_losses: int = 0
    locked_until: str | None = None  # ISO timestamp or None
    total_trips: int = 0
    last_result: str | None = None  # "win" | "loss" | None
    last_updated: str | None = None


class CircuitBreaker:
    def __init__(
        self,
        state_path: str = "./data/circuit_breaker.json",
        max_consecutive_losses: int = 2,
        lock_hours: int = 24,
        allow_reset: bool = False,
    ):
        self.state_path = state_path
        self.max_consecutive_losses = max_consecutive_losses
        self.lock_hours = lock_hours
        self.allow_reset = allow_reset
        self._state = self._load()

    # ── persistence ──────────────────────────────────────────────
    def _load(self) -> CircuitState:
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return CircuitState(**{k: data.get(k, getattr(CircuitState, k, None)) for k in CircuitState.__dataclass_fields__})
        except Exception:
            pass
        return CircuitState()

    def _save(self) -> None:
        d = os.path.dirname(self.state_path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(self._state), f, indent=2)
        os.replace(tmp, self.state_path)

    # ── core logic ───────────────────────────────────────────────
    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def is_locked(self) -> tuple[bool, str | None]:
        """Returns (locked, locked_until_iso). Auto-expires stale locks."""
        lu = self._state.locked_until
        if not lu:
            return False, None
        try:
            until = datetime.fromisoformat(lu)
        except ValueError:
            return False, None
        if self._now() >= until:
            self._state.locked_until = None
            self._state.consecutive_losses = 0
            self._save()
            return False, None
        return True, lu

    def time_remaining(self) -> timedelta | None:
        locked, lu = self.is_locked()
        if not locked or not lu:
            return None
        return datetime.fromisoformat(lu) - self._now()

    def record_result(self, won: bool, trade_id: str | None = None) -> dict:
        """Record a closed-trade outcome. Returns the new breaker status."""
        self._state.last_result = "win" if won else "loss"
        self._state.last_updated = self._now().isoformat()
        tripped = False
        if won:
            self._state.consecutive_losses = 0
        else:
            self._state.consecutive_losses += 1
            if self._state.consecutive_losses >= self.max_consecutive_losses:
                until = self._now() + timedelta(hours=self.lock_hours)
                self._state.locked_until = until.isoformat()
                self._state.total_trips += 1
                tripped = True
        self._save()
        locked, lu = self.is_locked()
        return {
            "trade_id": trade_id,
            "won": won,
            "consecutive_losses": self._state.consecutive_losses,
            "locked": locked,
            "locked_until": lu,
            "tripped_now": tripped,
        }

    def status(self) -> dict:
        locked, lu = self.is_locked()
        remaining = self.time_remaining()
        return {
            "locked": locked,
            "locked_until": lu,
            "remaining_seconds": int(remaining.total_seconds()) if remaining else 0,
            "consecutive_losses": self._state.consecutive_losses,
            "max_consecutive_losses": self.max_consecutive_losses,
            "lock_hours": self.lock_hours,
            "total_trips": self._state.total_trips,
            "last_result": self._state.last_result,
        }

    def reset(self) -> None:
        """Dev/test only. Raises unless allow_reset=True."""
        if not self.allow_reset:
            raise PermissionError("Circuit breaker reset is disabled (production safety). It expires by time only.")
        self._state = CircuitState()
        self._save()
