import re
from app.text_utils import normalize

# Stopwords básicas en español (mínimas, pero efectivas)
STOPWORDS = {
    "que", "qué", "dice", "del", "de", "el", "la", "los", "las", "sobre", "segun", "según",
    "en", "un", "una", "y", "o", "a", "por", "para", "al", "se", "es", "son", "hay"  # las dejamos fuera de keywords por defecto
}

# Sinónimos / alias (puedes crecer esto con tu hermano)
SYNONYMS = {
    "epp": ["epp", "equipo de proteccion personal", "equipo de protección personal"],
    "iperc": ["iperc", "identificacion de peligros", "evaluacion de riesgos", "medidas de control"],
    "negativa": [
    "derecho a la negativa",
    "negativa de trabajo",
    "retirarse de cualquier area de trabajo",
    "peligro de alto riesgo",
    "retirarse de cualquier área de trabajo",
    "dar aviso inmediato a sus superiores"
],
}

def extract_search_terms(user_question: str) -> list[str]:
    q_norm = normalize(user_question)

    # siempre inicializa terms al inicio
    terms: list[str] = []

    # Sinónimos por intención
    if "epp" in q_norm:
        terms.extend(SYNONYMS["epp"])

    if "iperc" in q_norm:
        terms.extend(SYNONYMS["iperc"])

    if ("negarse" in q_norm) or ("negativa" in q_norm) or ("retirarse" in q_norm) or ("peligro" in q_norm):
        terms.extend(SYNONYMS["negativa"])
    if ("negarse" in q_norm) or ("negativa" in q_norm) or ("retirarse" in q_norm) or ("peligro" in q_norm):
        terms.extend(SYNONYMS["negativa"])
        # Evita que palabras genéricas dominen la búsqueda
        # (porque ya tenemos frases fuertes)
        avoid_generic_words = True
    else:
        avoid_generic_words = False

    # Keywords generales (quitando stopwords)
    words = re.findall(r"[a-z0-9]+", q_norm)
    
    for w in words:
        if len(w) <= 2:
            continue
        if w in STOPWORDS:
            continue
        if avoid_generic_words and w in {"derecho", "trabajar"}:
            continue
        terms.append(w)

    # Deduplicar conservando orden
    seen = set()
    out = []
    for t in terms:
        t2 = t.strip()
        if not t2:
            continue
        t2n = normalize(t2)
        if t2n in seen:
            continue
        seen.add(t2n)
        out.append(t2)

    return out