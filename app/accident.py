from datetime import datetime
from app.answer import answer_with_citation
from app.search import multi_search
from app.query_utils import extract_search_terms


def generate_accident_report(description: str, text: str) -> dict:
    """
    Generates structured accident report using DS024 support.
    """

    # Buscar sustento normativo relacionado (seguridad / riesgo)
    terms = extract_search_terms(description)
    results = multi_search(text, terms, window=800)
    ans = answer_with_citation(description, results)

    # Identificación básica de factores
    desc_lower = description.lower()

    acto = "No determinado"
    condicion = "No determinada"

    if "no respet" in desc_lower or "no cumpl" in desc_lower:
        acto = "Incumplimiento de procedimiento o señalización establecida"

    if "húmed" in desc_lower or "mojad" in desc_lower:
        condicion = "Superficie de rodadura con presencia de humedad"

    if "velocidad" in desc_lower:
        acto = "Control inadecuado de velocidad"

    conclusion = f"""
CONCLUSIÓN TÉCNICA:

Del análisis del evento descrito, se identifica como acto subestándar: {acto}.
Asimismo, se determina como condición subestándar: {condicion}.

El evento se encuentra relacionado con disposiciones establecidas en el DS 024-2016-EM.
{ans.response}
"""

    recommendations = """
RECOMENDACIONES:

1. Reforzar capacitación en conducción defensiva.
2. Verificar cumplimiento de señalización obligatoria.
3. Implementar inspección preventiva de condiciones de vía.
4. Supervisión directa en zonas críticas de operación.
"""

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
        "conclusion": conclusion.strip(),
        "recommendations": recommendations.strip(),
        "normative_support": ans.response,
    }