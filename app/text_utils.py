import unicodedata


def normalize(text: str) -> str:
    """
    Lowercase + remove accents/diacritics.
    """
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))