from app.core import MiningSystem
from app.pdf_reader import PDFReader
from app.search import simple_search
from app.answer import answer_with_citation


def main():
    system = MiningSystem()
    print(system.system_info())

    # Cargar PDF
    pdf = PDFReader("data/ds024.pdf")
    text = pdf.extract_text()

    # Buscar EPP
    query = "EPP"
    results = simple_search(text, query)

    ans = answer_with_citation(query, results)

    print("\n=== ANSWER ===")
    print(ans.response)

    print("\n=== ARTICLE DETECTED ===")
    print(ans.article)

    print("\n=== EVIDENCE (snippet) ===")
    print(ans.evidence)


if __name__ == "__main__":
    main()