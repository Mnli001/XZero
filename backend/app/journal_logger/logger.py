"""Append-only JSONL journal. Records entries, exits, skips and system errors.

Each record keeps: entry/exit reason, confidence, checklist snapshot, P&L.
'SYSTEM_ERROR' records guarantee failures are never shown as silent success.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


class JournalLogger:
    def __init__(self, path: str = "./data/journal.jsonl"):
        self.path = path
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)

    def _append(self, rec: dict[str, Any]) -> dict[str, Any]:
        rec.setdefault("journaled_at", datetime.now(timezone.utc).isoformat())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        return rec

    def log_signal(self, signal: dict[str, Any]) -> dict:
        return self._append({"kind": "SIGNAL", **signal})

    def log_skip(self, reason: str, context: dict[str, Any]) -> dict:
        return self._append({"kind": "SKIP", "reason": reason, **context})

    def log_fill(self, fill: dict[str, Any]) -> dict:
        return self._append({"kind": "FILL", **fill})

    def log_close(self, close: dict[str, Any]) -> dict:
        return self._append({"kind": "CLOSE", **close})

    def log_risk_block(self, decision: dict[str, Any], context: dict[str, Any]) -> dict:
        return self._append({"kind": "RISK_BLOCK", "decision": decision, **context})

    def log_error(self, where: str, error: str, context: dict[str, Any] | None = None) -> dict:
        return self._append({"kind": "SYSTEM_ERROR", "where": where, "error": error, "context": context or {}})

    def read(self, kind: str | None = None, limit: int = 500) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        rows: list[dict] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if kind:
            rows = [r for r in rows if r.get("kind") == kind]
        return rows[-limit:]
