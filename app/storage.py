import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any


HISTORY_PATH = Path("docs/history.jsonl")


def ensure_docs_folder():
    Path("docs").mkdir(parents=True, exist_ok=True)


def append_history(record: dict[str, Any]):
    ensure_docs_folder()
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_last_history(n: int = 10) -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []

    # leer últimas N líneas sin cargar todo gigante (simple y suficiente)
    lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()
    last = lines[-n:] if len(lines) > n else lines

    out = []
    for line in last:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def export_last_answer_to_txt(last_record: dict[str, Any]) -> str:
    ensure_docs_folder()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path("docs") / f"consulta_{ts}.txt"

    q = last_record.get("question", "")
    response = last_record.get("response", "")
    chapter = last_record.get("chapter", "N/D")
    chapter_title = last_record.get("chapter_title", "N/D")
    article = last_record.get("article", "N/D")
    evidence = last_record.get("evidence", "")

    content = (
        "MINING INTELLIGENCE PERU (MIP)\n"
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "\n"
        f"Pregunta:\n{q}\n"
        "\n"
        "Respuesta:\n"
        f"{response}\n"
        "\n"
        "Cita:\n"
        f"Capítulo: {chapter}\n"
        f"Título: {chapter_title}\n"
        f"Artículo: {article}\n"
        "\n"
        "Evidencia (snippet):\n"
        f"{evidence}\n"
    )

    out_path.write_text(content, encoding="utf-8")
    return str(out_path)