"""Telegram alerts. Failures are logged, never raised (alerting must not crash trading)."""
from __future__ import annotations

import os

import httpx


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token if token is not None else os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id if chat_id is not None else os.getenv("TELEGRAM_CHAT_ID", "")

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> dict:
        if not self.enabled:
            return {"ok": False, "detail": "telegram not configured"}
        try:
            with httpx.Client(timeout=10) as c:
                r = c.post(f"https://api.telegram.org/bot{self.token}/sendMessage",
                           json={"chat_id": self.chat_id, "text": text[:4000]})
                r.raise_for_status()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "detail": f"telegram send failed: {e}"}
