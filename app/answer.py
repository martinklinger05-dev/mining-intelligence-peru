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
    clean = " ".join(snippet.replace("\n", " ").split())

    # DEBUG marker: if you see "[SUMMARY_V2]" printed, you're running the updated function
    # (remove later if you want)

    lower = clean.lower()

    # Prefer starting at the "retirarse..." clause if present
    key_phrases = [
        "d) retirarse de cualquier área de trabajo",
        "d) retirarse de cualquier area de trabajo",
        "retirarse de cualquier área de trabajo",
        "retirarse de cualquier area de trabajo",
        "peligro de alto riesgo",
        "dando aviso inmediato a sus superiores",
    ]

    positions = [lower.find(k) for k in key_phrases if lower.find(k) != -1]
    if positions:
        start = min(positions)
        clean = clean[start:]
    else:
        # fallback to article body
        m = re.search(r"(Artículo\s+\d+\s*[-\.]\s*)(.*)", clean, flags=re.IGNORECASE)
        if m:
            clean = m.group(2).strip()
            
    # If another article starts, cut before it
    cut = re.search(r"\bArtículo\s+\d+", clean, flags=re.IGNORECASE)
    if cut and cut.start() > 0:
        clean = clean[:cut.start()].strip()

    if len(clean) > 420:
        clean = clean[:420].rsplit(" ", 1)[0] + "..."

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