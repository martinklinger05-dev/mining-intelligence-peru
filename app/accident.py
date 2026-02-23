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
    d = description.lower()

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

    extracted = extract_search_terms(description)[:8]

    # Multi-search on DS024
    terms = preset_queries + extracted
    results = multi_search(ds024_text, terms, window=900)
    ans = answer_with_citation(" ".join(preset_queries), results)

    # Consecuencia (corrige 'no lesionado')
    consequence = "Daños materiales y/o condición de riesgo operacional."
    if "no lesion" in d or "sin lesion" in d or "no lesionado" in d or "operador no lesionado" in d or "sin lesiones" in d:
        consequence = "Daños materiales. No se reportan lesiones al personal."
    elif "lesion" in d or "lesión" in d:
        consequence = "Evento con lesión(es) reportada(s)."

    # Causa inmediata (heurística)
    causa_inmediata = "Pérdida de control por maniobra y/o control de velocidad no adecuado a la condición de la vía."
    if "humed" in d or "húmed" in d or "mojad" in d:
        causa_inmediata = "Pérdida de adherencia neumático–superficie por humedad, sumado a maniobra/velocidad no adecuada."
    if "pare" in d:
        causa_inmediata = "Ejecución de maniobra sin detención completa (PARE) y control de velocidad no adecuado al tramo."

    # 5 porqués simplificado
    cinco_porques = [
        "1) ¿Por qué ocurrió el evento? Porque se ejecutó la maniobra sin control adecuado (PARE/velocidad) en una zona de mayor riesgo.",
        "2) ¿Por qué no hubo control adecuado? Porque no se aplicó el estándar/procedimiento de tránsito interno y conducción defensiva.",
        "3) ¿Por qué no se aplicó el estándar? Por brecha de disciplina operativa y/o supervisión en puntos críticos.",
        "4) ¿Por qué existe esa brecha? Por capacitación/validación insuficiente y controles preventivos no consistentes.",
        "5) ¿Por qué los controles no son consistentes? Porque falta reforzar el sistema de gestión (IPERC continuo, verificación en campo, retroalimentación de PETS/estándares).",
    ]

    actions = [
        {
            "accion": "Reentrenamiento y evaluación en conducción defensiva y control de velocidad (rampas/curvas).",
            "responsable": "Supervisor de Operaciones / SSOMA",
            "plazo": "7 días",
        },
        {
            "accion": "Verificación del cumplimiento de señalización PARE (detención completa) en puntos críticos.",
            "responsable": "Supervisión / Vigías",
            "plazo": "Inmediato y continuo",
        },
        {
            "accion": "Inspección y reporte de condiciones de vía (humedad/material suelto) y medidas de control.",
            "responsable": "Operaciones / Mantenimiento de Vías",
            "plazo": "48 horas",
        },
        {
            "accion": "Reforzar IPERC continuo antes de maniobras y ante cambios de condición.",
            "responsable": "Todos + Supervisor",
            "plazo": "Inmediato",
        },
        {
            "accion": "Actualizar PETS/estándar de tránsito interno con lecciones aprendidas del evento.",
            "responsable": "SSOMA / Operaciones",
            "plazo": "14 días",
        },
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
        + "\n".join(cinco_porques)
        + "\n\n"
        "6. SUSTENTO NORMATIVO (DS 024-2016-EM)\n"
        f"{ans.response}\n\n"
        "7. ACCIONES CORRECTIVAS / PREVENTIVAS (PROPUESTA)\n"
    )

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
        "acto_subestandar": acto,
        "condicion_subestandar": condicion,
        "conclusion": informe.strip(),
        "normative_support": ans.response,
        "consequence": consequence,
        "causa_inmediata": causa_inmediata,
        "cinco_porques": cinco_porques,
        "actions": actions,
    }