import json
import unittest

from app.answer import format_hits
from app.evaluate import QUESTIONS, evaluate
from app.regulation import load_units
from app.search import Index, best_passage, stem, tokenize


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = Index(load_units()[0])

    def test_stemming_and_synonyms(self):
        self.assertEqual(stem("notificar"), stem("notificados"))
        self.assertEqual(stem("accidentes"), stem("accidente"))
        self.assertIn(stem("proteccion"), tokenize("uso de EPP", expand=True))
        self.assertNotIn(stem("proteccion"), tokenize("uso de EPP"))

    def test_definition_question_returns_definition(self):
        hit = self.index.search("¿Qué es un incidente peligroso?", k=1)[0]
        self.assertEqual(hit.unit.term, "Incidente peligroso y/o situación de emergencia")

    def test_citations_show_amendments_and_notice(self):
        text = format_hits("notificar accidente mortal", self.index.search("notificar accidente mortal", k=3))
        self.assertIn("Artículo 164", text)
        self.assertIn("DS N° 023-2017-EM", text)
        self.assertIn("No incluye el DS 034-2023-EM", text)
        self.assertIn("No se encontraron", format_hits("xyzzy", self.index.search("xyzzy")))

    def test_passage_contains_query_terms(self):
        text = "Primera oración sin relación. " * 30 + "La velocidad del aire no será menor de veinte metros. " + "Otra frase. " * 30
        self.assertIn("velocidad del aire", best_passage(text, [stem("velocidad"), stem("aire")]))

    def test_evaluation_does_not_regress(self):
        questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
        summary = evaluate(self.index, questions)["summary"]
        # Valores al publicar la versión 0.2.0: all 20/30 (hit@1) y 27/30 (hit@3).
        self.assertGreaterEqual(summary["all"]["hit@1"], 20)
        self.assertGreaterEqual(summary["all"]["hit@3"], 27)
        self.assertGreaterEqual(summary["test"]["hit@3"], 14)


if __name__ == "__main__":
    unittest.main()
