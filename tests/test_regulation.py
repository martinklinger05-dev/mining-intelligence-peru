import collections
import unittest

from app.regulation import (INDEX_PATH, PDF_PATH, build_vocabulary, load_units, parse_articles,
                            parse_document, repair_split_words, split_definitions, Unit)


class RepairTests(unittest.TestCase):
    def test_joins_fragments_only_when_full_word_exists(self):
        vocab = build_vocabulary("mineras mineras reglamento reglamento por debajo debajo bajo bajo bajo bajo de riesgo")
        fixed, joins = repair_split_words("actividades m ineras del reglam ento", vocab)
        self.assertEqual(fixed, "actividades mineras del reglamento")
        self.assertEqual(joins, 2)

    def test_does_not_merge_real_words(self):
        # "bajo" aparece muchas veces sola, así que no se trata como fragmento.
        text = ("trabajos de bajo riesgo. por debajo de. por debajo del. bajo control. bajo supervisión. "
                "bajo responsabilidad. bajo techo. bajo tierra.")
        fixed, _ = repair_split_words(text)
        self.assertIn("de bajo riesgo", fixed)

    def test_prefers_longer_word_after_function_word(self):
        vocab = collections.Counter({"maquinaria": 9, "dem": 2, "de": 50, "m": 30, "aquinaria": 3})
        fixed, _ = repair_split_words("uso de m aquinaria", vocab)
        self.assertEqual(fixed, "uso de maquinaria")


class ParseTests(unittest.TestCase):
    SAMPLE = (
        "TÍTULO PRIMERO\nGESTIÓN\nCAPÍTULO I\nDISPOSICIONES GENERALES\nSubcapítulo I\nObjetivos\n"
        "     Artículo 1.- Texto del primero.\n"
        "     Artículo 2.- Texto original del segundo. (*)\n"
        "(*) Artículo modificado por el Artículo 1 del Decreto Supremo N° 023 -2017-EM, publicado el 18 "
        "agosto 2017, cuyo texto es el siguiente:\n"
        "     “Artículo 2.- Texto vigente del segundo.”\n"
        "CAPÍTULO II\nSUPERVISORES\n     Artículo 3 . - Texto del tercero.\n"
    )

    def test_amended_article_keeps_current_text_and_history(self):
        units = {u.number: u for u in parse_articles(self.SAMPLE)}
        self.assertEqual(list(units), ["1", "2", "3"])
        self.assertEqual(units["2"].text, "Texto vigente del segundo.")
        self.assertEqual(units["2"].original_text, "Texto original del segundo.")
        self.assertEqual(units["2"].amendments[0]["decree"], "DS N° 023-2017-EM")
        self.assertEqual(units["2"].amendments[0]["date"], "18 agosto 2017")
        self.assertEqual((units["1"].chapter, units["1"].chapter_name), ("I", "DISPOSICIONES GENERALES"))
        self.assertEqual(units["3"].chapter, "II")
        self.assertNotIn("CAPÍTULO", units["2"].text)

    def test_definitions_are_split_and_amended_versions_replace_originals(self):
        raw = ("Las siguientes definiciones:\n     Acarreo      Traslado de materiales hacia un destino.\n"
               "     Incidente\n     Suceso con potencial de pérdidas sin lesiones.\n"
               "     Peligro\n     Situación con potencial de daño antiguo. (*)\n"
               "(*) Definición modificada por el Artículo 1 del Decreto Supremo N° 023-2017-EM, publicado el 18 agosto 2017, "
               "cuyo texto es el siguiente:\n     “Peligro: Situación o característica con potencial de causar daño.”\n")
        article = Unit("articulo", "7", "", chapter="I")
        defs = {d.term: d for d in split_definitions(article, raw)}
        self.assertEqual(set(defs), {"Acarreo", "Incidente", "Peligro"})
        self.assertTrue(defs["Peligro"].text.startswith("Situación o característica"))
        self.assertIn("antiguo", defs["Peligro"].original_text)
        self.assertEqual(defs["Acarreo"].label, "Artículo 7 (definición: Acarreo)")


class IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.units, cls.meta = load_units(INDEX_PATH)
        cls.by_label = {u.label: u for u in cls.units}

    def test_all_417_articles_once(self):
        numbers = [u.number for u in self.units if u.kind == "articulo"]
        self.assertEqual(sorted(map(int, numbers)), list(range(1, 418)))

    def test_known_amendments_and_structure(self):
        a164 = self.by_label["Artículo 164"]
        self.assertEqual(a164.amendments[0]["decree"], "DS N° 023-2017-EM")
        self.assertIsNotNone(a164.original_text)
        self.assertIn("veinticuatro (24) horas", a164.text)
        self.assertEqual(a164.chapter, "XIX")
        self.assertIn("NOTIFICACIÓN", a164.chapter_name)
        self.assertTrue(self.by_label["Artículo 40"].text.startswith("Los trabajadores tienen derecho"))
        self.assertIn("Artículo 7 (definición: Identificación de Peligros, Evaluación de Riesgos y Medidas de Control (IPERC))",
                      self.by_label)
        self.assertEqual([u.number for u in self.units if u.kind == "anexo"], ["1", "2", "3"])
        self.assertEqual(self.meta["amendments_included"], ["DS N° 023-2017-EM"])

    def test_no_amendment_notes_left_in_current_text(self):
        for u in self.units:
            self.assertNotIn("cuyo texto es el siguiente", u.text, u.label)
            self.assertNotIn("(*)", u.text, u.label)
            self.assertNotIn("debajo riesgo", u.text, u.label)

    @unittest.skipUnless(PDF_PATH.exists(), "PDF no disponible")
    def test_index_matches_pdf(self):
        try:
            from app.regulation import extract_pdf_text
            data = parse_document(extract_pdf_text())
        except ImportError:
            self.skipTest("pypdf no instalado")
        self.assertEqual(data["counts"], self.meta["counts"])


if __name__ == "__main__":
    unittest.main()
