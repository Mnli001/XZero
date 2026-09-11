"""Curated knowledge base (§2.7) — read-only references for AI reasoning."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import get_kb

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class SourceIn(BaseModel):
    title: str
    kind: str = "note"
    content: str
    uri: str = ""
    tags: list[str] = []


@router.get("")
def list_sources():
    kb = get_kb()
    return {"count": len(kb.list()), "sources": [vars(s) for s in kb.list()],
            "policy": "read-only reference: sources inform AI reasoning, code is never imported or executed from them (§2.7)"}


@router.post("")
def add_source(src: SourceIn):
    if len(src.content) < 20:
        raise HTTPException(400, "content too short — add a meaningful excerpt or note")
    s = get_kb().add(src.title, src.kind, src.content, src.uri, src.tags)
    return {"ok": True, "source": vars(s)}


@router.delete("/{source_id}")
def delete_source(source_id: str):
    if not get_kb().remove(source_id):
        raise HTTPException(404, "source not found")
    return {"ok": True}


@router.get("/search")
def search(q: str, top_k: int = 3):
    return {"query": q, "results": get_kb().search(q, top_k)}
