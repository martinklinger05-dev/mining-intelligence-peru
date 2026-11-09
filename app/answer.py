"""Formato de respuestas: cita completa, estado de modificación y fragmento de evidencia."""
from __future__ import annotations

from app import VALIDITY_NOTICE
from app.regulation import Unit
from app.search import Hit


def citation(unit: Unit) -> str:
    parts = ["DS 024-2016-EM"]
    if unit.title:
        if unit.kind == "anexo":
            parts.append(unit.title.title() if unit.title.isupper() else unit.title)
        else:
            parts.append(f"Título {unit.title}")
    if unit.chapter:
        name = (unit.chapter_name or "").capitalize()
        parts.append(f"Capítulo {unit.chapter}" + (f" ({name})" if name else ""))
    if unit.subchapter:
        parts.append(f"Subcapítulo {unit.subchapter}" + (f" ({unit.subchapter_name})" if unit.subchapter_name else ""))
    parts.append(unit.label)
    return ", ".join(parts)


def amendment_note(unit: Unit) -> str:
    if not unit.amendments:
        return "Sin modificaciones registradas en el texto incluido."
    notes = "; ".join(f"{a['action']} por {a['decree']} ({a['date']})" for a in unit.amendments)
    shown = " Se muestra el texto modificado." if unit.original_text else ""
    return f"{notes[0].upper()}{notes[1:]}.{shown}"


def format_hits(query: str, hits: list[Hit]) -> str:
    if not hits:
        return (f"No se encontraron artículos relacionados con: {query}\n"
                "Pruebe con otras palabras (por ejemplo, el nombre del tema o la sigla: EPP, IPERC, PETAR).")
    lines = [f"Artículos más relacionados con: {query}", ""]
    for n, hit in enumerate(hits, 1):
        lines += [f"[{n}] {citation(hit.unit)}",
                  f"    Estado: {amendment_note(hit.unit)}",
                  f"    {hit.passage}", ""]
    lines.append("Use /ver N para leer el texto completo. " + VALIDITY_NOTICE)
    return "\n".join(lines)


def format_unit(unit: Unit) -> str:
    text = [citation(unit), amendment_note(unit), "", unit.text]
    if unit.original_text:
        text += ["", "Texto anterior a la modificación (solo como referencia):", unit.original_text]
    return "\n".join(text)
