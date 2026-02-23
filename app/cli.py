from app.accident import generate_accident_report
from datetime import datetime

from app.pdf_reader import PDFReader
from app.search import multi_search
from app.query_utils import extract_search_terms
from app.answer import answer_with_citation
from app.storage import append_history, read_last_history, export_last_answer_to_txt
from app.search import multi_search
from app.query_utils import extract_search_terms
from app.answer import answer_with_citation
from app.pdf_reader import PDFReader

def run_cli(pdf_path: str = "data/ds024.pdf"):
    print("\n[MIP] Loading document...")
    pdf = PDFReader(pdf_path)
    text = pdf.extract_text()
    print(f"[MIP] Document loaded. Characters: {len(text)}")

    print("\n[MIP] Ready. Type your question. Commands: /exit, /help\n")
    last_record = None
    while True:
        user_q = input("> ").strip()
        if not user_q:
            continue

        cmd = user_q.lower()

        if cmd in ("/exit", "exit", "salir", "/salir"):
            print("[MIP] Bye.")
            break

        if cmd in ("/help", "help", "ayuda", "/ayuda"):
            print("\nCommands:")
            print("  /help      - show help")
            print("  /exit      - exit")
            print("  /history   - last 10 queries")
            print("  /export    - export last answer to txt")
            print("  /accidente - generate accident report")
            print("\nExample questions:")
            print("  ¿Qué dice el DS 024 sobre EPP?")
            print("  ¿Qué indica sobre IPERC?")
            print()
            continue

        if cmd in ("/history", "history", "/historial", "historial"):
            items = read_last_history(10)
            if not items:
                print("\n[MIP] No history yet.\n")
                continue

            print("\n[MIP] Last queries:")
            for i, it in enumerate(items, 1):
                art = it.get("article", "N/D")
                chap = it.get("chapter", "N/D")
                q = it.get("question", "")
                t = it.get("timestamp", "")
                print(f"{i}. [{t}] Art:{art} Cap:{chap} | {q}")
            print()
            continue

        if cmd in ("/export", "export", "/exportar", "exportar"):
            if not last_record:
                print("\n[MIP] Nothing to export yet. Ask a question first.\n")
                continue

            path = export_last_answer_to_txt(last_record)
            print(f"\n[MIP] Exported to: {path}\n")
            continue

        if cmd in ("/accidente", "accidente", "/accident", "accident"):
            print("\n[MIP] MODO INFORME DE ACCIDENTE")
            print("Describe el evento (qué pasó, dónde, qué equipo, condición de vía, etc.).")
            description = input(">> ").strip()

            print("\n¿Hubo lesiones? (si/no)")
            injury = input(">> ").strip().lower()

            print("\nTipo de daño: (material / personal / ambos / ninguno)")
            damage_type = input(">> ").strip().lower()

            full_desc = (
                f"Evento: {description}. "
                f"Lesiones: {injury}. "
                f"Daño: {damage_type}."
            )

            report = generate_accident_report(full_desc, text)

            print("\n=== INFORME GENERADO ===")
            print(report["conclusion"])
            print()

            last_record = {
                "timestamp": report["timestamp"],
                "question": f"ACCIDENTE: {full_desc}",
                "search_terms": extract_search_terms(full_desc),
                "response": report["conclusion"],
                "article": "N/D",
                "chapter": "N/D",
                "chapter_title": "N/D",
                "evidence": report["normative_support"],
            }
            append_history(last_record)
            continue

        # --- Normal question mode ---
        terms = extract_search_terms(user_q)
        print(f"\n[MIP] Search terms: {terms}")

        results = multi_search(text, terms, window=650)
        ans = answer_with_citation(user_q, results)

        print("\n=== RESPUESTA ===")
        print(ans.response)

        print("\n=== CITA ===")
        print(f"Capítulo: {ans.chapter or 'N/D'}")
        print(f"Título: {ans.chapter_title or 'N/D'}")
        print(f"Artículo: {ans.article or 'N/D'}")

        print("\n=== EVIDENCIA (snippet) ===")
        print(ans.evidence)
        print("\n")

        last_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": user_q,
            "search_terms": terms,
            "response": ans.response,
            "article": ans.article or "N/D",
            "chapter": ans.chapter or "N/D",
            "chapter_title": ans.chapter_title or "N/D",
            "evidence": ans.evidence,
        }
        append_history(last_record)
