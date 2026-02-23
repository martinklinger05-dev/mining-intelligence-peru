from dataclasses import dataclass
from app.search import SearchResult
from app.citation import extract_article


@dataclass
class Answer:
    response: str
    article: str | None
    evidence: str


def answer_with_citation(query: str, results: list[SearchResult]) -> Answer:
    if not results:
        return Answer(
            response=f"No encontré evidencia directa para: {query}",
            article=None,
            evidence=""
        )

    top = results[0].snippet
    article = extract_article(top, query=query)

    # Resumen simple (luego lo haremos IA)
    response = (
        "Para trabajos con riesgo es obligatorio usar EPP con especificaciones técnicas y "
        "certificados de calidad, y mantenerlos en buen estado de funcionamiento, conservación e higiene."
    )

    if article:
        response = f"Según el DS 024-2016-EM (Artículo {article}), " + response
    else:
        response = "Según el DS 024-2016-EM, " + response

    return Answer(response=response, article=article, evidence=top)