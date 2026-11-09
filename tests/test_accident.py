import json
import tempfile
import unittest
from pathlib import Path

from docx import Document

from app.accident import EventInput, build_report, detect_factors, report_text
from app.regulation import load_units
from app.search import Index
from app.storage import append_history, read_last_history
from app.word_export import export_report_docx

DESCRIPTION = ("Volquete desciende por rampa húmeda, al girar hacia un by pass no realiza el PARE completo, "
               "pierde adherencia y choca contra el hastial.")


def event(**changes):
    data = dict(equipo="Volquete 21", area="NV 4300", turno="noche", fecha_evento="2026-02-20 03:15",
                lesiones=False, danio="material", descripcion=DESCRIPTION)
    data.update(changes)
    return EventInput(**data)


class AccidentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = Index(load_units()[0])

    def test_factors_use_whole_words(self):
        # La versión anterior detectaba "pare" dentro de "parecía" y "distr" en "distribución".
        self.assertEqual(detect_factors("El operador parecía atento; se separó la carga para su distribución"), [])
        keys = [f["key"] for f in detect_factors(DESCRIPTION)]
        self.assertEqual(keys, ["superficie", "pendiente", "curva", "senal", "acarreo"])

    def test_input_validation(self):
        for bad in (dict(descripcion="  "), dict(danio="grave"), dict(lesiones=True, danio="material"),
                    dict(lesiones=False, danio="personal"), dict(fecha_evento="20/02/2026")):
            with self.assertRaises(ValueError):
                event(**bad)

    def test_report_does_not_invent_causes(self):
        report = build_report(event(), self.index)
        text = report_text(report)
        self.assertIn("no constituye informe de investigación", text)
        self.assertIn("Incidente (sin lesiones)", report.classification)
        self.assertTrue(any("definición: Incidente" in b for b in report.classification_basis))
        self.assertTrue(report.pending)
        self.assertNotIn("Causa raíz:", text)
        self.assertTrue(all("XIX" in p["citation"] for p in report.procedure))
        self.assertTrue(report.regulations)
        self.assertIn("No incluye el DS 034-2023-EM", text)
        injured = build_report(event(lesiones=True, danio="personal"), self.index)
        self.assertIn("Accidente de trabajo", injured.classification)

    def test_word_export_has_sections_to_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = export_report_docx(build_report(event(), self.index), Path(tmp))
            doc = Document(str(path))
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        self.assertIn("8. Análisis de causa raíz (5 porqués)", headings)
        self.assertEqual(len(doc.tables[-1].rows), 6)  # encabezado + 5 filas vacías de acciones

    def test_history_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            for i in range(12):
                append_history({"timestamp": str(i), "question": f"q{i}"}, path)
            path.write_text(path.read_text(encoding="utf-8") + "no es json\n", encoding="utf-8")
            items = read_last_history(10, path)
        self.assertEqual(len(items), 9)
        self.assertEqual(items[-1]["question"], "q11")


if __name__ == "__main__":
    unittest.main()
