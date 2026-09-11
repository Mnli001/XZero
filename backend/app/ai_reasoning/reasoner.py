"""AIReasoner: Claude (via Anthropic API) with deterministic fallback.

No API key -> rule-based fallback producing the SAME schema, labeled
provider='fallback'. Either way the output is advisory-only JSON.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .rag_store import KnowledgeBase
from .schemas import AI_Verdict


@dataclass
class ReasonRequest:
    symbol: str
    timeframe: str
    side: str
    price: float
    sl: float
    tp: float
    smc_checklist: dict[str, bool]
    confluence_score: float
    bias: str
    extra: dict[str, Any] | None = None


class AIReasoner:
    def __init__(self, kb: KnowledgeBase | None = None, api_key: str | None = None,
                 model: str | None = None, timeout_s: float = 30.0):
        self.kb = kb or KnowledgeBase()
        self.api_key = api_key if api_key is not None else os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        self.timeout_s = timeout_s

    # ── public ──────────────────────────────────────────────────
    def review(self, req: ReasonRequest) -> AI_Verdict:
        candidate = {
            "symbol": req.symbol, "timeframe": req.timeframe, "side": req.side,
            "price": req.price, "sl": req.sl, "tp": req.tp, "bias": req.bias,
            "checklist": req.smc_checklist, "confluence_score": req.confluence_score,
            "extra": req.extra or {},
        }
        query = f"{req.symbol} {req.side} sweep choch fvg premium discount retest {req.bias}"
        sources = self.kb.search(query, top_k=3)
        if self.api_key:
            try:
                return self._call_claude(candidate, sources)
            except Exception as e:  # LLM failure must degrade to fallback, never to "enter"
                fb = self._fallback(req, sources)
                fb.reasoning += f" [LLM unavailable, fallback used: {e}]"
                return fb
        return self._fallback(req, sources)

    # ── Claude path ─────────────────────────────────────────────
    def _call_claude(self, candidate: dict, sources: list[dict]) -> AI_Verdict:
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        body = {
            "model": self.model, "max_tokens": 800, "temperature": 0.2,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": build_user_prompt(candidate, sources)}],
        }
        with httpx.Client(timeout=self.timeout_s) as client:
            r = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
        obj = json.loads(text)
        obj["provider"] = f"claude:{self.model}"
        obj["advisory_only"] = True
        # Safety: only known source ids survive (anti-hallucination).
        known = {s["id"] for s in sources}
        obj["referenced_sources"] = [i for i in obj.get("referenced_sources", []) if i in known]
        return AI_Verdict(**obj)

    # ── deterministic fallback ──────────────────────────────────
    def _fallback(self, req: ReasonRequest, sources: list[dict]) -> AI_Verdict:
        ch = req.smc_checklist
        keys = ["sweep", "choch", "fvg", "valuation", "retest"]
        # map analyzer names -> verdict names
        mapped = {
            "sweep": bool(ch.get("sweep")),
            "choch": bool(ch.get("choch") or ch.get("structure_break")),
            "fvg": bool(ch.get("fvg")),
            "valuation": bool(ch.get("valuation")),
            "retest": bool(ch.get("retest")),
        }
        passed = sum(1 for k in keys if mapped[k])
        score = req.confluence_score
        if passed >= 4 and score >= 60:
            verdict, conf = "enter", min(score, 90.0)
            why = f"{passed}/5 rules passed with confluence {score:.0f} — setup qualifies for RISK-MANAGED review (advisory only)."
        else:
            verdict, conf = "skip", max(10.0, score * passed / 5)
            missing = [k for k in keys if not mapped[k]]
            why = f"Skipped: only {passed}/5 rules passed (missing: {', '.join(missing) or 'none'}), confluence {score:.0f}."
        return AI_Verdict(
            verdict=verdict, confidence=round(conf, 1), reasoning=why,
            checklist=mapped, referenced_sources=[s["id"] for s in sources[:2]],
            provider="fallback", advisory_only=True,
        )
