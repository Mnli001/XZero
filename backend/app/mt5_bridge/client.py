"""MT5 connection wrapper with explicit mock fallback.

Never pretends to be connected: `mode` is always reported and every consumer
(displays, journal) must show it. Errors (disconnect, reject, requote) are
returned as structured failures — never silent fake success (§6).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class MT5Mode(str, Enum):
    LIVE = "live"      # Windows + MetaTrader5 package + logged-in terminal
    MOCK = "mock"      # Linux/dev: simulated feed, paper + alerts only
    OFFLINE = "offline"  # explicitly disabled


@dataclass
class ConnectionInfo:
    mode: MT5Mode
    connected: bool
    server: str = ""
    login: str = ""
    detail: str = ""


class MT5Client:
    def __init__(self, mode: str | None = None):
        env_mode = (mode or os.getenv("MT5_MODE", "mock")).lower()
        self._mt5 = None
        self._info = ConnectionInfo(MT5Mode.MOCK, False)
        if env_mode == "off":
            self._info = ConnectionInfo(MT5Mode.OFFLINE, False, detail="MT5 disabled by MT5_MODE=off")
            return
        try:
            import MetaTrader5 as mt5  # noqa: F401  (Windows only)
            self._mt5 = mt5
            self._want_live = True
        except ImportError:
            self._want_live = False
            self._info = ConnectionInfo(
                MT5Mode.MOCK, False,
                detail="MetaTrader5 package unavailable (non-Windows) — mock feed active",
            )

    @property
    def mt5(self):
        return self._mt5

    def connect(self) -> ConnectionInfo:
        if self._info.mode == MT5Mode.OFFLINE:
            return self._info
        if not self._want_live or self._mt5 is None:
            self._info = ConnectionInfo(MT5Mode.MOCK, True, detail="mock feed connected (no real market data)")
            return self._info
        ok = self._mt5.initialize(
            path=os.getenv("MT5_PATH") or None,
            login=int(os.getenv("MT5_LOGIN", "0") or 0) or None,
            password=os.getenv("MT5_PASSWORD") or None,
            server=os.getenv("MT5_SERVER") or None,
            timeout=int(os.getenv("MT5_TIMEOUT_MS", "60000")),
        )
        if not ok:
            err = self._mt5.last_error()
            self._info = ConnectionInfo(MT5Mode.LIVE, False, detail=f"MT5 initialize failed: {err}")
            return self._info
        acct = self._mt5.account_info()
        self._info = ConnectionInfo(
            MT5Mode.LIVE, True,
            server=os.getenv("MT5_SERVER", ""), login=str(getattr(acct, "login", "")),
            detail=f"connected: balance={getattr(acct, 'balance', '?')} {getattr(acct, 'currency', '')}",
        )
        return self._info

    def status(self) -> ConnectionInfo:
        return self._info

    def shutdown(self) -> None:
        try:
            if self._mt5 is not None:
                self._mt5.shutdown()
        except Exception:
            pass
