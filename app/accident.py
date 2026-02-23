from datetime import datetime
from app.answer import answer_with_citation
from app.search import multi_search
from app.query_utils import extract_search_terms


def _detect_act_condition(description: str) -> tuple[str, str]:
    d = description.lower()

    acto = "No determinado"
    condicion = "No determinada"

    # Actos subestándar comunes (manejo/equipos)
    if "pare" in d or "stop" in d:
        acto = "No cumplimiento de señalización obligatoria (PARE) / detención completa"
    if "velocidad" in d or "rápida" in d or "rapida" in d or "control" in d:
        acto = "Control inadecuado de velocidad / conducción no defensiva"
    if "no respet" in d or "incumpl" in d:
        acto = "Incumplimiento de procedimiento o estándar establecido"
    if "distr" in d or "visibilidad" in d or "luces altas" in d:
        acto = "Evaluación deficiente de condiciones de operación / continuidad pese a condición insegura"

    # Condiciones subestándar comunes
    if "húmed" in d or "humed" in d or "mojad" in d:
        condicion = "Superficie de rodadura con presencia de humedad (baja adherencia)"
    if "curva" in d:
        condicion = "Tramo curvo con riesgo incrementado de pérdida de control"
    if "pendiente" in d or "rampa" in d:
        condicion = "Vía en pendiente/rampa (condición de mayor riesgo operacional)"
    if "ilumin" in d or "luces altas" in d or "encandil" in d:
        condicion = "Visibilidad reducida / encandilamiento"

    return acto, condicion


def generate_accident_report(description: str, ds024_text: str) -> dict:
    """
    Generates structured accident report using DS024 support.
    Uses 'smart' preset queries for accident investigations (not just raw description).
    """

    acto, condicion = _detect_act_condition(description)

    # Preset queries for accident/safety driving & risk control
    preset_queries = [
        "conducción defensiva",
        "control de velocidad",
        "señalización PARE",
        "derecho a retirarse de cualquier área de trabajo peligro de alto riesgo",
        "IPERC continuo",
        "supervisor verificar cumplimiento de estándares PETS y uso de EPP",
    ]

    # Also include some extracted keywords from description (but keep them limited)
    extracted = extract_search_terms(description)[:8]

    # Multi-search on DS024
    terms = preset_queries + extracted
    results = multi_search(ds024_text, terms, window=900)
    ans = answer_with_citation(" ".join(preset_queries), results)

    conclusion = (
        "CONCLUSIÓN TÉCNICA:\n\n"
        f"Del análisis del evento descrito, se identifica como acto subestándar: {acto}.\n"
        f"Asimismo, se determina como condición subestándar: {condicion}.\n\n"
        "De acuerdo con el DS 024-2016-EM, se sustenta la necesidad de controlar los riesgos "
        "mediante identificación/gestión y medidas de control, así como el retiro ante peligro alto riesgo "
        "cuando corresponda. Evidencia:\n"
        f"{ans.response}\n"
    )

    recommendations = (
        "RECOMENDACIONES:\n\n"
        "1. Reforzar capacitación y evaluación en conducción defensiva y control de velocidad (incluye maniobras en rampa/curva).\n"
        "2. Asegurar cumplimiento de señalización obligatoria (PARE) con detención completa y verificación de hábitos operativos.\n"
        "3. Implementar inspección preventiva de condiciones de vía (humedad, material suelto) y comunicar alertas operacionales.\n"
        "4. Establecer supervisión en puntos críticos (intersecciones/BP) y reforzar IPERC continuo antes de maniobras.\n"
        "5. Registrar el evento y retroalimentar el PETS/estándar de tránsito interno (lecciones aprendidas).\n"
    )

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
        "acto_subestandar": acto,
        "condicion_subestandar": condicion,
        "conclusion": conclusion.strip(),
        "recommendations": recommendations.strip(),
        "normative_support": ans.response,
    }