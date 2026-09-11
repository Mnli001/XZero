"""AI reasoning layer — advisory ONLY (§3.4).

The LLM reviews signal candidates against the curated knowledge base and
returns a structured verdict. It NEVER executes: the final decision always
passes through RiskManager + the execution gate (defense against hallucination).
Knowledge sources are read-only references — the system never downloads or
executes code from them (§2.7).
"""
from .rag_store import KnowledgeBase, KnowledgeSource
from .reasoner import AIReasoner, ReasonRequest
from .schemas import AI_Verdict

__all__ = ["KnowledgeBase", "KnowledgeSource", "AIReasoner", "ReasonRequest", "AI_Verdict"]
