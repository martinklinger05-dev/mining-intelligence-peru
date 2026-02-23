from dataclasses import dataclass


@dataclass
class SearchResult:
    snippet: str
    score: int


def simple_search(text: str, query: str, window: int = 500) -> list[SearchResult]:
    q = query.lower().strip()
    t = text.lower()

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