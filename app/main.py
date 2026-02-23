from app.core import MiningSystem
from app.pdf_reader import PDFReader
from app.search import simple_search


def main():
    system = MiningSystem()
    print(system.system_info())

    pdf = PDFReader("data/ds024.pdf")
    text = pdf.extract_text()

    query = "EPP"
    print(f"\nSearching for: {query}")
    results = simple_search(text, query)

    for i, r in enumerate(results, 1):
        print(f"\n--- Result {i} (score={r.score}) ---")
        print(r.snippet)


if __name__ == "__main__":
    main()