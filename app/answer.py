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


def _make_summary_from_snippet(snippet: str, query: str) -> str:
    clean = " ".join(snippet.replace("\n", " ").split())
    q = query.lower()

    # If question is about EPP, try to start at Article 81
    if "epp" in q:
        m81 = re.search(r"(Artículo\s+81\s*[-\.]\s*)(.*)", clean, flags=re.IGNORECASE)
        if m81:
            clean = m81.group(2).strip()

    # Prefer starting at withdrawal clause if present
    lower = clean.lower()
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

    # If another article starts, cut before it
    cut = re.search(r"\bArtículo\s+\d+", clean, flags=re.IGNORECASE)
    if cut and cut.start() > 0:
        clean = clean[:cut.start()].strip()

    # Limit length
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

    summary = _make_summary_from_snippet(top, query)

    # normalize weird split words/spaces from PDF extraction (on summary)
    summary = re.sub(r"\s+", " ", summary)
    summary = summary.replace("acc esos", "accesos")
    summary = summary.replace("pre establecidos", "preestablecidos")

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