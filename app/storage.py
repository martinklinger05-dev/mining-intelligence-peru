"""Historial de consultas y exportaciones de texto. Todo se guarda en output/ (no se versiona)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.regulation import ROOT

OUTPUT_DIR = ROOT / "output"
HISTORY_PATH = OUTPUT_DIR / "history.jsonl"


def append_history(record: dict[str, Any], path: Path = HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_last_history(n: int = 10, path: Path = HISTORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines()[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def export_text(content: str, prefix: str, folder: Path = OUTPUT_DIR) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path.write_text(content, encoding="utf-8")
    return path
