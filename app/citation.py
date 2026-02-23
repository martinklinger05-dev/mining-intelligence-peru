import re


def extract_article(snippet: str, query: str | None = None) -> str | None:
    """
    Extract the most relevant 'Artículo XX' from a snippet.
    Strategy:
    - Find all occurrences of 'Artículo XX'
    - If query is provided, choose the article closest to the query occurrence
    - Otherwise, choose the last article found (usually the more specific one later in text)
    """
    # Find all articles with their positions
    matches = [(m.start(), m.group(1)) for m in re.finditer(r"Artículo\s+(\d+)", snippet, flags=re.IGNORECASE)]
    if not matches:
        return None

    if query:
        q = query.lower()
        s = snippet.lower()
        qpos = s.find(q)
        if qpos != -1:
            # choose article whose position is closest to qpos
            closest = min(matches, key=lambda x: abs(x[0] - qpos))
            return closest[1]

    # fallback: choose the last one (often the relevant one later in snippet)
    return matches[-1][1]