"""Búsqueda por artículo con BM25 sobre el texto vigente del DS 024-2016-EM.

No usa modelos de lenguaje: ordena artículos, definiciones y anexos por relevancia léxica
(BM25), con normalización de tildes, una reducción simple de plurales y género, y una tabla
de siglas y sinónimos del sector (EPP, IPERC, PETAR…).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from app.regulation import Unit, normalize

STOPWORDS = set(
    "a al algo algun alguna algunas alguno algunos ante antes aquel aquella aquello asi aun bajo "
    "cada como con contra cual cuales cuando cuanto cuanta cuantos cuantas de del desde donde dos "
    "e el ella ellas ellos en entre era es esa esas ese eso esos esta estan estar este esto estos "
    "fue ha han hasta hay la las le les lo los mas me mi mis muy ni no nos o otra otras otro otros "
    "para pero poco por porque puede pueden puedo que quien quienes se segun ser si sido sin sobre "
    "son su sus tal tambien tan tanto te tiene tienen todo todos tu un una uno unos unas usted y ya "
    "dice dicen indica establece debe deben deberan debera hacer hace "
    "ds 024 2016 em decreto supremo reglamento".split()
)

# Siglas y expresiones del sector. Se expanden en la consulta, no en los documentos.
SYNONYMS = {
    "epp": "equipo proteccion personal",
    "iperc": "identificacion peligros evaluacion riesgos medidas control",
    "petar": "permiso escrito trabajo alto riesgo",
    "pets": "procedimiento escrito trabajo seguro",
    "ats": "analisis trabajo seguro",
    "sso": "seguridad salud ocupacional",
    "sst": "seguridad salud ocupacional",
    "loto": "bloqueo candado tarjeta",
    "negarme": "derecho retirarse peligro",
    "negarse": "derecho retirarse peligro",
    "negativa": "derecho retirarse peligro",
    "msnm": "metros nivel mar",
    "etiquetado": "tarjeta",
    "comite": "comite seguridad salud ocupacional",
    "interior": "subterraneo",
    "socavon": "subterraneo",
}

K1, B = 1.2, 0.75


SUFFIXES = sorted(
    "aciones acion amientos amiento imientos imiento adoras adores adora ador ables able ibles ible "
    "mente ados adas idos idas ado ada ido ida ando iendo ciones cion ar er ir es s a o e".split(),
    key=len, reverse=True)


def stem(word: str) -> str:
    """Reducción ligera de sufijos en español (plural, género, participios, -ción).
    "notificar" y "notificados" → "notific"; "accidentes" → "accident"."""
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[:-len(suffix)]
    return word


def tokenize(text: str, expand: bool = False) -> list[str]:
    words = re.findall(r"[a-z0-9]+", normalize(text))
    out = []
    for w in words:
        if w in STOPWORDS or (len(w) < 3 and not w.isdigit()):
            continue
        out.append(stem(w))
        if expand and w in SYNONYMS:
            out.extend(stem(x) for x in SYNONYMS[w].split())
    return out


@dataclass
class Hit:
    unit: Unit
    score: float
    passage: str
    matched: list[str]


def _fields(unit: Unit) -> list[str]:
    tokens = tokenize(unit.text)
    # La primera oración de un artículo suele enunciar su objeto ("Son funciones del Comité…").
    tokens += tokenize(re.split(r"(?<=[.:])\s", unit.text, maxsplit=1)[0][:250])
    if unit.term:  # el término definido pesa como título
        tokens += tokenize(unit.term) * 2
    heading = " ".join(x for x in (unit.chapter_name, unit.subchapter_name) if x)
    if unit.kind == "anexo" and unit.title:
        heading += " " + unit.title
    tokens += tokenize(heading) * 2
    return tokens


class Index:
    def __init__(self, units: list[Unit]):
        # El artículo 7 completo se reemplaza por sus definiciones individuales.
        has_definitions = any(u.kind == "definicion" for u in units)
        self.units = [u for u in units if not (has_definitions and u.kind == "articulo" and u.number == "7")]
        self.docs = [Counter(_fields(u)) for u in self.units]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / len(self.lengths)
        df = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        # Texto compacto (sin espacios) para encontrar palabras que quedaron partidas en el PDF.
        self.compact = [re.sub(r"[^a-z0-9]", "", normalize(u.text)) for u in self.units]

    def search(self, query: str, k: int = 5) -> list[Hit]:
        terms = tokenize(query, expand=True)
        raw_words = [w for w in re.findall(r"[a-z0-9]+", normalize(query)) if len(w) >= 6 and w not in STOPWORDS]
        if not terms:
            return []
        q = Counter(terms)
        definitional = bool(re.search(r"\b(que es|que son|que significa|definicion|define|concepto)\b", normalize(query)))
        scored = []
        for i, doc in enumerate(self.docs):
            score, matched = 0.0, []
            norm = K1 * (1 - B + B * self.lengths[i] / self.avg)
            for t, qtf in q.items():
                tf = doc.get(t, 0)
                if tf:
                    score += self.idf[t] * tf * (K1 + 1) / (tf + norm) * (1 + 0.2 * (qtf - 1))
                    matched.append(t)
            for w in raw_words:  # rescate de palabras partidas: coincidencia exacta en texto compacto
                t = stem(w)
                if t not in matched and w in self.compact[i]:
                    score += self.idf.get(t, 1.0) * 0.5
                    matched.append(t)
            unit = self.units[i]
            if score > 0 and unit.term and definitional:
                # "¿Qué es X?": premia la definición cuyo término coincide con la pregunta.
                term_tokens = set(tokenize(unit.term))
                coverage = len(term_tokens & set(terms)) / len(term_tokens) if term_tokens else 0
                score *= 1 + coverage
            if score > 0:
                scored.append((score, i, matched))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [Hit(self.units[i], s, best_passage(self.units[i].text, m), m) for s, i, m in scored[:k]]


def best_passage(text: str, stems: list[str], size: int = 420) -> str:
    """Fragmento del artículo con más términos de la consulta (para mostrar como evidencia)."""
    flat = " ".join(text.split())
    if len(flat) <= size:
        return flat
    sentences = re.split(r"(?<=[.;:])\s+|\s(?=[a-z0-9]{1,2}\)\s)", flat)
    best, best_score = flat[:size], -1
    for start in range(len(sentences)):
        chunk = ""
        for s in sentences[start:]:
            if len(chunk) + len(s) > size and chunk:
                break
            chunk = (chunk + " " + s).strip()
        words = {stem(w) for w in re.findall(r"[a-z0-9]+", normalize(chunk))}
        score = sum(1 for t in set(stems) if t in words)
        if score > best_score:
            best, best_score = chunk, score
    if len(best) > size:
        best = best[:size].rsplit(" ", 1)[0] + "…"
    prefix = "" if flat.startswith(best[:40]) else "… "
    suffix = "" if best.endswith("…") or flat.endswith(best[-40:]) else " …"
    return prefix + best + suffix
