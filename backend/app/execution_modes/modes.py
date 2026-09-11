"""Execution mode state machine: alert_only -> paper -> live_auto."""
from __future__ import annotations

from enum import Enum


class ExecutionMode(str, Enum):
    ALERT_ONLY = "alert_only"
    PAPER = "paper"
    LIVE_AUTO = "live_auto"


class ModeState:
    def __init__(self, mode: ExecutionMode = ExecutionMode.ALERT_ONLY):
        self.mode = mode

    def request(self, target: ExecutionMode, gate: dict | None = None) -> dict:
        """Request a mode change. Live Auto requires a passing gate decision."""
        if target == ExecutionMode.LIVE_AUTO:
            if not gate or not gate.get("live_auto_allowed"):
                reasons = (gate or {}).get("reasons", ["no gate decision supplied"])
                return {"ok": False, "mode": self.mode.value,
                        "detail": "Live Auto refused: " + "; ".join(reasons)}
        self.mode = target
        return {"ok": True, "mode": self.mode.value, "detail": f"mode set to {target.value}"}
