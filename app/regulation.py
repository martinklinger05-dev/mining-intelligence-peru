"""Convierte el PDF del DS 024-2016-EM en unidades citables (artículos y anexos).

Problemas del PDF que este módulo resuelve:
  * Texto consolidado: un artículo modificado aparece dos veces, primero con su texto
    original y luego, tras una nota "(*) Artículo modificado por ...", con el texto vigente.
    Se conserva solo el texto vigente para buscar y el original como historial.
  * Palabras partidas por la extracción ("m ineras", "reglam ento"). Se unen solo cuando
    la palabra completa aparece intacta en el mismo documento.
  * Encabezados (Título, Capítulo, Subcapítulo) mezclados con el texto de los artículos.

El índice resultante se guarda en JSON para no depender de la versión de pypdf al consultar.
"""
from __future__ import annotations

import collections
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = ROOT / "data" / "ds024.pdf"
INDEX_PATH = ROOT / "data" / "ds024_index.json"
INDEX_VERSION = 1

ARTICLE_RE = re.compile(r"[“\"]?\s*A\s?r\s?t\s?[íi]\s?c\s?u\s?l\s?o\s+(\d(?:\s?\d){0,2})\s*\.?\s*-\s*")
TITLE_RE = re.compile(r"T[ÍI]TULO\s+(PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO)\b")
CHAPTER_RE = re.compile(r"CAP[ÍI]TULO\s+([IVXLC]+)\b")
SUBCHAPTER_RE = re.compile(r"Subcap[íi]tulo\s+([IVXLC]+)\b")
ANNEX_RE = re.compile(r"(?m)^\s*[\"“]?ANEXO\s+(?:N\s?[º°]\s*)?(\d{1,2})\s*$")
NOTE_RE = re.compile(
    r"\(\*\)\s*(?:\(\*\)\s*)?(Artículo|Definición|Disposición|Literal|Numeral|Inciso|Párrafo|Anexo(?:\s+N\s?[°º])?\s*\d*)\s+"
    r"(modificad[oa]|incorporad[oa]|derogad[oa]|sustituid[oa])\s+por\s+(?:el|la)\s+(.{0,160}?)"
    r"publicad[oa]\s+(?:el\s+)?(\d{1,2}\s+\w+\s+\d{4})(?:,\s*cuyo\s+texto\s+es\s+el\s+siguiente\s*:)?\.?",
    re.S,
)
DECREE_RE = re.compile(r"N\s?[°º]\s*(\d\s?\d\s?\d)\s*-\s*(\d\s?\d\s?\d\s?\d)\s*-\s*EM")
ERRATA_RE = re.compile(r"\(\*\)\s*RECTIFICADO POR FE DE ERRATAS|RECTIFICADO POR FE DE ERRATAS")

# Palabras funcionales: si las dos piezas lo son, no se unen ("sin o" no pasa a "sino").
FUNCTION_WORDS = set(
    "a al con de del e el en es la las lo los ni no o para por que se si sin su sus un una uno y ya "
    "le les me mi nos os te tu ha he hay son ser sea fue era como cual mas más muy sobre entre tras "
    "este esta esto ese esa eso cada otro otra todo toda".split()
)


@dataclass
class Unit:
    kind: str                    # "articulo" | "anexo"
    number: str                  # "41", "16 A"
    text: str                    # texto vigente
    title: str | None = None     # Título PRIMERO … (artículos) o nombre del anexo
    title_name: str | None = None
    chapter: str | None = None
    chapter_name: str | None = None
    subchapter: str | None = None
    subchapter_name: str | None = None
    amendments: list[dict] = field(default_factory=list)   # [{"action", "decree", "date"}]
    original_text: str | None = None                        # texto anterior a una modificación
    term: str | None = None                                 # término definido (solo definiciones del art. 7)

    @property
    def label(self) -> str:
        if self.kind == "anexo":
            return f"Anexo N° {self.number}"
        if self.kind == "definicion":
            return f"Artículo {self.number} (definición: {self.term})"
        return f"Artículo {self.number}"


def strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def normalize(text: str) -> str:
    """Minúsculas y sin tildes, conservando la longitud de las palabras."""
    return strip_accents(text.lower())


# ------------------------------------------------------------------ reparación de palabras

_WORD = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")


def build_vocabulary(text: str) -> collections.Counter:
    return collections.Counter(w.lower() for w in _WORD.findall(text))


def _fragment_scores(tokens: list[str], vocab: collections.Counter) -> dict[str, float]:
    """Proporción de apariciones de cada pieza en las que, unida a su vecina, forma una
    palabra que sí aparece intacta en el documento. Cerca de 1 → fragmento ("ento");
    cerca de 0 → palabra real ("bajo")."""
    joinable, total = collections.Counter(), collections.Counter()
    words = []
    for i, t in enumerate(tokens):
        core = re.fullmatch(r"[^\wÁÉÍÓÚÜÑáéíóúüñ]*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)[^\wÁÉÍÓÚÜÑáéíóúüñ]*", t)
        if core:
            words.append((i, core.group(1).lower()))
    for k, (i, w) in enumerate(words):
        total[w] += 1
        for other in (k - 1, k + 1):
            if 0 <= other < len(words) and abs(words[other][0] - i) == 2 and tokens[min(i, words[other][0]) + 1] == " ":
                pair = w + words[other][1] if other > k else words[other][1] + w
                if vocab[pair] >= 2:
                    joinable[w] += 1
                    break
    return {w: joinable[w] / total[w] for w in total}


def repair_split_words(text: str, vocab: collections.Counter | None = None, max_parts: int = 4) -> tuple[str, int]:
    """Une fragmentos separados por un espacio ("m ineras" → "mineras", "reglam ento" →
    "reglamento") cuando la palabra completa aparece intacta al menos 2 veces en el
    documento y al menos una pieza es un fragmento (casi siempre aparece unible). Así
    "de bajo riesgo" no se convierte en "debajo riesgo". Devuelve el texto y las uniones."""
    vocab = vocab if vocab is not None else build_vocabulary(text)
    tokens = re.split(r"( +)", text)  # conserva separadores; solo un espacio simple cuenta como rotura
    fragment = _fragment_scores(tokens, vocab)

    def is_fragment(piece: str) -> bool:
        return piece not in FUNCTION_WORDS and (len(piece) == 1 or fragment.get(piece, 0) >= 0.5)

    def best_join(i: int):
        """Mejor unión que empieza en el token i: (fin, palabra, frecuencia) o None.
        Se permite puntuación antes de la primera pieza y después de la última."""
        for parts in range(max_parts, 1, -1):
            end = i + 2 * (parts - 1)
            if end >= len(tokens) or any(s != " " for s in tokens[i + 1:end:2]):
                continue
            raw = tokens[i:end + 1:2]
            first = re.fullmatch(r"([^\wÁÉÍÓÚÜÑáéíóúüñ]*)([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)", raw[0])
            last = re.fullmatch(r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)([^\wÁÉÍÓÚÜÑáéíóúüñ]*)", raw[-1])
            if not first or not last or not all(_WORD.fullmatch(p) for p in raw[1:-1]):
                continue
            pieces = [first.group(2)] + raw[1:-1] + [last.group(1)]
            word = "".join(pieces)
            if vocab[word.lower()] >= 2 and any(is_fragment(p.lower()) for p in pieces):
                return end, first.group(1) + word + last.group(2), vocab[word.lower()]
        return None

    out, joins, i = [], 0, 0
    while i < len(tokens):
        here = best_join(i)
        if here:
            # "uso de m aquinaria": si la pieza siguiente inicia una unión más frecuente
            # ("maquinaria"), se prefiere esa y no "dem".
            later = best_join(i + 2) if i + 2 < len(tokens) and tokens[i + 1] == " " else None
            if later and later[2] > here[2]:
                here = None
        if here:
            end, word, _ = here
            out.append(word)
            joins += (end - i) // 2
            i = end + 1
        else:
            out.append(tokens[i])
            i += 1
    return "".join(out), joins


def clean_text(text: str) -> str:
    text = ERRATA_RE.sub(" ", text)
    text = text.replace("­", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip().strip("“”\"").strip()


def _heading_name(text: str, start: int) -> str:
    """Nombre del encabezado: texto en mayúsculas o primera línea tras el número."""
    rest = text[start:start + 200]
    rest = ARTICLE_RE.split(rest, maxsplit=1)[0]
    lines = [l.strip() for l in rest.split("\n") if l.strip()]
    name = []
    for line in lines[:4]:
        if CHAPTER_RE.match(line) or SUBCHAPTER_RE.match(line) or TITLE_RE.match(line):
            break
        if not line.isupper():
            if not name:
                name.append(line)
            break
        name.append(line)
    name = re.split(r"\s+(?:Subcap[íi]tulo|CAP[ÍI]TULO|T[ÍI]TULO)\b", " ".join(name))[0]
    return re.sub(r"\s+", " ", name).strip(" .") or None


# ------------------------------------------------------------------ análisis del documento

def locate_sections(text: str) -> tuple[int, int, int]:
    """Inicio del cuerpo del reglamento, inicio de su disposición transitoria y de los anexos."""
    titles = [m.start() for m in re.finditer(r"REGLAMENTO DE SEGURIDAD Y SALUD OCUPACIONAL\s*(?:EN\s+MINER[ÍI]A)?\s*\n\s*T[ÍI]TULO\s+PRIMERO", text)]
    if not titles:
        raise ValueError("No se encontró el inicio del reglamento (TÍTULO PRIMERO)")
    body_start = titles[-1]
    transitory = [m.start() for m in re.finditer(r"DISPOSICI[ÓO]N COMPLEMENTARIA TRANSITORIA", text)]
    body_end = next((p for p in transitory if p > body_start), len(text))
    annex_start = next((m.start() for m in ANNEX_RE.finditer(text) if m.start() > body_end), len(text))
    return body_start, body_end, annex_start


def _events(body: str):
    events = []
    for kind, regex in (("titulo", TITLE_RE), ("capitulo", CHAPTER_RE), ("subcapitulo", SUBCHAPTER_RE)):
        for m in regex.finditer(body):
            events.append((m.start(), m.end(), kind, m.group(1)))
    for m in ARTICLE_RE.finditer(body):
        events.append((m.start(), m.end(), "articulo", re.sub(r"\s", "", m.group(1))))
    return sorted(events)


def _amendment(note: re.Match) -> dict:
    d = DECREE_RE.search(note.group(3))
    if d:
        number, year = (re.sub(r"\s", "", g) for g in d.groups())
        decree = f"DS N° {number}-{year}-EM"
    else:
        decree = note.group(3).strip()
    return {"action": note.group(2).lower()[:-1] + "o",
            "scope": note.group(1),
            "decree": decree,
            "date": re.sub(r"\s+", " ", note.group(4))}


def parse_articles(body: str) -> list[Unit]:
    events = _events(body)
    context = {"titulo": (None, None), "capitulo": (None, None), "subcapitulo": (None, None)}
    units: dict[str, Unit] = {}
    order: list[str] = []
    for idx, (start, end, kind, value) in enumerate(events):
        if kind != "articulo":
            context[kind] = (value, _heading_name(body, end))
            if kind == "titulo":
                context["capitulo"] = context["subcapitulo"] = (None, None)
            elif kind == "capitulo":
                context["subcapitulo"] = (None, None)
            continue
        nxt = events[idx + 1][0] if idx + 1 < len(events) else len(body)
        raw = body[end:nxt]
        notes = list(NOTE_RE.finditer(raw))
        # Notas de artículo completo al final del segmento: el texto siguiente con el mismo número es el vigente.
        article_note = next((n for n in notes if n.group(1) == "Artículo"), None)
        own_text = raw[:article_note.start()] if article_note else raw
        inline_amendments = [_amendment(n) for n in notes if n.group(1) != "Artículo"]
        text = clean_text(NOTE_RE.sub(lambda n: f" [{_amendment(n)['action'].capitalize()} por {_amendment(n)['decree']}] ", own_text)
                          .replace("(*)", ""))
        unit = Unit("articulo", value, text,
                    title=context["titulo"][0], title_name=context["titulo"][1],
                    chapter=context["capitulo"][0], chapter_name=context["capitulo"][1],
                    subchapter=context["subcapitulo"][0], subchapter_name=context["subcapitulo"][1],
                    amendments=inline_amendments)
        if value in units:
            previous = units[value]
            unit.original_text = previous.text
            unit.amendments = previous.amendments + unit.amendments
            if previous.__dict__.get("_pending"):
                unit.amendments.append(previous.__dict__.pop("_pending"))
            units[value] = unit
        else:
            units[value] = unit
            order.append(value)
        if article_note:
            units[value].__dict__["_pending"] = _amendment(article_note)
    result = []
    for key in order:
        u = units[key]
        pending = u.__dict__.pop("_pending", None)
        if pending:  # nota sin texto nuevo (p. ej. derogación)
            u.amendments.append(pending)
        result.append(u)
    return result


def parse_annexes(text: str, start: int = 0) -> list[Unit]:
    """Anexos incluidos en el PDF. El texto consolidado solo trae los anexos modificados
    (1 a 3); los formatos restantes se publicaron por separado."""
    matches = [m for m in ANNEX_RE.finditer(text) if m.start() >= start]
    units = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segment = text[m.end():end]
        notes = list(NOTE_RE.finditer(segment))
        tail_note = notes[-1] if notes and notes[-1].group(1).startswith("Anexo") else None
        body = segment[:tail_note.start()] if tail_note else segment
        unit = Unit("anexo", m.group(1), clean_text(NOTE_RE.sub(" ", body).replace("(*)", "")),
                    title=_heading_name(text, m.end()))
        before = text[max(start - 600, 0):m.start()] if i == 0 else text[matches[i - 1].end():m.start()]
        for note in NOTE_RE.finditer(before):
            if note.group(1).startswith("Anexo"):
                unit.amendments.append(_amendment(note))
                break
        units.append(unit)
    return units


TERM_LINE = re.compile(r"^[ \t]*[\"“]?([A-ZÁÉÍÓÚÑ][^\n.:;]{1,140}?)(?:\s*:|\s{4,}|[ \t]*\n)")


def split_definitions(article: Unit, raw: str) -> list[Unit]:
    """Divide el artículo 7 en una unidad por término definido. Si una definición fue
    modificada, la versión posterior (entre comillas, tras la nota) reemplaza a la anterior."""
    defs: dict[str, Unit] = {}
    order: list[str] = []
    # Un término puede empezar a mitad de línea tras el punto final de la definición anterior.
    raw = re.sub(r"([.:])[ \t]{5,}(?=[A-ZÁÉÍÓÚÑ])", r"\1\n     ", raw)
    lines = raw.split("\n")
    # Términos en dos líneas ("... y Enfermedades" / "Ocupacionales" / definición).
    merged = []
    for line in lines:
        prev = merged[-1] if merged else ""
        if (merged and len(line.split()) <= 3 and line.strip()[:1].isupper() and not line.strip().endswith(".")
                and 0 < len(prev.strip()) <= 110 and not prev.strip().endswith((".", ":", ";")) and len(prev.split()) >= 4
                and TERM_LINE.match(prev + "\n") and prev.strip() == TERM_LINE.match(prev + "\n").group(1).strip()):
            merged[-1] = prev.rstrip() + " " + line.strip()
        else:
            merged.append(line)
    lines = merged
    starts = []
    for idx, line in enumerate(lines):
        m = TERM_LINE.match(line + "\n")
        if not m:
            continue
        term = m.group(1).strip()
        words = term.split()
        rest = line[m.end():].strip() if m.end() <= len(line) else ""
        standalone = not rest
        # Un término: pocas palabras, no termina en punto, y le sigue la definición en la misma línea
        # (separada por 4+ espacios o ":") o en la línea siguiente.
        if len(words) > 14 or term[0].isdigit() or re.search(r"\bx\b|=", term) or term.lower().startswith(("es ", "según", "el ", "la ", "los ", "las ", "para ", "se ", "en ")):
            continue
        if standalone and (len(line.strip()) > 120 or idx + 1 >= len(lines) or not lines[idx + 1].strip()[:1].isupper()):
            continue
        starts.append((idx, term, line.lstrip().startswith(("\"", "“"))))
    for k, (idx, term, quoted) in enumerate(starts):
        stop = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        chunk = "\n".join(lines[idx:stop])
        chunk = chunk.split(term, 1)[1] if term in chunk else chunk
        note = NOTE_RE.search(chunk)
        amendment = _amendment(note) if note else None
        chunk = chunk[:note.start()] if note else chunk
        text = clean_text(chunk.lstrip(" :\t").replace("(*)", ""))
        if len(text) < 15:
            continue
        key = normalize(re.sub(r"\s*\(.*?\)", "", term)).strip()
        unit = Unit("definicion", article.number, text, title=article.title, title_name=article.title_name,
                    chapter=article.chapter, chapter_name=article.chapter_name,
                    subchapter=article.subchapter, subchapter_name=article.subchapter_name, term=term)
        if key in defs:
            unit.original_text = defs[key].text
            unit.amendments = defs[key].amendments
        if amendment:
            unit.amendments = unit.amendments + [amendment]
        if key not in defs:
            order.append(key)
        defs[key] = unit
    return [defs[k] for k in order]


def parse_document(raw_text: str) -> dict:
    vocab = build_vocabulary(raw_text)
    text, joins = repair_split_words(raw_text, vocab)
    body_start, body_end, annex_start = locate_sections(text)
    body = text[body_start:body_end]
    articles = parse_articles(body)
    definitions = []
    seven = next((a for a in articles if a.number == "7"), None)
    if seven:
        m7 = [m for m in ARTICLE_RE.finditer(body) if re.sub(r"\s", "", m.group(1)) == "7"][0]
        m8 = next(m for m in ARTICLE_RE.finditer(body, m7.end()) if re.sub(r"\s", "", m.group(1)) != "7")
        definitions = split_definitions(seven, body[m7.end():m8.start()])
    annexes = parse_annexes(text, annex_start)
    decrees = sorted({a["decree"] for u in articles + definitions + annexes for a in u.amendments},
                     key=lambda d: d[-7:])
    return {
        "index_version": INDEX_VERSION,
        "source": "DS 024-2016-EM, texto consolidado incluido en data/ds024.pdf",
        "amendments_included": decrees,
        "word_repairs": joins,
        "counts": {"articulos": len(articles), "definiciones": len(definitions), "anexos": len(annexes)},
        "units": [asdict(u) for u in articles + definitions + annexes],
    }


def extract_pdf_text(pdf_path: Path = PDF_PATH) -> str:
    from pypdf import PdfReader  # solo se necesita para reconstruir el índice
    reader = PdfReader(str(pdf_path))
    return "".join((page.extract_text() or "") for page in reader.pages)


def build_index(pdf_path: Path = PDF_PATH, out: Path = INDEX_PATH) -> dict:
    data = parse_document(extract_pdf_text(pdf_path))
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def load_units(path: Path = INDEX_PATH) -> tuple[list[Unit], dict]:
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}. Genérelo con: python -m app.build_index")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("index_version") != INDEX_VERSION:
        raise ValueError("El índice es de otra versión. Regenérelo con: python -m app.build_index")
    units = [Unit(**u) for u in data["units"]]
    meta = {k: v for k, v in data.items() if k != "units"}
    return units, meta
