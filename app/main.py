from app.core import MiningSystem
from app.pdf_reader import PDFReader


def main():
    system = MiningSystem()
    print(system.system_info())

    print("\nLoading DS 024 PDF...")

    pdf = PDFReader("data/ds024.pdf")
    text = pdf.extract_text()

    print("PDF loaded successfully.")
    print(f"Total characters extracted: {len(text)}")


if __name__ == "__main__":
    main()
    