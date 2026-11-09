"""Evalúa el buscador con preguntas cuya respuesta se verificó leyendo el reglamento.

Uso: python -m app.evaluate            (resumen)
     python -m app.evaluate --detail   (cada pregunta)

Métricas: acierto en la 1.ª posición (hit@1) y entre las 3 primeras (hit@3), por partición.
"""
import argparse
import json
from pathlib import Path

from app.regulation import ROOT, load_units
from app.search import Index

QUESTIONS = ROOT / "tests" / "eval_questions.json"


def evaluate(index: Index, questions: list[dict]) -> dict:
    rows = []
    for q in questions:
        labels = [h.unit.label for h in index.search(q["q"], k=3)]
        rank = next((i + 1 for i, label in enumerate(labels) if label in q["accept"]), None)
        rows.append({"id": q["id"], "split": q["split"], "q": q["q"], "top3": labels, "rank": rank})
    summary = {}
    for split in ("dev", "test", "all"):
        sel = [r for r in rows if split == "all" or r["split"] == split]
        summary[split] = {"n": len(sel),
                          "hit@1": sum(r["rank"] == 1 for r in sel),
                          "hit@3": sum(r["rank"] is not None for r in sel)}
    return {"summary": summary, "rows": rows}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--detail", action="store_true")
    args = p.parse_args()
    units, _ = load_units()
    questions = json.loads(Path(QUESTIONS).read_text(encoding="utf-8"))["questions"]
    result = evaluate(Index(units), questions)
    for split, s in result["summary"].items():
        print(f"{split:5}  n={s['n']:2}  hit@1={s['hit@1']:2}/{s['n']}  hit@3={s['hit@3']:2}/{s['n']}")
    if args.detail:
        for r in result["rows"]:
            mark = f"#{r['rank']}" if r["rank"] else "--"
            print(f"[{r['split']:4}] {mark:3} {r['q']}\n          → {' | '.join(r['top3'])}")


if __name__ == "__main__":
    main()
