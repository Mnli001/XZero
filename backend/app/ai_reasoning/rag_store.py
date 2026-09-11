"""Curated knowledge base (§2.7): read-only reference store + TF-IDF retrieval.

Sources are added MANUALLY by the operator (GitHub repo note, PDF summary,
research excerpt). Content is stored as text for retrieval only — never
imported or executed. Retrieval is a dependency-free TF-IDF cosine search so
the backend runs without a vector DB; swap `search()` for pgvector later.
"""
from __future__ import annotations

import json
import math
import os
import re
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class KnowledgeSource:
    id: str
    title: str
    kind: str  # "github" | "paper" | "note" | "book" | "other"
    uri: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    added_at: str = ""


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class KnowledgeBase:
    def __init__(self, store_dir: str = "./data/knowledge"):
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)
        self._path = os.path.join(store_dir, "sources.json")
        self._sources: list[KnowledgeSource] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    for row in json.load(f):
                        self._sources.append(KnowledgeSource(**row))
            except Exception:
                self._sources = []

    def _save(self) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in self._sources], f, indent=2)
        os.replace(tmp, self._path)

    def add(self, title: str, kind: str, content: str, uri: str = "", tags: list[str] | None = None) -> KnowledgeSource:
        src = KnowledgeSource(
            id="src_" + uuid.uuid4().hex[:8], title=title, kind=kind, uri=uri,
            content=content, tags=tags or [], added_at=datetime.now(timezone.utc).isoformat(),
        )
        self._sources.append(src)
        self._save()
        return src

    def remove(self, source_id: str) -> bool:
        before = len(self._sources)
        self._sources = [s for s in self._sources if s.id != source_id]
        if len(self._sources) != before:
            self._save()
            return True
        return False

    def list(self) -> list[KnowledgeSource]:
        return list(self._sources)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """TF-IDF cosine retrieval over title+content+tags."""
        if not self._sources:
            return []
        docs = [f"{s.title} {' '.join(s.tags)} {s.content}" for s in self._sources]
        tok_docs = [_tokens(d) for d in docs]
        qtok = _tokens(query)
        if not qtok:
            return []
        df = Counter()
        for td in tok_docs:
            for t in set(td):
                df[t] += 1
        n = len(tok_docs)
        idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        qvec = Counter(qtok)
        qnorm = math.sqrt(sum((c * idf.get(t, 1.0)) ** 2 for t, c in qvec.items())) or 1.0
        scored = []
        for s, td in zip(self._sources, tok_docs):
            dvec = Counter(td)
            dot = sum(qvec[t] * dvec.get(t, 0) * idf.get(t, 1.0) ** 2 for t in qvec)
            dnorm = math.sqrt(sum((c * idf.get(t, 1.0)) ** 2 for t, c in dvec.items())) or 1.0
            sim = dot / (qnorm * dnorm)
            scored.append((sim, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"id": s.id, "title": s.title, "kind": s.kind, "uri": s.uri,
                 "score": round(sim, 4), "excerpt": s.content[:400]} for sim, s in scored[:top_k] if sim > 0]
