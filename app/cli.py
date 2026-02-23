from app.pdf_reader import PDFReader
from app.search import simple_search
from app.answer import answer_with_citation


def run_cli(pdf_path: str = "data/ds024.pdf"):
    print("\n[MIP] Loading document...")
    pdf = PDFReader(pdf_path)
    text = pdf.extract_text()
    print(f"[MIP] Document loaded. Characters: {len(text)}")

    print("\n[MIP] Ready. Type your question. Commands: /exit, /help\n")

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
            print("  /help  - show help")
            print("  /exit  - exit")
            print("\nExample questions:")
            print("  ¿Qué dice el DS 024 sobre EPP?")
            print("  ¿Qué indica sobre IPERC?")
            print("  ¿Qué sanciones hay por alterar EPP?")
            print()
            continue

        # Search + answer
        results = simple_search(text, user_q, window=650)
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