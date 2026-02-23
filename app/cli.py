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

def prompt_or_cancel(label: str) -> str | None:
    v = input(label).strip()
    if v.lower() in ("/exit", "exit", "/salir", "salir", "/cancel", "cancel", "/cancelar", "cancelar"):
        return None
    return v

def run_cli(pdf_path: str = "data/ds024.pdf"):
    print("\n[MIP] Loading document...")
    pdf = PDFReader(pdf_path)
    text = pdf.extract_text()
    print(f"[MIP] Document loaded. Characters: {len(text)}")

    print("\n[MIP] Ready. Type your question. Commands: /exit, /help\n")
    last_record = None
    last_report = None
    last_word_path = None
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
            print("  /export-word - export last accident report to Word (.docx)")
            print("  /open-word  - open last exported Word (Windows)")
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

        if cmd in ("/export-word", "export-word", "/word", "word", "/exportar-word", "exportar-word"):
            if not last_report:
                print("\n[MIP] No hay informe de accidente para exportar. Ejecuta /accidente primero.\n")
                continue

            from app.word_export import export_accident_report_to_docx
            path = export_accident_report_to_docx(last_report)
            last_word_path = path
            print(f"\n[MIP] Word exportado a: {path}\n")
            print(f"[MIP] Tip: para abrirlo rápido en Windows: start {path}")
            continue

        if cmd in ("/open-word", "open-word", "/abrir-word", "abrir-word"):
            if not last_word_path:
                print("\n[MIP] No hay Word exportado aún. Ejecuta /export-word primero.\n")
                continue

            import os
            os.system(f'start "" "{last_word_path}"')
            print(f"\n[MIP] Abriendo: {last_word_path}\n")
            continue

        if cmd in ("/export", "export", "/exportar", "exportar"):
            if not last_record:
                print("\n[MIP] Nothing to export yet. Ask a question first.\n")
                continue

            path = export_last_answer_to_txt(last_record)
            print(f"\n[MIP] Exported to: {path}\n")
            continue

        if cmd in ("/accidente", "accidente", "/accident", "accident"):
            print("\n[MIP] MODO INFORME DE ACCIDENTE (FORMATO MINA)")

            equipo = prompt_or_cancel("Equipo (ej. Volquete DCR-21): ")
            if equipo is None:
                print("\n[MIP] Formulario cancelado.\n")
                continue

            area = prompt_or_cancel("Área / Labor (ej. NV 4300 / RP +6000): ")
            if area is None:
                print("\n[MIP] Formulario cancelado.\n")
                continue

            turno = prompt_or_cancel("Turno (Día/Noche): ")
            if turno is None:
                print("\n[MIP] Formulario cancelado.\n")
                continue
            
            fecha_evento = prompt_or_cancel("Fecha y hora del evento (YYYY-MM-DD HH:MM) [Enter = ahora]: ")
            if fecha_evento is None:
                print("\n[MIP] Formulario cancelado.\n")
                continue
            if not fecha_evento:
                fecha_evento = datetime.now().strftime("%Y-%m-%d %H:%M")

            lesiones = prompt_or_cancel("¿Hubo lesiones? (si/no): ")
            if lesiones is None:
                print("\n[MIP] Formulario cancelado.\n")
                continue
            lesiones = lesiones.lower()

            danio = prompt_or_cancel("Tipo de daño (material/personal/ambos/ninguno): ")
            if danio is None:
                print("\n[MIP] Formulario cancelado.\n")
                continue
            danio = danio.lower()

            descripcion = prompt_or_cancel("Describe el evento (qué pasó, dónde, condiciones, maniobra, etc.): ")
            if descripcion is None:
                print("\n[MIP] Formulario cancelado.\n")
                continue
            
            print("\n¿Hubo lesiones? (si/no)")
            injury = input(">> ").strip().lower()

            print("\nTipo de daño: (material / personal / ambos / ninguno)")
            damage_type = input(">> ").strip().lower()

            print("\nDescribe el evento (qué pasó, dónde, condiciones, maniobra, etc.):")
            description = input(">> ").strip()

            full_desc = (
                f"Evento: {descripcion}. "
                f"Equipo: {equipo}. "
                f"Área: {area}. "
                f"Turno: {turno}. "
                f"Fecha evento: {fecha_evento}. "
                f"Lesiones: {lesiones}. "
                f"Daño: {danio}."
            )

            report = generate_accident_report(full_desc, text)

            # Guardar metadata para Word
            report["meta"] = {
                "equipo": equipo,
                "area": area,
                "turno": turno,
                "fecha_evento": fecha_evento,
                "lesiones": lesiones,
                "danio": danio,
            }

            last_report = report
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
