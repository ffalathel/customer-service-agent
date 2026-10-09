import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi


@dataclass
class PolicyDoc:
    title: str
    text: str
    score: float = 0.0


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class PolicyKB:
    def __init__(self, docs_dir: Path):
        self._docs = [PolicyDoc(p.stem, p.read_text()) for p in sorted(docs_dir.glob("*.md"))]
        self._bm25 = BM25Okapi([_tokens(d.text) for d in self._docs])

    def search(self, query: str, k: int = 3) -> list[PolicyDoc]:
        scores = self._bm25.get_scores(_tokens(query))
        ranked = sorted(zip(scores, self._docs), key=lambda pair: -pair[0])[:k]
        return [PolicyDoc(d.title, d.text, float(s)) for s, d in ranked]
