"""Exporta el borrador de investigación a Word (.docx) con secciones para completar."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.accident import Report
from app.storage import OUTPUT_DIR


def _table(doc, headers: list[str], rows: int):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, headers):
        cell.text = text
    for _ in range(rows):
        table.add_row()
    return table


def export_report_docx(report: Report, folder: Path = OUTPUT_DIR) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"borrador_investigacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    e = report.event
    doc = Document()
    title = doc.add_heading("BORRADOR PARA INICIAR LA INVESTIGACIÓN", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note = doc.add_paragraph("Documento de trabajo. No constituye el informe de investigación ni determina causas.")
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("1. Datos del evento", level=2)
    data = [("Equipo", e.equipo), ("Área / labor", e.area), ("Turno", e.turno), ("Fecha y hora", e.fecha_evento),
            ("Lesiones", "Sí" if e.lesiones else "No"), ("Tipo de daño", e.danio),
            ("Supervisor responsable", ""), ("Código de informe", "")]
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for k, v in data:
        row = table.add_row().cells
        row[0].text, row[1].text = k, v
    doc.add_paragraph()
    doc.add_paragraph(e.descripcion)

    doc.add_heading("2. Clasificación preliminar", level=2)
    doc.add_paragraph(report.classification)
    for b in report.classification_basis:
        doc.add_paragraph(b, style="List Bullet")

    doc.add_heading("3. Posibles factores mencionados (verificar; no son causas)", level=2)
    if report.factors:
        for f in report.factors:
            doc.add_paragraph(f"{f['label']} (palabras: {', '.join(f['evidence'])})", style="List Bullet")
    else:
        doc.add_paragraph("Ninguno detectado por palabras clave.")

    doc.add_heading("4. Normativa relacionada con cada factor (revisar aplicabilidad)", level=2)
    for r in report.regulations:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(r["citation"]).bold = True
        p.add_run(f" — relacionado con: {'; '.join(r['factors'])}").italic = True
        doc.add_paragraph(r["passage"])

    doc.add_heading("5. Notificación e investigación: artículos aplicables", level=2)
    for r in report.procedure:
        doc.add_paragraph(r["citation"], style="List Bullet")

    doc.add_heading("6. Causas inmediatas (completar tras verificar en campo)", level=2)
    causes = _table(doc, ["Tipo", "Descripción", "Evidencia"], 4)
    for row, label in zip(causes.rows[1:], ["Acto subestándar", "Acto subestándar", "Condición subestándar", "Condición subestándar"]):
        row.cells[0].text = label
    doc.add_heading("7. Causas básicas", level=2)
    _table(doc, ["Factor", "Descripción", "Evidencia"], 3)
    doc.add_heading("8. Análisis de causa raíz (5 porqués)", level=2)
    t = _table(doc, ["N°", "¿Por qué?", "Respuesta / evidencia"], 5)
    for i in range(1, 6):
        t.rows[i].cells[0].text = str(i)
    doc.add_heading("9. Acciones correctivas y preventivas", level=2)
    _table(doc, ["N°", "Acción", "Responsable", "Plazo", "Estado"], 5)

    doc.add_paragraph()
    doc.add_paragraph().add_run(report.notice).italic = True
    doc.add_paragraph("\n_______________________________\nFirma del supervisor responsable")
    doc.save(str(path))
    return path
