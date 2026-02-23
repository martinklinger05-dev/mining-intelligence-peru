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

    # Heurísticas simples para consecuencias
    d = description.lower()
    consequence = "Daños materiales y/o condición de riesgo operacional. Sin información de lesiones."
    if "sin lesion" in d or "no lesion" in d or "sin lesiones" in d:
        consequence = "Daños materiales. No se reportan lesiones al personal."
    if "lesion" in d and ("si" in d or "hubo" in d):
        consequence = "Evento con lesión(es) reportada(s)."

    # Causa inmediata (heurística)
    causa_inmediata = "Pérdida de control por maniobra y/o control de velocidad no adecuado a la condición de la vía."
    if "humed" in d or "húmed" in d:
        causa_inmediata = "Pérdida de adherencia neumático–superficie por humedad, sumado a maniobra/velocidad no adecuada."
    if "pare" in d:
        causa_inmediata = "Ejecución de maniobra sin detención completa (PARE) y control de velocidad no adecuado al tramo."

    # 5 porqués simplificado (plantilla)
    cinco_porques = [
        "1) ¿Por qué ocurrió el evento? Porque se ejecutó la maniobra sin control adecuado (PARE/velocidad) en una zona de mayor riesgo.",
        "2) ¿Por qué no hubo control adecuado? Porque no se aplicó el estándar/procedimiento de tránsito interno y conducción defensiva.",
        "3) ¿Por qué no se aplicó el estándar? Por brecha de disciplina operativa y/o supervisión en puntos críticos.",
        "4) ¿Por qué existe esa brecha? Por capacitación/validación insuficiente y controles preventivos no consistentes.",
        "5) ¿Por qué los controles no son consistentes? Porque falta reforzar el sistema de gestión (IPERC continuo, verificación en campo, retroalimentación de PETS/estándares).",
    ]

    informe = (
        "INFORME DE INVESTIGACIÓN – BORRADOR AUTOMÁTICO (MIP)\n\n"
        "1. RESUMEN DEL EVENTO\n"
        f"{description.strip()}\n\n"
        "2. HALLAZGO CLAVE\n"
        f"El evento se asocia a {acto.lower()} en presencia de {condicion.lower()}.\n\n"
        "3. CLASIFICACIÓN\n"
        f"Acto subestándar: {acto}\n"
        f"Condición subestándar: {condicion}\n"
        f"Consecuencia: {consequence}\n\n"
        "4. CAUSA INMEDIATA (PROBABLE)\n"
        f"{causa_inmediata}\n\n"
        "5. CAUSA RAÍZ (5 POR QUÉS – PRELIMINAR)\n"
        + "\n".join(cinco_porques) + "\n\n"
        "6. SUSTENTO NORMATIVO (DS 024-2016-EM)\n"
        f"{ans.response}\n\n"
        "7. ACCIONES CORRECTIVAS / PREVENTIVAS (PROPUESTA)\n"
        "1) Reentrenamiento y evaluación en conducción defensiva y control de velocidad (incluye rampas/curvas). "
        "Responsable: Supervisor de Operaciones / SSOMA. Plazo: 7 días.\n"
        "2) Verificación del cumplimiento de señalización PARE (detención completa) en puntos críticos. "
        "Responsable: Supervisión / Vigías. Plazo: inmediato y continuo.\n"
        "3) Inspección y reporte de condiciones de vía (humedad/material suelto), con medidas de control (señalización temporal, riego/control, restricción). "
        "Responsable: Operaciones / Mantenimiento de Vías. Plazo: 48 horas.\n"
        "4) Reforzar IPERC continuo antes de maniobras y en cambios de condición (humedad/visibilidad). "
        "Responsable: Todos los trabajadores + Supervisor. Plazo: inmediato.\n"
        "5) Actualizar/retroalimentar PETS/estándar de tránsito interno con lecciones aprendidas del evento. "
        "Responsable: SSOMA / Operaciones. Plazo: 14 días.\n"
    )

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
        "acto_subestandar": acto,
        "condicion_subestandar": condicion,
        "conclusion": informe.strip(),
        "recommendations": "",  # ya está dentro del informe
        "normative_support": ans.response,
    }