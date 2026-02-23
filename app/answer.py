from dataclasses import dataclass
from app.search import SearchResult
from app.citation import extract_article, extract_chapter


@dataclass
class Answer:
    response: str
    article: str | None
    chapter: str | None
    chapter_title: str | None
    evidence: str


def answer_with_citation(query: str, results: list[SearchResult]) -> Answer:

    if not results:
        return Answer("No se encontró información relevante.", None, None, None, "")

    top = results[0].snippet

    article = extract_article(top)
    chapter, chapter_title = extract_chapter(top)

    response = f"Según el DS 024-2016-EM (Artículo {article}), ..."

    return Answer(
        response=response,
        article=article,
        chapter=chapter,
        chapter_title=chapter_title,
        evidence=top
    )