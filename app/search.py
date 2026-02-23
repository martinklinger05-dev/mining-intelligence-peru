from dataclasses import dataclass
from app.text_utils import normalize


@dataclass
class SearchResult:
    snippet: str
    score: int


def simple_search(text: str, query: str, window: int = 500) -> list[SearchResult]:
    q = normalize(query).strip()
    t = normalize(text)

    results: list[SearchResult] = []
    start = 0

    while True:
        idx = t.find(q, start)
        if idx == -1:
            break

        left = max(0, idx - window)
        right = min(len(text), idx + window)

        snippet = text[left:right].replace("\n", " ").strip()
        score = snippet.lower().count(q)

        results.append(SearchResult(snippet=snippet, score=score))
        start = idx + len(q)

        if len(results) >= 5:
            break

    results.sort(key=lambda r: r.score, reverse=True)
    return results
import re
from app.text_utils import normalize

TOC_PATTERNS = [
    r"t[ií]tulo\s+[a-z0-9]+",
    r"subcap[ií]tulo",
    r"\(art\.\s*\d+\s*-\s*art\.\s*\d+\)",  # rangos tipo (Art. 40 - Art. 43)
]

def looks_like_toc(snippet: str) -> bool:
    s = normalize(snippet)
    hits = 0
    for p in TOC_PATTERNS:
        if re.search(p, s):
            hits += 1
    # Si parece índice (varios patrones), lo descartamos
    return hits >= 2


def multi_search(text: str, terms: list[str], window: int = 650, max_results: int = 5) -> list[SearchResult]:
    all_results: list[SearchResult] = []

    for term in terms:
        res = simple_search(text, term, window=window)
        all_results.extend(res)

    # Orden por score
    all_results.sort(key=lambda r: r.score, reverse=True)

    # Filtrar TOC + deduplicar
    seen = set()
    final: list[SearchResult] = []
    for r in all_results:
        if looks_like_toc(r.snippet):
            continue

        key = normalize(r.snippet[:140])
        if key in seen:
            continue
        seen.add(key)
        final.append(r)

        if len(final) >= max_results:
            break

    return final