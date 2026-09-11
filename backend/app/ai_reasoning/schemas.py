"""Structured verdict schema shared by the LLM and fallback reasoners."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AI_Verdict(BaseModel):
    verdict: str = Field(pattern="^(enter|skip)$")
    confidence: float = Field(ge=0, le=100)
    reasoning: str
    checklist: dict[str, bool] = Field(default_factory=dict)
    referenced_sources: list[str] = Field(default_factory=list)
    provider: str = "fallback"
    advisory_only: bool = True
