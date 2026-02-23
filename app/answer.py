from dataclasses import dataclass
import re

from app.search import SearchResult
from app.citation import extract_article, extract_chapter


@dataclass
class Answer:
    response: str
    article: str | None
    chapter: str | None
    chapter_title: str | None
    evidence: str


def _make_summary_from_snippet(snippet: str) -> str:
    """
    Very simple summarizer: takes the most informative first 1–2 sentences/clauses.
    """
    clean = " ".join(snippet.replace("\n", " ").split())
    # Cut after a reasonable length
    if len(clean) > 420:
        clean = clean[:420].rsplit(" ", 1)[0] + "..."

    # Try to start near "Artículo XX.-"
    m = re.search(r"(Artículo\s+\d+\s*[-\.]\s*)(.*)", clean, flags=re.IGNORECASE)
    if m:
        return m.group(2).strip()

    return clean.strip()


def answer_with_citation(query: str, results: list[SearchResult]) -> Answer:
    if not results:
        return Answer(
            response=f"No encontré evidencia directa para: {query}",
            article=None,
            chapter=None,
            chapter_title=None,
            evidence=""
        )

    top = results[0].snippet

    article = extract_article(top, query=query)
    chapter, chapter_title = extract_chapter(top)

    summary = _make_summary_from_snippet(top)

    # Armado de respuesta con cita
    prefix = "Según el DS 024-2016-EM"
    if chapter and chapter_title:
        prefix += f" (Capítulo {chapter}: {chapter_title})"
    if article:
        prefix += f" (Artículo {article})"

    response = f"{prefix}: {summary}"

    return Answer(
        response=response,
        article=article,
        chapter=chapter,
        chapter_title=chapter_title,
        evidence=top
    )